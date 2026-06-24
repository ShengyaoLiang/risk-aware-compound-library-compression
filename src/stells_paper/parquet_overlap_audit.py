"""Leakage audit against the exact fold-specific training rows in a Parquet dataset."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .overlap_audit import (
    canonicalize_smiles,
    file_sha256,
    iter_csv_values,
    murcko_scaffold,
    overlap_gate_status,
)


@dataclass(frozen=True)
class ParquetTrainingAudit:
    query_path: str
    query_sha256: str
    dataset_path: str
    dataset_sha256: str
    held_out_fold: int
    query_rows: int
    query_unique_canonical: int
    query_unique_scaffolds: int
    training_rows_scanned: int
    canonical_matches: int
    canonical_overlap_rate: float
    scaffold_matches: int
    scaffold_overlap_rate: float
    gate_status: str
    gate_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_dependencies() -> tuple[Any, Any]:
    try:
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError(
            "Parquet training audit requires pyarrow and RDKit. "
            "Run it with the stells backend Docker image."
        ) from exc
    if canonicalize_smiles("CC") is None:
        raise RuntimeError(
            "Parquet training audit requires pyarrow and RDKit. "
            "Run it with the stells backend Docker image."
        )
    return pc, pq


def audit_fold_training_parquet(
    *,
    query_path: Path,
    dataset_path: Path,
    held_out_fold: int,
    query_smiles_column: str | None = None,
    batch_size: int = 65_536,
) -> ParquetTrainingAudit:
    pc, pq = _require_dependencies()

    query_values = list(iter_csv_values(query_path, query_smiles_column, (query_smiles_column or "SMILES",)))
    canonical_query = {
        value
        for raw in query_values
        if (value := canonicalize_smiles(raw)) is not None
    }
    scaffold_query = {
        value
        for raw in canonical_query
        if (value := murcko_scaffold(raw)) is not None
    }
    rows_scanned, canonical_matches, scaffold_matches = scan_fold_training_matches(
        dataset_path=dataset_path,
        held_out_fold=held_out_fold,
        canonical_query=canonical_query,
        scaffold_query=scaffold_query,
        batch_size=batch_size,
        dependencies=(pc, pq),
    )

    canonical_rate = (
        len(canonical_matches) / len(canonical_query) if canonical_query else 0.0
    )
    scaffold_rate = (
        len(scaffold_matches) / len(scaffold_query) if scaffold_query else 0.0
    )
    status, reasons = overlap_gate_status(
        exact_matches=0,
        canonical_matches=len(canonical_matches),
        scaffold_overlap_rate=scaffold_rate,
    )
    return ParquetTrainingAudit(
        query_path=str(query_path),
        query_sha256=file_sha256(query_path),
        dataset_path=str(dataset_path),
        dataset_sha256=file_sha256(dataset_path),
        held_out_fold=held_out_fold,
        query_rows=len(query_values),
        query_unique_canonical=len(canonical_query),
        query_unique_scaffolds=len(scaffold_query),
        training_rows_scanned=rows_scanned,
        canonical_matches=len(canonical_matches),
        canonical_overlap_rate=canonical_rate,
        scaffold_matches=len(scaffold_matches),
        scaffold_overlap_rate=scaffold_rate,
        gate_status=status,
        gate_reasons=reasons,
    )


def scan_fold_training_matches(
    *,
    dataset_path: Path,
    held_out_fold: int,
    canonical_query: set[str],
    scaffold_query: set[str],
    batch_size: int = 65_536,
    dependencies: tuple[Any, Any] | None = None,
) -> tuple[int, set[str], set[str]]:
    pc, pq = dependencies or _require_dependencies()
    canonical_matches: set[str] = set()
    scaffold_matches: set[str] = set()
    rows_scanned = 0

    parquet = pq.ParquetFile(dataset_path)
    required = {"smiles", "scaffold", "is_future", "cv_fold"}
    missing = required.difference(parquet.schema.names)
    if missing:
        raise ValueError(f"dataset is missing required columns: {sorted(missing)}")

    for batch in parquet.iter_batches(
        columns=["smiles", "scaffold", "is_future", "cv_fold"],
        batch_size=batch_size,
    ):
        training_mask = pc.and_(
            pc.invert(batch.column("is_future")),
            pc.not_equal(batch.column("cv_fold"), held_out_fold),
        )
        selected = batch.filter(training_mask)
        rows_scanned += selected.num_rows
        for value in selected.column("smiles").to_pylist():
            if value in canonical_query:
                canonical_matches.add(value)
        for value in selected.column("scaffold").to_pylist():
            if value in scaffold_query:
                scaffold_matches.add(value)
    return rows_scanned, canonical_matches, scaffold_matches


def report_markdown(report: ParquetTrainingAudit) -> str:
    return "\n".join(
        [
            "# Fold-specific Training Overlap Audit",
            "",
            f"- Query: `{report.query_path}`",
            f"- Training dataset: `{report.dataset_path}`",
            f"- Held-out validation fold: {report.held_out_fold}",
            f"- Training rows scanned: {report.training_rows_scanned}",
            f"- Gate status: **{report.gate_status}**",
            f"- Gate reasons: {'; '.join(report.gate_reasons)}",
            "",
            "| Audit | Matches | Query unique | Overlap rate |",
            "| --- | ---: | ---: | ---: |",
            f"| Standardized structure | {report.canonical_matches} | "
            f"{report.query_unique_canonical} | {report.canonical_overlap_rate:.2%} |",
            f"| Bemis-Murcko scaffold | {report.scaffold_matches} | "
            f"{report.query_unique_scaffolds} | {report.scaffold_overlap_rate:.2%} |",
            "",
            "A non-zero scaffold overlap does not by itself prove label leakage, but it "
            "requires a scaffold-disjoint sensitivity analysis for strong external "
            "generalization claims.",
            "",
        ]
    )
