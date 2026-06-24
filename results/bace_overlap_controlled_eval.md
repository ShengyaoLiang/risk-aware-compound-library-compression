# Overlap-controlled BACE Evaluation

- Original rows: 1513
- Fold-0 training rows scanned: 875979
- Removed standardized-structure matches: 321
- Training-overlapping query scaffolds: 232

| Evaluation subset | Rows | Prevalence | ROC AUC | RMSE | Spearman | EF@1% | EF@5% | EF@10% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original full BACE | 1513 | 45.67% | 0.8304 | 0.9330 | 0.6958 | 2.0527 | 2.1031 | 1.9735 |
| Standardized-structure disjoint | 1192 | 46.98% | 0.8035 | 1.0052 | 0.6641 | 2.1286 | 2.0576 | 1.8980 |
| Bemis-Murcko scaffold disjoint | 962 | 49.38% | 0.7626 | 1.0370 | 0.6047 | 2.0253 | 2.0253 | 1.7956 |

The original full-dataset result is retained for provenance only. Strong external-generalization claims must use the overlap-controlled subsets.
