"""Build bootstrap intervals and multi-seed virtual-batch results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PAPER_ROOT.parent.parent
ARTIFACTS = (
    PROJECT_ROOT
    / "training"
    / "so_active_v3"
    / "runs"
    / "so_active_v3"
    / "fold0"
    / "artifacts"
)
sys.path.insert(0, str(PAPER_ROOT / "src"))

from stells_paper.overlap_audit import file_sha256
from stells_paper.statistical_analysis import (
    DatasetArrays,
    paired_bootstrap,
    summarize_seed_runs,
    virtual_batch_metrics,
)


def _dependencies() -> tuple[Any, Any]:
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "Statistical result generation requires numpy and pandas. "
            "Run it with the stells backend Docker image."
        ) from exc
    return np, pd


def load_standard(path: Path) -> DatasetArrays:
    np, pd = _dependencies()
    frame = pd.read_csv(
        path,
        usecols=["pIC50", "pred_pIC50", "is_active"],
        low_memory=False,
    )
    labels = frame["is_active"].astype(str).str.lower().isin(("true", "1"))
    return DatasetArrays(
        observed=frame["pIC50"].to_numpy(np.float64),
        predicted=frame["pred_pIC50"].to_numpy(np.float64),
        labels=labels.to_numpy(np.int8),
    )


def load_strict(path: Path, *, schema: str) -> DatasetArrays:
    np, pd = _dependencies()
    if schema == "bace":
        frame = pd.read_csv(
            path,
            usecols=["class_bin", "pIC50_true", "pred_pIC50"],
            low_memory=False,
        )
        label_col = "class_bin"
        observed_col = "pIC50_true"
    elif schema == "egfr":
        frame = pd.read_csv(
            path,
            usecols=["true_label", "true_pchembl", "pred_pIC50"],
            low_memory=False,
        )
        label_col = "true_label"
        observed_col = "true_pchembl"
    else:
        raise ValueError(f"unsupported strict schema: {schema}")
    return DatasetArrays(
        observed=frame[observed_col].to_numpy(np.float64),
        predicted=frame["pred_pIC50"].to_numpy(np.float64),
        labels=frame[label_col].to_numpy(np.int8),
    )


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Statistical Evaluation Summary",
        "",
        "## Paired Bootstrap Intervals",
        "",
        "| Dataset | Rows | RMSE 95% CI | Spearman 95% CI | ROC AUC 95% CI | EF@1% 95% CI |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, result in payload["bootstrap"].items():
        intervals = result["intervals"]

        def interval(metric: str) -> str:
            row = intervals.get(metric)
            return (
                f"{row['lower_95']:.4f}-{row['upper_95']:.4f}"
                if row is not None
                else "not estimated"
            )

        lines.append(
            f"| {name} | {result['rows']} | {interval('rmse')} | "
            f"{interval('spearman')} | {interval('roc_auc')} | {interval('ef_1')} |"
        )
    lines.extend(
        [
            "",
            "## Multi-seed Virtual Batches",
            "",
            "| Dataset | Batch | Seeds | EF@1% | EF@5% | EF@10% | NDCG@10% |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for dataset, by_batch in payload["virtual_batches"].items():
        for batch_size, result in by_batch.items():
            metrics = result["metrics"]

            def mean_sd(metric: str) -> str:
                row = metrics[metric]
                return f"{row['mean']:.4f} +/- {row['sd']:.4f}"

            lines.append(
                f"| {dataset} | {batch_size} | {len(result['seeds'])} | "
                f"{mean_sd('ef_1')} | {mean_sd('ef_5')} | "
                f"{mean_sd('ef_10')} | {mean_sd('ndcg_10')} |"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=PAPER_ROOT / "results")
    parser.add_argument("--large-bootstrap-replicates", type=int, default=200)
    parser.add_argument("--small-bootstrap-replicates", type=int, default=2000)
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[7, 42, 2026, 3407, 10007],
    )
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[100, 500, 1000])
    args = parser.parse_args()

    sources = {
        "ChEMBL36 internal validation": ARTIFACTS / "eval_fold0_val.csv",
        "ChEMBL36 temporal holdout": ARTIFACTS / "eval_fold0_future.csv",
        "BACE scaffold-disjoint": PAPER_ROOT / "results" / "bace_scaffold_disjoint.csv",
        "EGFR scaffold-disjoint replay": PAPER_ROOT
        / "results"
        / "egfr_scaffold_disjoint.csv",
    }
    datasets = {
        "ChEMBL36 internal validation": load_standard(
            sources["ChEMBL36 internal validation"]
        ),
        "ChEMBL36 temporal holdout": load_standard(
            sources["ChEMBL36 temporal holdout"]
        ),
        "BACE scaffold-disjoint": load_strict(
            sources["BACE scaffold-disjoint"], schema="bace"
        ),
        "EGFR scaffold-disjoint replay": load_strict(
            sources["EGFR scaffold-disjoint replay"], schema="egfr"
        ),
    }
    bootstrap: dict[str, Any] = {}
    for index, (name, data) in enumerate(datasets.items()):
        is_large = "ChEMBL36" in name
        bootstrap[name] = paired_bootstrap(
            data,
            replicates=(
                args.large_bootstrap_replicates
                if is_large
                else args.small_bootstrap_replicates
            ),
            seed=20260623 + index,
            include_ef=not is_large,
        )

    virtual_batches: dict[str, Any] = {}
    for name, data in datasets.items():
        virtual_batches[name] = {}
        for batch_size in args.batch_sizes:
            if len(data.observed) < batch_size // 2:
                continue
            runs = [
                virtual_batch_metrics(
                    data,
                    batch_size=batch_size,
                    seed=seed,
                )
                for seed in args.seeds
            ]
            virtual_batches[name][str(batch_size)] = summarize_seed_runs(runs)

    payload = {
        "protocol": {
            "bootstrap": "paired nonparametric bootstrap over frozen prediction rows",
            "large_bootstrap_replicates": args.large_bootstrap_replicates,
            "small_bootstrap_replicates": args.small_bootstrap_replicates,
            "virtual_batch_seeds": args.seeds,
            "virtual_batch_sizes": args.batch_sizes,
            "active_threshold": 7.0,
            "notes": [
                "EF bootstrap intervals are reported only for strict BACE and EGFR subsets.",
                "Virtual-batch variability reflects library composition and shuffle seed, not model retraining variability.",
            ],
        },
        "inputs": {
            name: {"path": str(path.resolve()), "sha256": file_sha256(path)}
            for name, path in sources.items()
        },
        "bootstrap": bootstrap,
        "virtual_batches": virtual_batches,
    }
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "statistical_results.json"
    md_path = output_dir / "statistical_results.md"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text(markdown(payload), encoding="utf-8")
    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
