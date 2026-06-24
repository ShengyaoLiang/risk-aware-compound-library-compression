# Operational Validation Summary

Frozen artifacts only; no model retraining is performed here.

## Random and Diversity Baselines

| Strategy | Top N | Hit rate | Mean pIC50 | Scaffold diversity |
| --- | ---: | ---: | ---: | ---: |
| system_activity_order | 10 | 1.0000 | 8.3516 | 1.0000 |
| random | 10 | 0.4400 +/- 0.1342 | 6.6667 +/- 0.3905 | 0.9400 |
| scaffold_diversity | 10 | 0.4200 +/- 0.1304 | 6.2401 +/- 0.2620 | 1.0000 |
| system_activity_order | 50 | 1.0000 | 8.2026 | 0.5600 |
| random | 50 | 0.5240 +/- 0.0654 | 6.8378 +/- 0.1919 | 0.8160 |
| scaffold_diversity | 50 | 0.4400 +/- 0.0678 | 6.4208 +/- 0.1913 | 1.0000 |
| system_activity_order | 100 | 0.8900 | 7.8911 | 0.5100 |
| random | 100 | 0.4740 +/- 0.0541 | 6.6163 +/- 0.1467 | 0.7520 |
| scaffold_diversity | 100 | 0.4440 +/- 0.0483 | 6.4902 +/- 0.1531 | 1.0000 |

## High-ranked Inactive Scope-boundary Cases

- `BACE_SD_052` rank 52: true pIC50 6.8239, predicted 7.7409, scaffold frequency 3.
- `BACE_SD_057` rank 57: true pIC50 5.4401, predicted 7.7257, scaffold frequency 1.
- `BACE_SD_060` rank 60: true pIC50 6.7595, predicted 7.7065, scaffold frequency 41.

## Cost-framing Example

- A 10,000-compound library compressed to Top 10% yields 1000 first-round tests and avoids 9000 initial tests.
- In the BACE scaffold-disjoint reference subset, Top 10% captured 85/475 active labels (recall 0.1789).
- Boundary: The calculation is an assay-budget framing example. It should be calibrated with external project labels before being used for a project-specific cost or hit-rate claim.

## Top-10 Strategy Overlap

| Strategy A | Strategy B | Overlap | Jaccard |
| --- | --- | ---: | ---: |
| activity_order | scaffold_diversity | 0 | 0.0000 |
| activity_order | random_seed2026 | 0 | 0.0000 |
| random_seed2026 | scaffold_diversity | 0 | 0.0000 |
