# Paper Evidence Matrix

| Evidence | Role | Status | Main limitation |
| --- | --- | --- | --- |
| `chembl36_internal_val` | internal_validation | **available** | single trained fold currently reported; bootstrap intervals exclude model-retraining variability |
| `chembl36_future` | temporal_holdout | **available** | single trained fold currently reported; bootstrap intervals exclude model-retraining variability |
| `multifold_training_variability` | training_variability | **insufficient_completed_folds** | only fold 0 is complete at this snapshot; fold 1 and fold 2 should be completed before making a multi-fold claim |
| `bace1513_full` | external_source_historical_result | **overlap_detected** | not valid as strict independent evidence without overlap removal; full-set metrics retained for provenance only |
| `bace1513_structure_disjoint` | external_structure_disjoint | **available** | scaffold overlap remains; bootstrap intervals exclude model-retraining variability |
| `bace1513_scaffold_disjoint` | external_scaffold_disjoint_sensitivity | **available** | bootstrap intervals exclude model-retraining variability |
| `egfr_chembl203_full_replay` | workflow_demonstration | **overlap_detected** | same ChEMBL 36 source family as the activity training data; full-set result retained for workflow provenance only; excluded from independent external-generalization claims |
| `egfr_chembl203_structure_disjoint` | target_specific_workflow_sensitivity | **available_with_limitations** | scaffold overlap remains; same-source target-specific replay, not independent external validation; bootstrap intervals exclude model-retraining variability |
| `egfr_chembl203_scaffold_disjoint` | target_specific_workflow_sensitivity | **available_with_limitations** | same-source target-specific replay, not independent external validation; bootstrap intervals exclude model-retraining variability |
| `batch_ranking_seed2026` | budget_constrained_ranking | **available** | legacy full-set BACE batch rows are not used for strict external claims |
| `multiseed_virtual_batches` | budget_constrained_ranking_sensitivity | **available** | seed variability reflects library shuffling only, not model retraining |
| `paired_bootstrap_intervals` | fixed_prediction_uncertainty | **available** | intervals are over frozen prediction rows and exclude retraining variability |
| `baseline_sanity_checks` | model_context | **available_with_limitations** | random forest and Chemprop baselines use sampled ChEMBL 36 splits; not full Future all-row same-protocol benchmarks; not a final unified full-scale benchmark suite |
| `decision_layer_replay` | risk_aware_ranking | **available_with_limitations** | single replay seed; not uniformly superior to activity-only ranking; strict BACE replay uses one 100-molecule virtual batch |
| `operational_ab_controls` | budgeted_selection_controls | **available_with_limitations** | retrospective simulation on frozen BACE predictions; random and scaffold-diversity controls use five selection seeds; Top-10 overlap is reported as a strategy-difference display; does not establish project-specific wet-lab gains |
| `released_package_scope` | public_reproducibility_boundary | **available_with_scope_limits** | complete ChEMBL-derived training assets are not published; full train/validation ID lists are not published; released scripts reproduce manuscript tables from frozen non-sensitive artifacts |
| `failure_case_analysis` | scope_boundary_analysis | **available** | small descriptive sample of high-ranked inactive molecules; not a complete mechanistic error taxonomy |
| `assay_budget_accounting` | illustrative_cost_framing | **available_with_limitations** | illustrative accounting only; requires external calibration before project-specific savings claims |
| `prospective_wet_lab` | prospective_validation | **missing** | required before claiming project-specific hit-rate or cost gains; reported as a limitation, not required for an arXiv methods preprint |

## Submission Blockers

- confirm final author metadata, license, and arXiv category in the arXiv web form
- complete final visual review and obtain an independent domain review

## Future Strengthening

- run all baselines at full scale under identical splits and preprocessing
- complete fold-1 and fold-2 full training to report 2-3 fold variability
- add externally blinded historical replay or prospective wet-lab validation
