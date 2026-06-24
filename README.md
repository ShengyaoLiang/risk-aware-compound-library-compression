# Budget-Constrained Compound Library Prioritization - Reproducibility Package

[![DOI](https://zenodo.org/badge/1279105623.svg)](https://doi.org/10.5281/zenodo.20833014)

Zenodo latest-record DOI: https://doi.org/10.5281/zenodo.20833014

The original v1.0.0 archive is available at https://doi.org/10.5281/zenodo.20833015.
For later releases, use the Zenodo badge or repository release page to access
the version-specific DOI assigned after archival.

This repository contains the non-sensitive reproducibility materials for the
preprint:

**Budget-Constrained Compound Library Prioritization with Risk Awareness and Uncertainty Quantification**

The package is technical only. It includes scripts, frozen result artifacts,
subset files, generated manuscript tables and a small public benchmark example.
It does not include runtime accounts, credentials, private submissions, hidden
labels, deployment state or business correspondence.

The release also does not publish complete ChEMBL-derived training assets or
full train/validation ID lists. Those files are large and remain outside the
non-sensitive public package because of size, provenance and internal-asset
boundaries. The released package instead provides frozen non-sensitive
summaries, public subset files, generated tables and scripts sufficient to
reproduce the manuscript tables from the released artifacts.

The recommended public repository name is
`risk-aware-compound-library-compression`. The public repository URL is
<https://github.com/ShengyaoLiang/risk-aware-compound-library-compression>.
Code is released under the MIT license. Public benchmark data and manuscript
content remain subject to their respective upstream and publication terms.

## Contents

```text
.
├── manuscript/                  LaTeX source, bibliography, figures, generated tables
├── results/                     Frozen public/reproducible evaluation artifacts
├── scripts/                     Reproducibility entry points
├── src/stells_paper/            Shared metric and overlap-audit utilities
├── tests/                       Unit tests for metrics/statistics/auditing
├── examples/                    Small public benchmark sample
├── requirements.txt             Python dependency list
└── RELEASE_MANIFEST.json        File manifest generated at packaging time
```

## Reproduce Core Tables

Install dependencies in a clean Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Regenerate the manuscript tables and vector figures from frozen artifacts:

```bash
python scripts/build_operational_validation.py
python scripts/build_evidence_matrix.py
python scripts/build_manuscript_tables.py
python scripts/build_manuscript_figures.py
```

`results/manuscript_source_metrics.json` is the frozen, non-sensitive snapshot
of the training-summary metrics needed by the table generator. The
`build_manuscript_source_snapshot.py` helper is included for provenance but
requires the original private training workspace and is not needed to reproduce
the released tables.

The generated LaTeX table file is:

```text
manuscript/generated/results_tables.tex
```

Generated figures are written under:

```text
manuscript/figures/
```

## Evidence Boundaries

- ChEMBL 36 internal validation and temporal holdout are frozen split
  evaluations.
- BACE full-set metrics are provenance only because fold-0 training overlap was
  detected.
- BACE structure-disjoint and scaffold-disjoint subsets are the primary
  external-source sensitivity evidence.
- EGFR/CHEMBL203 replay is a same-source label-hidden operational sensitivity
  analysis, not independent external validation.
- Random forest and Chemprop are sampled model sanity checks, not full Future
  all-row, same-protocol benchmarks.
- A real unknown-activity external library can be ranked from SMILES alone, but
  enrichment and hit-rate effects require later historical-label reveal or
  prospective experimental readout.
- Bootstrap intervals are computed over frozen prediction rows and exclude
  retraining variability.
- Only one complete full-scale training fold is reported. The included
  `results/multifold_training_summary.*` files track completed folds and should
  not be used as a multi-fold claim until at least fold 1 and fold 2 are
  complete.
- The operational A/B controls are retrospective simulations on frozen public
  artifacts and do not establish project-specific wet-lab hit-rate or cost
  improvement.

## Example Data

`examples/bace_scaffold_disjoint_sample.csv` is a small sample from the public
BACE scaffold-disjoint artifact. It is intended for script smoke tests and
format inspection, not for reporting final metrics.


