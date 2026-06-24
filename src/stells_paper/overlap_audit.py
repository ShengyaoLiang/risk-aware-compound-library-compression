"""Streaming molecular overlap audits with optional RDKit normalization."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence


DEFAULT_SMILES_COLUMNS = (
    "standardized_smiles",
    "canonical_smiles",
    "SMILES",
    "smiles",
    "mol",
)


def stable_text_key(value: str) -> str:
    return "".join(str(value or "").split())


@lru_cache(maxsize=1)
def _load_rdkit() -> tuple[object | None, object | None]:
    try:
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold

        return Chem, MurckoScaffold
    except Exception:
        return None, None


def canonicalize_smiles(smiles: str) -> str | None:
    chem, _ = _load_rdkit()
    if chem is None:
        return None
    mol = chem.MolFromSmiles(smiles)
    return chem.MolToSmiles(mol, canonical=True, isomericSmiles=True) if mol is not None else None


def murcko_scaffold(smiles: str) -> str | None:
    chem, murcko = _load_rdkit()
    if chem is None or murcko is None:
        return None
    mol = chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    scaffold = murcko.GetScaffoldForMol(mol)
    return chem.MolToSmiles(scaffold, canonical=True, isomericSmiles=False) if scaffold is not None else None


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def detect_column(fieldnames: Sequence[str] | None, candidates: Sequence[str]) -> str:
    fields = list(fieldnames or [])
    for candidate in candidates:
        if candidate in fields:
            return candidate
    lower = {field.lower(): field for field in fields}
    for candidate in candidates:
        match = lower.get(candidate.lower())
        if match:
            return match
    raise ValueError(f"none of columns {list(candidates)} found in {fields}")


def iter_csv_values(path: Path, column: str | None, candidates: Sequence[str]) -> Iterator[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        selected = column or detect_column(reader.fieldnames, candidates)
        for row in reader:
            value = stable_text_key(row.get(selected, ""))
            if value:
                yield value


@dataclass(frozen=True)
class ReferenceAudit:
    name: str
    path: str
    sha256: str
    rows_scanned: int
    unique_reference_values: int
    exact_matches: int
    exact_overlap_rate: float
    canonical_matches: int | None
    canonical_overlap_rate: float | None
    scaffold_matches: int | None
    scaffold_overlap_rate: float | None
    gate_status: str
    gate_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, str | int | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class AuditReport:
    query_path: str
    query_sha256: str
    query_rows: int
    query_unique_exact: int
    query_unique_canonical: int | None
    query_unique_scaffolds: int | None
    rdkit_available: bool
    references: tuple[ReferenceAudit, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["references"] = [item.to_dict() for item in self.references]
        return payload


def _optional_keys(values: Iterable[str], transform: Callable[[str], str | None]) -> set[str] | None:
    transformed: set[str] = set()
    attempted = False
    for value in values:
        attempted = True
        key = transform(value)
        if key:
            transformed.add(key)
    return transformed if attempted and transformed else None


def audit_reference(
    *,
    name: str,
    path: Path,
    query_exact: set[str],
    query_canonical: set[str] | None,
    query_scaffolds: set[str] | None,
    smiles_column: str | None = None,
    scaffold_column: str | None = None,
) -> ReferenceAudit:
    rows_scanned = 0
    unique_reference: set[str] = set()
    exact_matches: set[str] = set()
    canonical_matches: set[str] = set()
    scaffold_matches: set[str] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        selected_smiles = smiles_column or detect_column(reader.fieldnames, DEFAULT_SMILES_COLUMNS)
        selected_scaffold = scaffold_column
        if selected_scaffold is None and reader.fieldnames and "scaffold" in reader.fieldnames:
            selected_scaffold = "scaffold"

        for row in reader:
            rows_scanned += 1
            raw = stable_text_key(row.get(selected_smiles, ""))
            if not raw:
                continue
            unique_reference.add(raw)
            if raw in query_exact:
                exact_matches.add(raw)

            if query_canonical is not None:
                canonical = canonicalize_smiles(raw)
                if canonical in query_canonical:
                    canonical_matches.add(canonical)

            if query_scaffolds is not None:
                scaffold = stable_text_key(row.get(selected_scaffold, "")) if selected_scaffold else murcko_scaffold(raw)
                if scaffold in query_scaffolds:
                    scaffold_matches.add(scaffold)

    query_exact_count = len(query_exact)
    query_canonical_count = len(query_canonical) if query_canonical is not None else 0
    query_scaffold_count = len(query_scaffolds) if query_scaffolds is not None else 0
    gate_status, gate_reasons = overlap_gate_status(
        exact_matches=len(exact_matches),
        canonical_matches=len(canonical_matches) if query_canonical is not None else None,
        scaffold_overlap_rate=(
            len(scaffold_matches) / query_scaffold_count if query_scaffold_count else 0.0
        )
        if query_scaffolds is not None
        else None,
    )
    return ReferenceAudit(
        name=name,
        path=str(path),
        sha256=file_sha256(path),
        rows_scanned=rows_scanned,
        unique_reference_values=len(unique_reference),
        exact_matches=len(exact_matches),
        exact_overlap_rate=len(exact_matches) / query_exact_count if query_exact_count else 0.0,
        canonical_matches=len(canonical_matches) if query_canonical is not None else None,
        canonical_overlap_rate=(
            len(canonical_matches) / query_canonical_count if query_canonical_count else 0.0
        )
        if query_canonical is not None
        else None,
        scaffold_matches=len(scaffold_matches) if query_scaffolds is not None else None,
        scaffold_overlap_rate=(
            len(scaffold_matches) / query_scaffold_count if query_scaffold_count else 0.0
        )
        if query_scaffolds is not None
        else None,
        gate_status=gate_status,
        gate_reasons=gate_reasons,
    )


def overlap_gate_status(
    *,
    exact_matches: int,
    canonical_matches: int | None,
    scaffold_overlap_rate: float | None,
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if exact_matches:
        reasons.append(f"{exact_matches} exact structure matches detected")
    if canonical_matches:
        reasons.append(f"{canonical_matches} standardized structure matches detected")
    if reasons:
        return "failed", tuple(reasons)

    missing: list[str] = []
    if canonical_matches is None:
        missing.append("standardized-structure audit not run")
    if scaffold_overlap_rate is None:
        missing.append("scaffold audit not run")
    if missing:
        return "incomplete", tuple(missing)
    return "passed", ("no exact or standardized structure overlap detected",)


def run_overlap_audit(
    *,
    query_path: Path,
    references: Sequence[tuple[str, Path]],
    query_smiles_column: str | None = None,
    reference_smiles_column: str | None = None,
) -> AuditReport:
    query_values = list(iter_csv_values(query_path, query_smiles_column, DEFAULT_SMILES_COLUMNS))
    query_exact = set(query_values)
    chem, _ = _load_rdkit()
    query_canonical = _optional_keys(query_exact, canonicalize_smiles) if chem is not None else None
    query_scaffolds = _optional_keys(query_exact, murcko_scaffold) if chem is not None else None

    audits = tuple(
        audit_reference(
            name=name,
            path=path,
            query_exact=query_exact,
            query_canonical=query_canonical,
            query_scaffolds=query_scaffolds,
            smiles_column=reference_smiles_column,
        )
        for name, path in references
    )
    return AuditReport(
        query_path=str(query_path),
        query_sha256=file_sha256(query_path),
        query_rows=len(query_values),
        query_unique_exact=len(query_exact),
        query_unique_canonical=len(query_canonical) if query_canonical is not None else None,
        query_unique_scaffolds=len(query_scaffolds) if query_scaffolds is not None else None,
        rdkit_available=chem is not None,
        references=audits,
    )


def report_markdown(report: AuditReport) -> str:
    lines = [
        "# Molecular Overlap Audit",
        "",
        f"- Query: `{report.query_path}`",
        f"- Query SHA256: `{report.query_sha256}`",
        f"- Query rows: {report.query_rows}",
        f"- Unique exact structures: {report.query_unique_exact}",
        f"- RDKit available: {report.rdkit_available}",
        "",
        "| Reference | Gate | Rows scanned | Exact matches | Exact overlap | Canonical overlap | Scaffold overlap |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in report.references:
        canonical = f"{item.canonical_overlap_rate:.2%}" if item.canonical_overlap_rate is not None else "not run"
        scaffold = f"{item.scaffold_overlap_rate:.2%}" if item.scaffold_overlap_rate is not None else "not run"
        lines.append(
            f"| {item.name} | {item.gate_status} | {item.rows_scanned} | {item.exact_matches} | "
            f"{item.exact_overlap_rate:.2%} | {canonical} | {scaffold} |"
        )
        lines.append(f"|  | Reasons: {'; '.join(item.gate_reasons)} |  |  |  |  |  |")
    lines.extend(
        [
            "",
            "## Interpretation Gate",
            "",
            "Any non-zero exact or standardized-structure overlap must be removed or "
            "explicitly disclosed before the dataset is used as independent external evidence.",
            "",
        ]
    )
    return "\n".join(lines)
