# Decision-Layer Replay via Official Backend API: external_bace

- Seed: `2026`
- Batch size: `100`
- Sampled virtual batches: `1`
- Sampled labeled rows: `100`
- Overall final-risk ratio: `0.98`

| Order | Hit@10 | Mean pIC50@10 | Risk@10 | Hit@20 | Mean pIC50@20 | Risk@20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw activity | 1.0 | 8.2303 | 1.0 | 0.9 | 7.6705 | 1.0 |
| Decision (`triage -> priority_score`) | 0.9 | 7.9546 | 1.0 | 0.85 | 7.6392 | 1.0 |

| Triage bucket | Share | Hit rate | Mean true pIC50 | Risk ratio |
| --- | ---: | ---: | ---: | ---: |
| priority | 0.11 | 0.9091 | 8.0637 | 1.0 |
| watch | 0.18 | 0.8333 | 7.3748 | 1.0 |
| low | 0.71 | 0.4225 | 6.1861 | 0.9718 |
| review | 0.0 | None | None | None |
