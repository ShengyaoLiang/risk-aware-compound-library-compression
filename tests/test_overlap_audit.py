from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path


PAPER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER_ROOT / "src"))

from stells_paper.overlap_audit import overlap_gate_status, run_overlap_audit


def write_csv(path: Path, field: str, values: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field])
        writer.writeheader()
        writer.writerows([{field: value} for value in values])


class OverlapAuditTests(unittest.TestCase):
    def test_exact_overlap_is_streamed_and_counted(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            query = root / "query.csv"
            reference = root / "reference.csv"
            write_csv(query, "SMILES", ["CCO", "CCC", "CCN"])
            write_csv(reference, "canonical_smiles", ["CCC", "c1ccccc1", "CCO", "CCO"])

            report = run_overlap_audit(
                query_path=query,
                references=[("reference", reference)],
                query_smiles_column="SMILES",
            )

            self.assertEqual(report.query_rows, 3)
            self.assertEqual(report.references[0].exact_matches, 2)
            self.assertAlmostEqual(report.references[0].exact_overlap_rate, 2 / 3)
            self.assertEqual(report.references[0].gate_status, "failed")

    def test_gate_is_incomplete_without_rdkit_audits(self) -> None:
        status, reasons = overlap_gate_status(
            exact_matches=0,
            canonical_matches=None,
            scaffold_overlap_rate=None,
        )
        self.assertEqual(status, "incomplete")
        self.assertEqual(len(reasons), 2)

    def test_gate_passes_zero_overlap_complete_audit(self) -> None:
        status, _ = overlap_gate_status(
            exact_matches=0,
            canonical_matches=0,
            scaffold_overlap_rate=0.4,
        )
        self.assertEqual(status, "passed")


if __name__ == "__main__":
    unittest.main()
