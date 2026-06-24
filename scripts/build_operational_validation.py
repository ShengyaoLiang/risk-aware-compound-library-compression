"""Build operational-validation artifacts for the manuscript.

The script intentionally uses frozen prediction artifacts. It does not retrain
models and does not turn retrospective replay into prospective evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parents[1]
RESULTS = PAPER_ROOT / "results"


def _deps() -> tuple[Any, Any]:
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("This script requires numpy and pandas.") from exc
    return np, pd


def _load_bace():
    _, pd = _deps()
    frame = pd.read_csv(RESULTS / "bace_scaffold_disjoint.csv")
    frame = frame.reset_index(drop=True)
    frame["row_id"] = frame.index
    frame["active"] = frame["class_bin"].astype(int)
    return frame


def _metrics(frame, selected_ids: list[int]) -> dict[str, float]:
    selected = frame.loc[selected_ids]
    return {
        "n": int(len(selected)),
        "hit_rate": round(float(selected["active"].mean()), 4),
        "mean_pIC50": round(float(selected["pIC50_true"].mean()), 4),
        "mean_pred_pIC50": round(float(selected["pred_pIC50"].mean()), 4),
        "unique_scaffold_rate": round(float(selected["scaffold"].nunique() / len(selected)), 4),
    }


def _random_ids(frame, n: int, seed: int) -> list[int]:
    np, _ = _deps()
    rng = np.random.default_rng(seed)
    return rng.choice(frame.index.to_numpy(), size=n, replace=False).tolist()


def _diverse_ids(frame, n: int, seed: int) -> list[int]:
    """Select a scaffold-diverse set without using labels or predicted activity.

    One randomized representative is chosen per scaffold first; if more rows are
    needed, the remaining rows are filled in a second deterministic random pass.
    """

    np, _ = _deps()
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    for _, group in frame.groupby("scaffold", sort=False):
        selected.append(int(rng.choice(group.index.to_numpy())))
    rng.shuffle(selected)
    selected = selected[:n]
    if len(selected) < n:
        remaining = [int(idx) for idx in frame.index if int(idx) not in set(selected)]
        selected.extend(rng.choice(remaining, size=n - len(selected), replace=False).tolist())
    return selected


def _system_ids(frame, n: int) -> list[int]:
    return frame.sort_values("pred_pIC50", ascending=False).head(n).index.astype(int).tolist()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def build_ab_control(frame) -> dict[str, Any]:
    cutoffs = [10, 50, 100]
    seeds = [7, 42, 2026, 3407, 10007]
    rows: list[dict[str, Any]] = []
    for n in cutoffs:
        system = _metrics(frame, _system_ids(frame, n))
        rows.append({"strategy": "system_activity_order", "top_n": n, **system})
        for name, selector in (
            ("random", _random_ids),
            ("scaffold_diversity", _diverse_ids),
        ):
            seed_metrics = [_metrics(frame, selector(frame, n, seed)) for seed in seeds]
            rows.append(
                {
                    "strategy": name,
                    "top_n": n,
                    "seeds": seeds,
                    "hit_rate_mean": round(
                        sum(row["hit_rate"] for row in seed_metrics) / len(seed_metrics), 4
                    ),
                    "hit_rate_sd": round(
                        _sample_sd([row["hit_rate"] for row in seed_metrics]), 4
                    ),
                    "mean_pIC50_mean": round(
                        sum(row["mean_pIC50"] for row in seed_metrics) / len(seed_metrics), 4
                    ),
                    "mean_pIC50_sd": round(
                        _sample_sd([row["mean_pIC50"] for row in seed_metrics]), 4
                    ),
                    "unique_scaffold_rate_mean": round(
                        sum(row["unique_scaffold_rate"] for row in seed_metrics)
                        / len(seed_metrics),
                        4,
                    ),
                }
            )
    return {"dataset": "BACE scaffold-disjoint", "rows": int(len(frame)), "results": rows}


def _sample_sd(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((value - mean) ** 2 for value in values) / (len(values) - 1)) ** 0.5


def build_error_cases(frame) -> list[dict[str, Any]]:
    ranked = frame.sort_values("pred_pIC50", ascending=False).copy()
    ranked["rank"] = range(1, len(ranked) + 1)
    inactive_top = ranked[ranked["active"] == 0].head(3)
    scaffold_counts = Counter(frame["scaffold"])
    cases = []
    for _, row in inactive_top.iterrows():
        cases.append(
            {
                "case_id": f"BACE_SD_{int(row['rank']):03d}",
                "rank": int(row["rank"]),
                "smiles_hash": _hash_text(row["canonical_smiles"]),
                "scaffold_hash": _hash_text(row["scaffold"]),
                "pIC50_true": round(float(row["pIC50_true"]), 4),
                "pred_pIC50": round(float(row["pred_pIC50"]), 4),
                "scaffold_frequency_in_subset": int(scaffold_counts[row["scaffold"]]),
                "interpretation": (
                    "High predicted score with an inactive label in the strict "
                    "scaffold-disjoint subset. The case is reported as a scope "
                    "boundary for retrospective ranking and as a candidate for "
                    "domain/risk review, not as evidence of a failed system design."
                ),
            }
        )
    return cases


def build_strategy_summary(frame) -> dict[str, Any]:
    activity_ids = set(_system_ids(frame, 10))
    diverse_ids = set(_diverse_ids(frame, 10, 2026))
    random_ids = set(_random_ids(frame, 10, 2026))
    strategies = {
        "activity_order": activity_ids,
        "scaffold_diversity": diverse_ids,
        "random_seed2026": random_ids,
    }
    rows = []
    for left_name, left_ids in strategies.items():
        for right_name, right_ids in strategies.items():
            if left_name >= right_name:
                continue
            union = left_ids | right_ids
            rows.append(
                {
                    "left": left_name,
                    "right": right_name,
                    "top10_overlap": len(left_ids & right_ids),
                    "top10_jaccard": round(len(left_ids & right_ids) / len(union), 4),
                }
            )
    return {"dataset": "BACE scaffold-disjoint", "results": rows}


def build_cost_case(frame) -> dict[str, Any]:
    active_total = int(frame["active"].sum())
    top_10_percent = max(1, int(round(len(frame) * 0.10)))
    top_ids = _system_ids(frame, top_10_percent)
    selected = frame.loc[top_ids]
    captured = int(selected["active"].sum())
    return {
        "example_library_size": 10000,
        "compression_fraction": 0.10,
        "screened_after_compression": 1000,
        "formula": "first_round_tests = library_size * compression_fraction; avoided_tests = library_size - first_round_tests",
        "bace_scaffold_disjoint_reference": {
            "rows": int(len(frame)),
            "active_total": active_total,
            "top_10_percent_rows": top_10_percent,
            "active_captured_at_top_10_percent": captured,
            "recall_at_top_10_percent": round(captured / active_total, 4),
        },
        "boundary": (
            "The calculation is an assay-budget framing example. It should be "
            "calibrated with external project labels before being used for a "
            "project-specific cost or hit-rate claim."
        ),
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Operational Validation Summary",
        "",
        "Frozen artifacts only; no model retraining is performed here.",
        "",
        "## Random and Diversity Baselines",
        "",
        "| Strategy | Top N | Hit rate | Mean pIC50 | Scaffold diversity |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["ab_control"]["results"]:
        if row["strategy"] == "system_activity_order":
            hit = f"{row['hit_rate']:.4f}"
            mean = f"{row['mean_pIC50']:.4f}"
            diversity = f"{row['unique_scaffold_rate']:.4f}"
        else:
            hit = f"{row['hit_rate_mean']:.4f} +/- {row['hit_rate_sd']:.4f}"
            mean = f"{row['mean_pIC50_mean']:.4f} +/- {row['mean_pIC50_sd']:.4f}"
            diversity = f"{row['unique_scaffold_rate_mean']:.4f}"
        lines.append(f"| {row['strategy']} | {row['top_n']} | {hit} | {mean} | {diversity} |")

    lines.extend(["", "## High-ranked Inactive Scope-boundary Cases", ""])
    for case in payload["error_cases"]:
        lines.append(
            f"- `{case['case_id']}` rank {case['rank']}: true pIC50 "
            f"{case['pIC50_true']:.4f}, predicted {case['pred_pIC50']:.4f}, "
            f"scaffold frequency {case['scaffold_frequency_in_subset']}."
        )

    lines.extend(["", "## Cost-framing Example", ""])
    case = payload["cost_case"]
    ref = case["bace_scaffold_disjoint_reference"]
    lines.append(
        f"- A 10,000-compound library compressed to Top 10% yields "
        f"{case['screened_after_compression']} first-round tests and avoids "
        f"{case['example_library_size'] - case['screened_after_compression']} "
        "initial tests."
    )
    lines.append(
        f"- In the BACE scaffold-disjoint reference subset, Top 10% captured "
        f"{ref['active_captured_at_top_10_percent']}/{ref['active_total']} "
        f"active labels (recall {ref['recall_at_top_10_percent']:.4f})."
    )
    lines.append(f"- Boundary: {case['boundary']}")
    lines.extend(["", "## Top-10 Strategy Overlap", ""])
    lines.append("| Strategy A | Strategy B | Overlap | Jaccard |")
    lines.append("| --- | --- | ---: | ---: |")
    for row in payload["strategy_summary"]["results"]:
        lines.append(
            f"| {row['left']} | {row['right']} | "
            f"{row['top10_overlap']} | {row['top10_jaccard']:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    frame = _load_bace()
    payload = {
        "schema_version": "1.0",
        "source": "results/bace_scaffold_disjoint.csv",
        "ab_control": build_ab_control(frame),
        "error_cases": build_error_cases(frame),
        "strategy_summary": build_strategy_summary(frame),
        "cost_case": build_cost_case(frame),
        "decision_matrix": [
            {
                "activity": "high",
                "interval_or_domain": "narrow_interval_or_in_domain",
                "recommended_action": "advance_for_first_review",
            },
            {
                "activity": "high",
                "interval_or_domain": "wide_interval_or_out_of_domain",
                "recommended_action": "advance_only_with_risk_review",
            },
            {
                "activity": "moderate_or_low",
                "interval_or_domain": "narrow_interval_or_in_domain",
                "recommended_action": "reserve_or_use_as_diversity_control",
            },
            {
                "activity": "moderate_or_low",
                "interval_or_domain": "wide_interval_or_out_of_domain",
                "recommended_action": "defer_unless_project_context_supports_it",
            },
        ],
    }
    (RESULTS / "operational_validation.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (RESULTS / "operational_validation.md").write_text(
        markdown(payload),
        encoding="utf-8",
    )
    print(RESULTS / "operational_validation.json")
    print(RESULTS / "operational_validation.md")


if __name__ == "__main__":
    main()
