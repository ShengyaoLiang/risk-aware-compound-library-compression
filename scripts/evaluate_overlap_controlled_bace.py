"""Evaluate BACE after removing fold-specific structure and scaffold overlap."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER_ROOT / "src"))

from stells_paper.metrics import binary_ranking_metrics, regression_metrics, roc_auc
from stells_paper.overlap_audit import canonicalize_smiles, file_sha256, murcko_scaffold
from stells_paper.parquet_overlap_audit import scan_fold_training_matches


FRACTIONS = (0.001, 0.005, 0.01, 0.05, 0.10, 0.20)


def _float(row: dict[str, str], column: str) -> float:
    value = float(row[column])
    if not math.isfinite(value):
        raise ValueError(f"non-finite value in {column}")
    return value


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            canonical = canonicalize_smiles(row.get("canonical_smiles") or row.get("mol") or "")
            if canonical is None:
                continue
            rows.append(
                {
                    "canonical_smiles": canonical,
                    "scaffold": murcko_scaffold(canonical) or "",
                    "class_bin": int(float(row["class_bin"])),
                    "pIC50_true": _float(row, "pIC50_true"),
                    "pred_pIC50": _float(row, "pred_pIC50"),
                }
            )
    return rows


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(rows, key=lambda row: row["pred_pIC50"], reverse=True)
    labels = [int(row["class_bin"]) for row in ranked]
    scores = [float(row["pred_pIC50"]) for row in ranked]
    observed = [float(row["pIC50_true"]) for row in ranked]
    return {
        "rows": len(ranked),
        "positives": sum(labels),
        "prevalence": sum(labels) / len(labels) if labels else 0.0,
        "roc_auc": roc_auc(labels, scores),
        "regression": regression_metrics(observed, scores).to_dict(),
        "ranking": {
            f"top_{fraction:g}": binary_ranking_metrics(labels, fraction=fraction).to_dict()
            for fraction in FRACTIONS
        },
    }


def write_compact_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = ["canonical_smiles", "scaffold", "class_bin", "pIC50_true", "pred_pIC50"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Overlap-controlled BACE Evaluation",
        "",
        f"- Original rows: {payload['original_rows']}",
        f"- Fold-0 training rows scanned: {payload['training_rows_scanned']}",
        f"- Removed standardized-structure matches: {payload['structure_matches']}",
        f"- Training-overlapping query scaffolds: {payload['scaffold_matches']}",
        "",
        "| Evaluation subset | Rows | Prevalence | ROC AUC | RMSE | Spearman | EF@1% | EF@5% | EF@10% |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, label in (
        ("full", "Original full BACE"),
        ("structure_disjoint", "Standardized-structure disjoint"),
        ("scaffold_disjoint", "Bemis-Murcko scaffold disjoint"),
    ):
        result = payload["subsets"][key]
        regression = result["regression"]
        ranking = result["ranking"]
        lines.append(
            f"| {label} | {result['rows']} | {result['prevalence']:.2%} | "
            f"{result['roc_auc']:.4f} | {regression['rmse']:.4f} | "
            f"{regression['spearman']:.4f} | "
            f"{ranking['top_0.01']['enrichment_factor']:.4f} | "
            f"{ranking['top_0.05']['enrichment_factor']:.4f} | "
            f"{ranking['top_0.1']['enrichment_factor']:.4f} |"
        )
    lines.extend(
        [
            "",
            "The original full-dataset result is retained for provenance only. Strong "
            "external-generalization claims must use the overlap-controlled subsets.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--training-dataset", type=Path, required=True)
    parser.add_argument("--held-out-fold", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    rows = load_rows(args.predictions)
    canonical_query = {row["canonical_smiles"] for row in rows}
    scaffold_query = {row["scaffold"] for row in rows if row["scaffold"]}
    training_rows, structure_matches, scaffold_matches = scan_fold_training_matches(
        dataset_path=args.training_dataset,
        held_out_fold=args.held_out_fold,
        canonical_query=canonical_query,
        scaffold_query=scaffold_query,
    )
    structure_disjoint = [
        row for row in rows if row["canonical_smiles"] not in structure_matches
    ]
    scaffold_disjoint = [
        row for row in rows if row["scaffold"] not in scaffold_matches
    ]

    payload = {
        "inputs": {
            "predictions_path": str(args.predictions.resolve()),
            "predictions_sha256": file_sha256(args.predictions),
            "training_dataset_path": str(args.training_dataset.resolve()),
            "training_dataset_sha256": file_sha256(args.training_dataset),
        },
        "original_rows": len(rows),
        "training_rows_scanned": training_rows,
        "held_out_fold": args.held_out_fold,
        "structure_matches": len(structure_matches),
        "scaffold_matches": len(scaffold_matches),
        "subsets": {
            "full": evaluate(rows),
            "structure_disjoint": evaluate(structure_disjoint),
            "scaffold_disjoint": evaluate(scaffold_disjoint),
        },
    }
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_compact_csv(output_dir / "bace_structure_disjoint.csv", structure_disjoint)
    write_compact_csv(output_dir / "bace_scaffold_disjoint.csv", scaffold_disjoint)
    (output_dir / "bace_overlap_controlled_eval.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "bace_overlap_controlled_eval.md").write_text(
        markdown(payload),
        encoding="utf-8",
    )
    print(output_dir / "bace_overlap_controlled_eval.json")
    print(output_dir / "bace_overlap_controlled_eval.md")


if __name__ == "__main__":
    main()
