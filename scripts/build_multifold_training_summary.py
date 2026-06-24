"""Summarize completed so_active_v3 training folds without exposing row IDs."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PAPER_ROOT.parent.parent
RUN_ROOT = PROJECT_ROOT / "training" / "so_active_v3" / "runs" / "so_active_v3"
OUTPUT_JSON = PAPER_ROOT / "results" / "multifold_training_summary.json"
OUTPUT_MD = PAPER_ROOT / "results" / "multifold_training_summary.md"
METRICS = ("rmse", "r2", "spearman", "top0_01_ef", "top0_05_ef", "top0_1_ef")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mean_sd(values: list[float]) -> dict[str, float | None]:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return {"mean": None, "sd": None}
    mean = sum(clean) / len(clean)
    if len(clean) < 2:
        return {"mean": mean, "sd": 0.0}
    var = sum((value - mean) ** 2 for value in clean) / (len(clean) - 1)
    return {"mean": mean, "sd": math.sqrt(var)}


def fold_payload(fold_dir: Path) -> dict[str, Any] | None:
    summary_path = fold_dir / "artifacts" / "train_summary.json"
    if not summary_path.exists():
        return None
    payload = load_json(summary_path)
    return {
        "fold": int(payload.get("fold", fold_dir.name.removeprefix("fold"))),
        "best_epoch": payload.get("best_epoch"),
        "last_finished_epoch": payload.get("last_finished_epoch"),
        "train_rows": payload.get("train_rows"),
        "val_rows": payload.get("val_rows"),
        "val_metrics": payload.get("val_metrics", {}),
        "future_metrics": payload.get("future_metrics", {}),
        "source": str(summary_path.relative_to(PROJECT_ROOT).as_posix()),
    }


def summarize_split(folds: list[dict[str, Any]], split: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for metric in METRICS:
        values = [
            row.get(f"{split}_metrics", {}).get(metric)
            for row in folds
            if row.get(f"{split}_metrics", {}).get(metric) is not None
        ]
        out[metric] = mean_sd(values)
    return out


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Multi-fold Training Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Completed folds: `{', '.join(str(x) for x in payload['completed_folds']) or 'none'}`",
        f"- Completed fold count: `{payload['completed_fold_count']}`",
        "",
        payload["interpretation"],
        "",
        "## Completed Fold Metrics",
        "",
        "| Fold | Val RMSE | Val Spearman | Val EF@1% | Future RMSE | Future Spearman | Future EF@1% |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    def fmt(value: object) -> str:
        if value is None:
            return "--"
        return f"{float(value):.4f}"

    for row in payload["folds"]:
        val = row.get("val_metrics", {})
        future = row.get("future_metrics", {})
        lines.append(
            f"| {row['fold']} | {fmt(val.get('rmse'))} | {fmt(val.get('spearman'))} | "
            f"{fmt(val.get('top0_01_ef'))} | {fmt(future.get('rmse'))} | "
            f"{fmt(future.get('spearman'))} | {fmt(future.get('top0_01_ef'))} |"
        )

    if payload["completed_fold_count"] >= 2:
        lines.extend(
            [
                "",
                "## Mean +/- SD",
                "",
                "| Split | RMSE | Spearman | EF@1% |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for split in ("val", "future"):
            summary = payload["summary"][split]
            lines.append(
                f"| {split} | {fmt(summary['rmse']['mean'])} +/- {fmt(summary['rmse']['sd'])} | "
                f"{fmt(summary['spearman']['mean'])} +/- {fmt(summary['spearman']['sd'])} | "
                f"{fmt(summary['top0_01_ef']['mean'])} +/- {fmt(summary['top0_01_ef']['sd'])} |"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    folds = []
    for fold_dir in sorted(RUN_ROOT.glob("fold*")):
        if not fold_dir.is_dir():
            continue
        payload = fold_payload(fold_dir)
        if payload is not None:
            folds.append(payload)
    folds = sorted(folds, key=lambda row: row["fold"])

    completed = [int(row["fold"]) for row in folds]
    status = "available" if len(folds) >= 2 else "insufficient_completed_folds"
    interpretation = (
        "At least two complete folds are available; mean and sample-standard-deviation "
        "summaries can be used as model-training variability evidence."
        if status == "available"
        else "Fewer than two complete folds are available. The manuscript should continue "
        "to report fold-0 as the complete full-scale training artifact and treat multi-fold "
        "training as future strengthening until additional folds finish."
    )

    payload = {
        "schema_version": "1.0",
        "status": status,
        "completed_folds": completed,
        "completed_fold_count": len(folds),
        "minimum_for_multifold_claim": 2,
        "evidence_boundary": (
            "This summary contains non-sensitive fold-level metrics only. It does not "
            "publish model weights, molecule IDs, private inputs or account data."
        ),
        "interpretation": interpretation,
        "folds": folds,
        "summary": {
            "val": summarize_split(folds, "val"),
            "future": summarize_split(folds, "future"),
        },
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(OUTPUT_JSON)
    print(OUTPUT_MD)


if __name__ == "__main__":
    main()
