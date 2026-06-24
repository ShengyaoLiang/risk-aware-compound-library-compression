"""Build a concise, machine-readable status matrix for the paper evidence."""

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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def artifact_ref(path: Path) -> str:
    """Return a portable project-relative artifact reference."""

    for root in (PAPER_ROOT, PROJECT_ROOT):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            continue
    return path.name


def main() -> None:
    bace_audit = load_json(PAPER_ROOT / "results" / "bace_fold0_training_overlap.json")
    bace_strict = load_json(PAPER_ROOT / "results" / "bace_overlap_controlled_eval.json")
    egfr_strict = load_json(PAPER_ROOT / "results" / "egfr_overlap_controlled_eval.json")
    operational = load_json(PAPER_ROOT / "results" / "operational_validation.json")
    multifold_path = PAPER_ROOT / "results" / "multifold_training_summary.json"
    multifold = load_json(multifold_path) if multifold_path.exists() else None
    decision_replay_path = PAPER_ROOT / "results" / "bace_scaffold_decision_replay.json"
    decision_replay_available = decision_replay_path.exists()
    multifold_available = bool(multifold and multifold.get("status") == "available")
    matrix = {
        "schema_version": "1.0",
        "submission_readiness": "ready_after_author_confirmation_and_final_review",
        "evidence": [
            {
                "id": "chembl36_internal_val",
                "role": "internal_validation",
                "status": "available",
                "artifact": artifact_ref(ARTIFACTS / "eval_fold0.json"),
                "limitations": [
                    "single trained fold currently reported",
                    "bootstrap intervals exclude model-retraining variability",
                ],
            },
            {
                "id": "chembl36_future",
                "role": "temporal_holdout",
                "status": "available",
                "artifact": artifact_ref(ARTIFACTS / "eval_fold0.json"),
                "limitations": [
                    "single trained fold currently reported",
                    "bootstrap intervals exclude model-retraining variability",
                ],
            },
            {
                "id": "multifold_training_variability",
                "role": "training_variability",
                "status": "available" if multifold_available else "insufficient_completed_folds",
                "artifact": artifact_ref(multifold_path),
                "rows": multifold.get("completed_fold_count") if multifold else 0,
                "limitations": (
                    [
                        "mean and sample-standard-deviation summaries use completed folds only",
                        "future holdout rows are shared across folds",
                    ]
                    if multifold_available
                    else [
                        "only fold 0 is complete at this snapshot",
                        "fold 1 and fold 2 should be completed before making a multi-fold claim",
                    ]
                ),
            },
            {
                "id": "bace1513_full",
                "role": "external_source_historical_result",
                "status": "overlap_detected",
                "standardized_structure_overlap": bace_audit["canonical_overlap_rate"],
                "limitations": [
                    "not valid as strict independent evidence without overlap removal",
                    "full-set metrics retained for provenance only",
                ],
            },
            {
                "id": "bace1513_structure_disjoint",
                "role": "external_structure_disjoint",
                "status": "available",
                "rows": bace_strict["subsets"]["structure_disjoint"]["rows"],
                "limitations": [
                    "scaffold overlap remains",
                    "bootstrap intervals exclude model-retraining variability",
                ],
            },
            {
                "id": "bace1513_scaffold_disjoint",
                "role": "external_scaffold_disjoint_sensitivity",
                "status": "available",
                "rows": bace_strict["subsets"]["scaffold_disjoint"]["rows"],
                "limitations": [
                    "bootstrap intervals exclude model-retraining variability",
                ],
            },
            {
                "id": "egfr_chembl203_full_replay",
                "role": "workflow_demonstration",
                "status": "overlap_detected",
                "standardized_structure_overlap": (
                    egfr_strict["structure_matches"] / egfr_strict["original_rows"]
                ),
                "limitations": [
                    "same ChEMBL 36 source family as the activity training data",
                    "full-set result retained for workflow provenance only",
                    "excluded from independent external-generalization claims",
                ],
            },
            {
                "id": "egfr_chembl203_structure_disjoint",
                "role": "target_specific_workflow_sensitivity",
                "status": "available_with_limitations",
                "rows": egfr_strict["subsets"]["structure_disjoint"]["rows"],
                "limitations": [
                    "scaffold overlap remains",
                    "same-source target-specific replay, not independent external validation",
                    "bootstrap intervals exclude model-retraining variability",
                ],
            },
            {
                "id": "egfr_chembl203_scaffold_disjoint",
                "role": "target_specific_workflow_sensitivity",
                "status": "available_with_limitations",
                "rows": egfr_strict["subsets"]["scaffold_disjoint"]["rows"],
                "limitations": [
                    "same-source target-specific replay, not independent external validation",
                    "bootstrap intervals exclude model-retraining variability",
                ],
            },
            {
                "id": "batch_ranking_seed2026",
                "role": "budget_constrained_ranking",
                "status": "available",
                "artifact": artifact_ref(ARTIFACTS / "batch_ranking_eval_seed2026.json"),
                "limitations": [
                    "legacy full-set BACE batch rows are not used for strict external claims",
                ],
            },
            {
                "id": "multiseed_virtual_batches",
                "role": "budget_constrained_ranking_sensitivity",
                "status": "available",
                "artifact": artifact_ref(PAPER_ROOT / "results" / "statistical_results.json"),
                "limitations": [
                    "seed variability reflects library shuffling only, not model retraining",
                ],
            },
            {
                "id": "paired_bootstrap_intervals",
                "role": "fixed_prediction_uncertainty",
                "status": "available",
                "artifact": artifact_ref(PAPER_ROOT / "results" / "statistical_results.json"),
                "limitations": [
                    "intervals are over frozen prediction rows and exclude retraining variability",
                ],
            },
            {
                "id": "baseline_sanity_checks",
                "role": "model_context",
                "status": "available_with_limitations",
                "artifact": artifact_ref(ARTIFACTS),
                "limitations": [
                    "random forest and Chemprop baselines use sampled ChEMBL 36 splits",
                    "not full Future all-row same-protocol benchmarks",
                    "not a final unified full-scale benchmark suite",
                ],
            },
            {
                "id": "decision_layer_replay",
                "role": "risk_aware_ranking",
                "status": (
                    "available_with_limitations"
                    if decision_replay_available
                    else "available_with_pending_strict_subset"
                ),
                "artifact": artifact_ref(decision_replay_path) if decision_replay_available else None,
                "limitations": [
                    "single replay seed",
                    "not uniformly superior to activity-only ranking",
                    *(
                        ["strict BACE replay uses one 100-molecule virtual batch"]
                        if decision_replay_available
                        else ["overlap-controlled BACE decision replay pending"]
                    ),
                ],
            },
            {
                "id": "operational_ab_controls",
                "role": "budgeted_selection_controls",
                "status": "available_with_limitations",
                "artifact": artifact_ref(PAPER_ROOT / "results" / "operational_validation.json"),
                "rows": operational["ab_control"]["rows"],
                "limitations": [
                    "retrospective simulation on frozen BACE predictions",
                    "random and scaffold-diversity controls use five selection seeds",
                    "Top-10 overlap is reported as a strategy-difference display",
                    "does not establish project-specific wet-lab gains",
                ],
            },
            {
                "id": "released_package_scope",
                "role": "public_reproducibility_boundary",
                "status": "available_with_scope_limits",
                "artifact": "paper/build/stells_paper_github_release.zip",
                "limitations": [
                    "complete ChEMBL-derived training assets are not published",
                    "full train/validation ID lists are not published",
                    "released scripts reproduce manuscript tables from frozen non-sensitive artifacts",
                ],
            },
            {
                "id": "failure_case_analysis",
                "role": "scope_boundary_analysis",
                "status": "available",
                "artifact": artifact_ref(PAPER_ROOT / "results" / "operational_validation.json"),
                "rows": len(operational["error_cases"]),
                "limitations": [
                    "small descriptive sample of high-ranked inactive molecules",
                    "not a complete mechanistic error taxonomy",
                ],
            },
            {
                "id": "assay_budget_accounting",
                "role": "illustrative_cost_framing",
                "status": "available_with_limitations",
                "artifact": artifact_ref(PAPER_ROOT / "results" / "operational_validation.json"),
                "limitations": [
                    "illustrative accounting only",
                    "requires external calibration before project-specific savings claims",
                ],
            },
            {
                "id": "prospective_wet_lab",
                "role": "prospective_validation",
                "status": "missing",
                "limitations": [
                    "required before claiming project-specific hit-rate or cost gains",
                    "reported as a limitation, not required for an arXiv methods preprint",
                ],
            },
        ],
        "future_strengthening": [
            "run all baselines at full scale under identical splits and preprocessing",
            "complete fold-1 and fold-2 full training to report 2-3 fold variability",
            "add externally blinded historical replay or prospective wet-lab validation",
        ],
        "submission_blockers": [
            "confirm final author metadata, license, and arXiv category in the arXiv web form",
            "complete final visual review and obtain an independent domain review",
        ],
    }
    output_json = PAPER_ROOT / "results" / "evidence_matrix.json"
    output_md = PAPER_ROOT / "results" / "evidence_matrix.md"
    output_json.write_text(json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Paper Evidence Matrix",
        "",
        "| Evidence | Role | Status | Main limitation |",
        "| --- | --- | --- | --- |",
    ]
    for row in matrix["evidence"]:
        limitations = "; ".join(row.get("limitations", [])) or "none recorded"
        lines.append(
            f"| `{row['id']}` | {row['role']} | **{row['status']}** | {limitations} |"
        )
    lines.extend(["", "## Submission Blockers", ""])
    lines.extend(f"- {item}" for item in matrix["submission_blockers"])
    lines.extend(["", "## Future Strengthening", ""])
    lines.extend(f"- {item}" for item in matrix["future_strengthening"])
    lines.append("")
    output_md.write_text("\n".join(lines), encoding="utf-8")
    print(output_json)
    print(output_md)


if __name__ == "__main__":
    main()
