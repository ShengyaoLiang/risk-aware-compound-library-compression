# Fold-specific Training Overlap Audit

- Query: `training/so_active_v3/runs/so_active_v3/fold0/artifacts/bace_new_model_pred.csv`
- Training dataset: `training/so_active_v3/data/activity_v3.parquet`
- Held-out validation fold: 0
- Training rows scanned: 875979
- Gate status: **failed**
- Gate reasons: 321 standardized structure matches detected

| Audit | Matches | Query unique | Overlap rate |
| --- | ---: | ---: | ---: |
| Standardized structure | 321 | 1513 | 21.22% |
| Bemis-Murcko scaffold | 232 | 671 | 34.58% |

A non-zero scaffold overlap does not by itself prove label leakage, but it requires a scaffold-disjoint sensitivity analysis for strong external generalization claims.
