"""Freeze the non-sensitive metric inputs used by manuscript table generation."""

from __future__ import annotations

import json
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
OUTPUT = PAPER_ROOT / "results" / "manuscript_source_metrics.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    payload = {
        "schema_version": "1.0",
        "evidence_boundary": (
            "Frozen non-sensitive metrics used to generate manuscript tables. "
            "The snapshot does not contain model weights, private inputs or account data."
        ),
        "dataset_summary": load_json(
            PROJECT_ROOT / "training" / "so_active_v3" / "data" / "activity_v3.summary.json"
        ),
        "train_summary": load_json(ARTIFACTS / "train_summary.json"),
        "model_metrics": load_json(ARTIFACTS / "eval_fold0.json")["metrics"],
        "conformal_report": load_json(ARTIFACTS / "conformal_report.json"),
        "random_forest": load_json(ARTIFACTS / "rf_morgan_eval.json"),
        "chemprop": load_json(ARTIFACTS / "chemprop_eval.json"),
        "previous_so_f4": load_json(ARTIFACTS / "future_sof4_eval.json")[
            "metrics_sof4_future"
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
