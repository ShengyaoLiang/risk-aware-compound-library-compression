"""Run streaming structure-overlap audits for a candidate evaluation dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PAPER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER_ROOT / "src"))

from stells_paper.overlap_audit import report_markdown, run_overlap_audit


def parse_reference(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("reference must use name=path")
    name, raw_path = value.split("=", 1)
    if not name.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("reference must use non-empty name=path")
    return name.strip(), Path(raw_path).expanduser().resolve()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=Path, required=True)
    parser.add_argument("--query-smiles-column")
    parser.add_argument("--reference", type=parse_reference, action="append", required=True)
    parser.add_argument("--reference-smiles-column")
    parser.add_argument("--output", type=Path, required=True, help="Output path without extension")
    args = parser.parse_args()

    query = args.query.expanduser().resolve()
    references = [(name, path) for name, path in args.reference]
    missing = [str(path) for _, path in references if not path.exists()]
    if not query.exists() or missing:
        raise FileNotFoundError({"query": str(query), "missing_references": missing})

    report = run_overlap_audit(
        query_path=query,
        references=references,
        query_smiles_column=args.query_smiles_column,
        reference_smiles_column=args.reference_smiles_column,
    )
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    output.with_suffix(".md").write_text(report_markdown(report), encoding="utf-8")
    print(output.with_suffix(".json"))
    print(output.with_suffix(".md"))


if __name__ == "__main__":
    main()

