"""Evaluate EGFR workflow replay after fold-specific training-overlap control."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER_ROOT / "src"))

from stells_paper.metrics import (
    binary_ranking_metrics,
    roc_auc,
    spearman_correlation,
)
from stells_paper.overlap_audit import canonicalize_smiles, file_sha256, murcko_scaffold
from stells_paper.parquet_overlap_audit import scan_fold_training_matches


FRACTIONS = (0.001, 0.005, 0.01, 0.05, 0.10, 0.20)


def _float(value: Any, label: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite value in {label}")
    return parsed


def load_hidden_labels(path: Path) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            canonical = canonicalize_smiles(row.get("SMILES", ""))
            if canonical is None:
                continue
            label = {
                "canonical_smiles": canonical,
                "true_label": int(float(row["True_Label"])),
                "true_pchembl": _float(row["Derived_pChEMBL"], "Derived_pChEMBL"),
                "molecule_id": row.get("Molecule_ID", ""),
                "source_chembl_id": row.get("Source_CHEMBL_ID", ""),
            }
            previous = labels.get(canonical)
            if previous is not None and previous != label:
                raise ValueError(
                    f"conflicting hidden labels for canonical structure: {canonical}"
                )
            labels[canonical] = label
    return labels


def load_batch_predictions(
    *,
    results_db: Path,
    batch_id: str,
    labels_by_canonical: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    query = """
        select seq, smiles, standardized_smiles, has_error, pIC50, similarity_score
        from results
        where batch_id=?
        order by seq
    """
    with sqlite3.connect(results_db) as connection:
        connection.row_factory = sqlite3.Row
        for record in connection.execute(query, (batch_id,)):
            if int(record["has_error"] or 0):
                continue
            input_canonical = canonicalize_smiles(record["smiles"] or "")
            standardized_canonical = canonicalize_smiles(
                record["standardized_smiles"] or record["smiles"] or ""
            )
            if standardized_canonical is None:
                continue

            # Hidden labels correspond to the uploaded input. Training-overlap
            # control must still use the structure produced by preprocessing.
            label = (
                labels_by_canonical.get(input_canonical)
                if input_canonical is not None
                else None
            ) or labels_by_canonical.get(standardized_canonical)
            if label is None:
                continue

            score = _float(record["pIC50"], "pIC50")
            scaffold = murcko_scaffold(standardized_canonical) or ""
            rows.append(
                {
                    "seq": int(record["seq"]),
                    "canonical_smiles": standardized_canonical,
                    "scaffold": scaffold,
                    "true_label": int(label["true_label"]),
                    "true_pchembl": float(label["true_pchembl"]),
                    "pred_pIC50": score,
                    "similarity_score": (
                        None
                        if record["similarity_score"] is None
                        else float(record["similarity_score"])
                    ),
                    "molecule_id": label["molecule_id"],
                    "source_chembl_id": label["source_chembl_id"],
                }
            )
    return rows


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = sorted(rows, key=lambda row: row["pred_pIC50"], reverse=True)
    labels = [int(row["true_label"]) for row in ranked]
    scores = [float(row["pred_pIC50"]) for row in ranked]
    observed = [float(row["true_pchembl"]) for row in ranked]
    return {
        "rows": len(ranked),
        "positives": sum(labels),
        "prevalence": sum(labels) / len(labels) if labels else 0.0,
        "roc_auc": roc_auc(labels, scores) if labels else 0.0,
        "spearman_true_pchembl_vs_proxy": (
            spearman_correlation(observed, scores) if len(ranked) >= 2 else 0.0
        ),
        "ranking": {
            f"top_{fraction:g}": binary_ranking_metrics(
                labels, fraction=fraction
            ).to_dict()
            for fraction in FRACTIONS
        },
    }


def write_compact_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "molecule_id",
        "source_chembl_id",
        "canonical_smiles",
        "scaffold",
        "true_label",
        "true_pchembl",
        "pred_pIC50",
        "similarity_score",
    ]
    ranked = sorted(rows, key=lambda row: row["pred_pIC50"], reverse=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in columns} for row in ranked)


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Overlap-controlled EGFR/CHEMBL203 Workflow Replay",
        "",
        f"- Original matched rows: {payload['original_rows']}",
        f"- Fold-0 training rows scanned: {payload['training_rows_scanned']}",
        f"- Removed standardized-structure matches: {payload['structure_matches']}",
        f"- Training-overlapping query scaffolds: {payload['scaffold_matches']}",
        "",
        "| Evaluation subset | Rows | Prevalence | ROC AUC | Spearman | EF@1% | EF@5% | EF@10% | Hit@10% | NDCG@10% |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, label in (
        ("full", "Original full EGFR replay"),
        ("structure_disjoint", "Standardized-structure disjoint"),
        ("scaffold_disjoint", "Bemis-Murcko scaffold disjoint"),
    ):
        result = payload["subsets"][key]
        ranking = result["ranking"]
        top10 = ranking["top_0.1"]
        lines.append(
            f"| {label} | {result['rows']} | {result['prevalence']:.2%} | "
            f"{result['roc_auc']:.4f} | "
            f"{result['spearman_true_pchembl_vs_proxy']:.4f} | "
            f"{ranking['top_0.01']['enrichment_factor']:.4f} | "
            f"{ranking['top_0.05']['enrichment_factor']:.4f} | "
            f"{top10['enrichment_factor']:.4f} | "
            f"{top10['hit_rate']:.2%} | {top10['ndcg']:.4f} |"
        )
    lines.extend(
        [
            "",
            "This replay is built from ChEMBL EGFR/CHEMBL203 records. Even after "
            "overlap removal, it should be reported as a target-specific workflow "
            "sensitivity analysis, not as fully independent external validation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-db", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--training-dataset", type=Path, required=True)
    parser.add_argument("--held-out-fold", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    labels = load_hidden_labels(args.labels)
    rows = load_batch_predictions(
        results_db=args.results_db,
        batch_id=args.batch_id,
        labels_by_canonical=labels,
    )
    if not rows:
        raise RuntimeError("no EGFR prediction rows matched hidden labels")
    if len(rows) != len(labels):
        raise RuntimeError(
            "incomplete EGFR replay match: "
            f"{len(rows)} platform rows matched {len(labels)} hidden labels"
        )
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
            "results_db_path": str(args.results_db.resolve()),
            "results_db_sha256": file_sha256(args.results_db),
            "batch_id": args.batch_id,
            "labels_path": str(args.labels.resolve()),
            "labels_sha256": file_sha256(args.labels),
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
    write_compact_csv(output_dir / "egfr_full_scored.csv", rows)
    write_compact_csv(output_dir / "egfr_structure_disjoint.csv", structure_disjoint)
    write_compact_csv(output_dir / "egfr_scaffold_disjoint.csv", scaffold_disjoint)
    (output_dir / "egfr_overlap_controlled_eval.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "egfr_overlap_controlled_eval.md").write_text(
        markdown(payload),
        encoding="utf-8",
    )
    print(output_dir / "egfr_overlap_controlled_eval.json")
    print(output_dir / "egfr_overlap_controlled_eval.md")


if __name__ == "__main__":
    main()
