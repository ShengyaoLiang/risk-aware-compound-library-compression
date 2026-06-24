# Statistical Evaluation Summary

## Paired Bootstrap Intervals

| Dataset | Rows | RMSE 95% CI | Spearman 95% CI | ROC AUC 95% CI | EF@1% 95% CI |
| --- | ---: | ---: | ---: | ---: | ---: |
| ChEMBL36 internal validation | 218995 | 0.8432-0.8497 | 0.7653-0.7696 | 0.8838-0.8867 | not estimated |
| ChEMBL36 temporal holdout | 274541 | 1.1585-1.1648 | 0.5143-0.5197 | 0.7513-0.7550 | not estimated |
| BACE scaffold-disjoint | 962 | 0.9861-1.0895 | 0.5598-0.6452 | 0.7315-0.7906 | 1.9050-2.1619 |
| EGFR scaffold-disjoint replay | 223 | 2.1179-2.3440 | 0.7306-0.8123 | 0.9596-0.9899 | 1.8583-2.4239 |

## Multi-seed Virtual Batches

| Dataset | Batch | Seeds | EF@1% | EF@5% | EF@10% | NDCG@10% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ChEMBL36 internal validation | 100 | 5 | 2.7619 +/- 0.0062 | 2.7084 +/- 0.0033 | 2.6320 +/- 0.0017 | 0.9511 +/- 0.0002 |
| ChEMBL36 internal validation | 500 | 5 | 2.7386 +/- 0.0033 | 2.6828 +/- 0.0006 | 2.6127 +/- 0.0010 | 0.9510 +/- 0.0001 |
| ChEMBL36 internal validation | 1000 | 5 | 2.7326 +/- 0.0027 | 2.6789 +/- 0.0013 | 2.6108 +/- 0.0007 | 0.9510 +/- 0.0000 |
| ChEMBL36 temporal holdout | 100 | 5 | 2.4041 +/- 0.0143 | 2.1466 +/- 0.0045 | 1.9612 +/- 0.0019 | 0.8819 +/- 0.0002 |
| ChEMBL36 temporal holdout | 500 | 5 | 2.4306 +/- 0.0059 | 2.1489 +/- 0.0014 | 1.9551 +/- 0.0034 | 0.8817 +/- 0.0002 |
| ChEMBL36 temporal holdout | 1000 | 5 | 2.4398 +/- 0.0080 | 2.1513 +/- 0.0035 | 1.9534 +/- 0.0012 | 0.8811 +/- 0.0002 |
| BACE scaffold-disjoint | 100 | 5 | 2.0537 +/- 0.0167 | 1.9418 +/- 0.0503 | 1.8392 +/- 0.0274 | 0.9217 +/- 0.0038 |
| BACE scaffold-disjoint | 500 | 5 | 2.0265 +/- 0.0028 | 2.0017 +/- 0.0242 | 1.7963 +/- 0.0152 | 0.9187 +/- 0.0011 |
| BACE scaffold-disjoint | 1000 | 5 | 2.0253 +/- 0.0000 | 2.0253 +/- 0.0000 | 1.7956 +/- 0.0000 | 0.9143 +/- 0.0000 |
| EGFR scaffold-disjoint replay | 100 | 5 | 2.1614 +/- 0.0439 | 2.1614 +/- 0.0439 | 2.1614 +/- 0.0439 | 0.9323 +/- 0.0040 |
