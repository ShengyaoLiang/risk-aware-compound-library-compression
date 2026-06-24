# Budget-Constrained Compound Library Prioritization - Reproducibility Package

[![DOI](https://zenodo.org/badge/1279105623.svg)](https://doi.org/10.5281/zenodo.20833014)

Zenodo latest-record DOI: https://doi.org/10.5281/zenodo.20833014

The original v1.0.0 archive is available at https://doi.org/10.5281/zenodo.20833015.
For later releases, use the Zenodo badge or repository release page to access
the version-specific DOI assigned after archival.

This repository is my public, non-sensitive reproducibility record for the
preprint:

**Budget-Constrained Compound Library Prioritization with Risk Awareness and Uncertainty Quantification**

The manuscript argues for a specific decision layer: before a project spends
experimental or expert-review budget on a large molecular library, it can first
compress that library into a smaller, risk-annotated Top-k candidate set. I am
publishing this repository so that the evidence chain behind that claim can be
inspected, not merely asserted. It is not a dump of the full platform, a
deployment package for the Web service, or a promise that every external
library will show the same enrichment.

What is public here is the non-sensitive record needed to reproduce the
reported manuscript tables from frozen artifacts: scripts, result summaries,
public subset files, generated manuscript tables, tests and a small public
benchmark example. What I have intentionally not included are runtime accounts,
credentials, private submissions, withheld labels, deployment state, complete
ChEMBL-derived training assets and full train/validation ID lists. That
boundary is deliberate: the release should make the evidence auditable without
exposing private operational data or pretending that a public package is the
same thing as a deployed screening service.

The right way to use this repository is to understand the evidence boundary
and, if the framing is relevant, design an external blind replay or prospective
A/B pilot on an independent library. The code is released under the MIT
license. Public benchmark data and manuscript content remain subject to their
respective upstream and publication terms.

Repository URL:
<https://github.com/ShengyaoLiang/risk-aware-compound-library-compression>

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

## External Validation Use

For an external team, the clean validation path is not to assume that the
public benchmark enrichment transfers unchanged to its own chemistry. A better
protocol is:

1. Provide a blinded SMILES-only library while holding back labels or project
   outcomes.
2. Rank the library and export Top-k candidate sets without using the labels.
3. Reveal historical labels or complete prospective testing.
4. Compare enrichment, hit rate, recall and NDCG against random,
   diversity-matched and local-selection baselines.

That protocol tests the central claim of the manuscript in the only place it
ultimately matters: the external team's own chemical and experimental context.
This is also the collaboration path I prefer, because it lets the platform rank
first and lets the partner's data decide whether the compression layer adds
real value.

## Example Data

`examples/bace_scaffold_disjoint_sample.csv` is a small sample from the public
BACE scaffold-disjoint artifact. It is intended for script smoke tests and
format inspection, not for reporting final metrics.


