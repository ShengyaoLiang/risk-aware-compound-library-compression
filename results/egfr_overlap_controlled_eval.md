# Overlap-controlled EGFR/CHEMBL203 Workflow Replay

- Original matched rows: 500
- Fold-0 training rows scanned: 875979
- Removed standardized-structure matches: 170
- Training-overlapping query scaffolds: 119

| Evaluation subset | Rows | Prevalence | ROC AUC | Spearman | EF@1% | EF@5% | EF@10% | Hit@10% | NDCG@10% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original full EGFR replay | 500 | 50.00% | 0.9582 | 0.7001 | 2.0000 | 2.0000 | 2.0000 | 100.00% | 1.0000 |
| Standardized-structure disjoint | 330 | 50.00% | 0.9754 | 0.7479 | 2.0000 | 2.0000 | 2.0000 | 100.00% | 1.0000 |
| Bemis-Murcko scaffold disjoint | 223 | 47.53% | 0.9769 | 0.7773 | 2.1038 | 2.1038 | 2.1038 | 100.00% | 1.0000 |

This replay is built from ChEMBL EGFR/CHEMBL203 records. Even after overlap removal, it should be reported as a target-specific workflow sensitivity analysis, not as fully independent external validation.
