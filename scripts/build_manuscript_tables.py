"""Generate LaTeX result tables from versioned machine-readable artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PAPER_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SNAPSHOT = PAPER_ROOT / "results" / "manuscript_source_metrics.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def f4(value: float) -> str:
    return f"{float(value):.4f}"


def f4_or_dash(value: object) -> str:
    if value is None:
        return "--"
    return f4(float(value))


def tex_escape(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def ci(result: dict[str, Any], metric: str) -> str:
    interval = result["intervals"][metric]
    return f"{interval['lower_95']:.4f}--{interval['upper_95']:.4f}"


def mean_sd(summary: dict[str, Any], metric: str) -> str:
    row = summary["metrics"][metric]
    return f"{row['mean']:.4f} $\\pm$ {row['sd']:.4f}"


def append_table(lines: list[str], command: str, rows: list[str]) -> None:
    lines.append(f"\\newcommand{{\\{command}}}{{%")
    lines.extend(rows)
    lines.append("}")
    lines.append("")


def main() -> None:
    source = load_json(SOURCE_SNAPSHOT)
    dataset_summary = source["dataset_summary"]
    train_summary = source["train_summary"]
    model = source["model_metrics"]
    conformal = source["conformal_report"]
    rf = source["random_forest"]
    chemprop = source["chemprop"]
    sof4 = source["previous_so_f4"]
    bace = load_json(PAPER_ROOT / "results" / "bace_overlap_controlled_eval.json")
    egfr = load_json(PAPER_ROOT / "results" / "egfr_overlap_controlled_eval.json")
    decision = load_json(PAPER_ROOT / "results" / "bace_scaffold_decision_replay.json")
    stats = load_json(PAPER_ROOT / "results" / "statistical_results.json")
    operational = load_json(PAPER_ROOT / "results" / "operational_validation.json")

    lines = [""]

    append_table(
        lines,
        "DataSummaryTable",
        [
            r"\begin{table}[!htbp]",
            r"\centering",
            r"\caption{Prepared ChEMBL 36 activity dataset and fold-0 split.}",
            r"\label{tab:data-summary}",
            r"\begin{tabular}{lr}",
            r"\toprule",
            r"Quantity & Value \\",
            r"\midrule",
            f"Raw activity rows queried & {dataset_summary['rows_raw']:,} \\\\",
            f"Canonical molecules after filtering and deduplication & {dataset_summary['rows_clean']:,} \\\\",
            f"Binary activity threshold & pChEMBL $\\geq$ {dataset_summary['active_threshold']:.1f} \\\\",
            f"Active molecules & {dataset_summary['active_count']:,} \\\\",
            f"Temporal holdout molecules & {dataset_summary['future_count']:,} \\\\",
            f"Fold-0 training molecules & {train_summary['train_rows']:,} \\\\",
            f"Fold-0 internal-validation molecules & {train_summary['val_rows']:,} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ],
    )

    table = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{Activity-model performance on ChEMBL 36 holdouts.}",
        r"\label{tab:model-performance}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Split & RMSE & $R^2$ & Spearman & EF@1\% \\",
        r"\midrule",
    ]
    for key, label in (("val", "Internal validation"), ("future", "Temporal holdout")):
        row = model[key]
        table.append(
            f"{label} & {f4(row['rmse'])} & {f4(row['r2'])} & "
            f"{f4(row['spearman'])} & {f4(row['top0_01_ef'])} \\\\"
        )
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    append_table(lines, "ModelPerformanceTable", table)

    append_table(
        lines,
        "BaselineSanityTable",
        [
            r"\begin{table}[!htbp]",
            r"\centering",
            r"\caption{Selected baseline sanity checks, not a full benchmark suite. Random forest and Chemprop use sampled ChEMBL 36 splits for context; the current model and previous so\_f4 comparison use the full future prediction artifacts.}",
            r"\label{tab:baselines}",
            r"\begin{tabular}{llrrrr}",
            r"\toprule",
            r"Model & Evaluation rows & RMSE & $R^2$ & Spearman & EF@1\% \\",
            r"\midrule",
            f"Current 2D MLP & Future full ({model['future']['rows']:,}) & {f4(model['future']['rmse'])} & {f4(model['future']['r2'])} & {f4(model['future']['spearman'])} & {f4(model['future']['top0_01_ef'])} \\\\",
            f"Previous so\\_f4 & Future full ({sof4['rows']:,}) & {f4(sof4['rmse'])} & {f4(sof4['r2'])} & {f4(sof4['spearman'])} & {f4(sof4['top0_01_ef'])} \\\\",
            f"Random forest Morgan & Future sample ({rf['sampled_rows']['future']:,}) & {f4(rf['metrics']['future']['rmse'])} & {f4(rf['metrics']['future']['r2'])} & {f4(rf['metrics']['future']['spearman'])} & {f4(rf['metrics']['future']['top0_01_ef'])} \\\\",
            f"Chemprop D-MPNN & Future sample ({chemprop['sampled_rows']['future']:,}) & {f4(chemprop['metrics']['future']['rmse'])} & {f4(chemprop['metrics']['future']['r2'])} & {f4(chemprop['metrics']['future']['spearman'])} & {f4(chemprop['metrics']['future']['top0_01_ef'])} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ],
    )

    table = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{BACE external-source performance before and after fold-0 training-overlap control. Primary interpretation should use the strict scaffold-disjoint row.}",
        r"\label{tab:bace-overlap}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Subset & $n$ & ROC AUC & RMSE & Spearman & EF@1\% \\",
        r"\midrule",
    ]
    for key, label in (
        ("full", "Full, provenance only"),
        ("structure_disjoint", "Structure-disjoint"),
        ("scaffold_disjoint", "Scaffold-disjoint"),
    ):
        row = bace["subsets"][key]
        table.append(
            f"{label} & {row['rows']} & {f4(row['roc_auc'])} & "
            f"{f4(row['regression']['rmse'])} & {f4(row['regression']['spearman'])} & "
            f"{f4(row['ranking']['top_0.01']['enrichment_factor'])} \\\\"
        )
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    append_table(lines, "BaceOverlapTable", table)

    table = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{EGFR/CHEMBL203 label-hidden operational sensitivity after fold-0 training-overlap control. This same-source replay is not independent external validation or a natural prospective library.}",
        r"\label{tab:egfr-overlap}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Subset & $n$ & ROC AUC & Spearman & EF@1\% & Hit@10\% \\",
        r"\midrule",
    ]
    for key, label in (
        ("full", "Full, workflow provenance"),
        ("structure_disjoint", "Structure-disjoint"),
        ("scaffold_disjoint", "Scaffold-disjoint"),
    ):
        row = egfr["subsets"][key]
        table.append(
            f"{label} & {row['rows']} & {f4(row['roc_auc'])} & "
            f"{f4(row['spearman_true_pchembl_vs_proxy'])} & "
            f"{f4(row['ranking']['top_0.01']['enrichment_factor'])} & "
            f"{f4(row['ranking']['top_0.1']['hit_rate'])} \\\\"
        )
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    append_table(lines, "EgfrOverlapTable", table)

    append_table(
        lines,
        "DecisionReplayTable",
        [
            r"\begin{table}[!htbp]",
            r"\centering",
            r"\caption{Strict BACE decision-layer replay on a 100-molecule virtual batch. The risk-aware order changes the front of the list rather than uniformly dominating raw activity sorting.}",
            r"\label{tab:decision-replay}",
            r"\small",
            r"\begin{tabular}{lrrrr}",
            r"\toprule",
            r"Order & Hit@10 & Mean pIC50@10 & Hit@20 & Mean pIC50@20 \\",
            r"\midrule",
            f"Raw activity & {f4(decision['raw_order']['top_10']['hit_rate'])} & "
            f"{f4(decision['raw_order']['top_10']['mean_true_pIC50'])} & "
            f"{f4(decision['raw_order']['top_20']['hit_rate'])} & "
            f"{f4(decision['raw_order']['top_20']['mean_true_pIC50'])} \\\\",
            f"Decision (triage $\\rightarrow$ priority score) & "
            f"{f4(decision['decision_order']['top_10']['hit_rate'])} & "
            f"{f4(decision['decision_order']['top_10']['mean_true_pIC50'])} & "
            f"{f4(decision['decision_order']['top_20']['hit_rate'])} & "
            f"{f4(decision['decision_order']['top_20']['mean_true_pIC50'])} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ],
    )

    ab_by_key = {
        (row["strategy"], row["top_n"]): row
        for row in operational["ab_control"]["results"]
    }

    def ab_cell(row: dict[str, Any], key: str) -> str:
        if key in row:
            return f4(row[key])
        mean_key = f"{key}_mean"
        sd_key = f"{key}_sd"
        if sd_key in row:
            return f"{f4(row[mean_key])} $\\pm$ {f4(row[sd_key])}"
        return f4(row[mean_key])

    table = [
        r"\begin{table}[!htbp]",
        r"\centering",
            r"\caption{Retrospective operational A/B controls on the BACE scaffold-disjoint subset. Random and scaffold-diversity rows are averaged over five seeds.}",
        r"\label{tab:operational-ab}",
        r"\begin{tabular}{llrr}",
        r"\toprule",
        r"Top N & Selection rule & Hit rate & Mean pIC50 \\",
        r"\midrule",
    ]
    for top_n in (10, 50, 100):
        for strategy, label in (
            ("system_activity_order", "Ranking score"),
            ("random", "Random"),
            ("scaffold_diversity", "Scaffold diversity"),
        ):
            row = ab_by_key[(strategy, top_n)]
            table.append(
                f"{top_n} & {label} & {ab_cell(row, 'hit_rate')} & "
                f"{ab_cell(row, 'mean_pIC50')} \\\\"
            )
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    append_table(lines, "OperationalABTable", table)

    table = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{High-ranked inactive cases from the BACE scaffold-disjoint subset. Hashes are reported instead of full structures in the manuscript; full public benchmark rows remain in the reproducibility artifact.}",
        r"\label{tab:error-cases}",
        r"\small",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Case & Rank & True pIC50 & Predicted pIC50 & Strict-subset scaffold frequency \\",
        r"\midrule",
    ]
    for row in operational["error_cases"]:
        case_id = tex_escape(row["case_id"])
        table.append(
            f"{case_id} & {row['rank']} & {f4(row['pIC50_true'])} & "
            f"{f4(row['pred_pIC50'])} & {row['scaffold_frequency_in_subset']} \\\\"
        )
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    append_table(lines, "ErrorCasesTable", table)

    strategy_rows = operational["strategy_summary"]["results"]
    strategy_labels = {
        "activity_order": "Activity rank",
        "system_activity_order": "Activity rank",
        "scaffold_diversity": "Scaffold diversity",
        "random_seed2026": "Random seed 2026",
    }
    append_table(
        lines,
        "StrategyDifferenceTable",
        [
            r"\begin{table}[!htbp]",
            r"\centering",
            r"\caption{Strategy-difference summary on the BACE scaffold-disjoint subset and the strict 100-molecule BACE replay. Top-10 overlap compares frozen selection rules on the same scaffold-disjoint subset; the bucket panel summarizes the label-hidden decision replay and is not a prospective risk-distribution claim.}",
            r"\label{tab:strategy-difference}",
            r"\footnotesize",
            r"\setlength{\tabcolsep}{3pt}",
            r"\begin{tabular}{>{\raggedright\arraybackslash}p{0.38\linewidth}p{0.19\linewidth}rr}",
            r"\toprule",
            r"Item & Context/share & Overlap/hit & Jaccard/pIC50 \\",
            r"\midrule",
            r"\multicolumn{4}{l}{\textit{Selection-rule contrast}} \\",
            r"\midrule",
            *[
                (
                    f"{tex_escape(strategy_labels.get(row['left'], row['left']))} vs. "
                    f"{tex_escape(strategy_labels.get(row['right'], row['right']))} "
                    f"& BACE SD & {row['top10_overlap']} & {row['top10_jaccard']:.4f} \\\\"
                )
                for row in strategy_rows
            ],
            r"\midrule",
            r"\multicolumn{4}{l}{\textit{Decision buckets in strict 100-molecule replay}} \\",
            r"\midrule",
            f"Priority & {f4_or_dash(decision['triage_buckets']['priority']['share'])} & "
            f"{f4_or_dash(decision['triage_buckets']['priority']['hit_rate'])} & "
            f"{f4_or_dash(decision['triage_buckets']['priority']['mean_true_pIC50'])} \\\\",
            f"Watch & {f4_or_dash(decision['triage_buckets']['watch']['share'])} & "
            f"{f4_or_dash(decision['triage_buckets']['watch']['hit_rate'])} & "
            f"{f4_or_dash(decision['triage_buckets']['watch']['mean_true_pIC50'])} \\\\",
            f"Low & {f4_or_dash(decision['triage_buckets']['low']['share'])} & "
            f"{f4_or_dash(decision['triage_buckets']['low']['hit_rate'])} & "
            f"{f4_or_dash(decision['triage_buckets']['low']['mean_true_pIC50'])} \\\\",
            f"Review & {f4_or_dash(decision['triage_buckets']['review']['share'])} & "
            f"{f4_or_dash(decision['triage_buckets']['review']['hit_rate'])} & "
            f"{f4_or_dash(decision['triage_buckets']['review']['mean_true_pIC50'])} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ],
    )

    append_table(
        lines,
        "DecisionMatrixTable",
        [
            r"\begin{table}[!htbp]",
            r"\centering",
            r"\caption{Decision matrix used for review guidance. The matrix is a reporting abstraction, not an automatic experimental decision.}",
            r"\label{tab:decision-matrix}",
            r"\begin{tabular}{lll}",
            r"\toprule",
            r"Activity evidence & Domain/uncertainty evidence & Suggested review action \\",
            r"\midrule",
            r"High & Narrow interval or in-domain & First review priority \\",
            r"High & Wide interval or out-of-domain & Risk review before advancement \\",
            r"Moderate/low & Narrow interval or in-domain & Reserve or diversity control \\",
            r"Moderate/low & Wide interval or out-of-domain & Defer without external support \\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ],
    )

    cost = operational["cost_case"]
    cost_ref = cost["bace_scaffold_disjoint_reference"]
    append_table(
        lines,
        "CostFramingTable",
        [
            r"\begin{table}[!htbp]",
            r"\centering",
            r"\caption{Assay-budget framing example for library compression. The values illustrate accounting under a fixed Top-10\% budget and are not a demonstrated project-specific savings claim.}",
            r"\label{tab:cost-framing}",
            r"\begin{tabular}{lr}",
            r"\toprule",
            r"Quantity & Value \\",
            r"\midrule",
            f"Initial library size & {cost['example_library_size']:,} \\\\",
            f"Compression fraction & {int(cost['compression_fraction'] * 100)}\\% \\\\",
            f"First-round tests after compression & {cost['screened_after_compression']:,} \\\\",
            f"Initial tests avoided & {cost['example_library_size'] - cost['screened_after_compression']:,} \\\\",
            f"BACE scaffold-disjoint active recall at Top 10\\% & {f4(cost_ref['recall_at_top_10_percent'])} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ],
    )

    table = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{Virtual-batch ranking at batch size 1,000 across five library-shuffle seeds. Variability reflects batch composition, not model retraining.}",
        r"\label{tab:batch-ranking}",
        r"\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Split & EF@1\% & EF@5\% & EF@10\% & NDCG@10 \\",
        r"\midrule",
    ]
    for key, label in (
        ("ChEMBL36 internal validation", "Internal validation"),
        ("ChEMBL36 temporal holdout", "Temporal holdout"),
        ("BACE scaffold-disjoint", "BACE scaffold-disjoint"),
    ):
        row = stats["virtual_batches"][key]["1000"]
        table.append(
            f"{label} & {mean_sd(row, 'ef_1')} & {mean_sd(row, 'ef_5')} & "
            f"{mean_sd(row, 'ef_10')} & {mean_sd(row, 'ndcg_10')} \\\\"
        )
    table.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2pt}",
            r"\begin{minipage}{0.92\linewidth}\footnotesize For BACE scaffold-disjoint ($n=962$), the batch-size 1,000 row corresponds to one near-complete virtual batch under each shuffle seed; the zero standard deviation is therefore a consequence of discrete binning rather than a formatting artifact.\end{minipage}",
            r"\end{table}",
        ]
    )
    append_table(lines, "VirtualBatchTable", table)

    table = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\caption{Paired bootstrap 95\% intervals over frozen prediction rows. These intervals quantify fixed-prediction uncertainty and exclude retraining variability.}",
        r"\label{tab:bootstrap}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Dataset & Rows & RMSE & Spearman & ROC AUC \\",
        r"\midrule",
    ]
    for key, label in (
        ("ChEMBL36 internal validation", "Internal validation"),
        ("ChEMBL36 temporal holdout", "Temporal holdout"),
        ("BACE scaffold-disjoint", "BACE scaffold-disjoint"),
        ("EGFR scaffold-disjoint replay", "EGFR scaffold-disjoint"),
    ):
        row = stats["bootstrap"][key]
        table.append(
            f"{label} & {row['rows']:,} & {ci(row, 'rmse')} & "
            f"{ci(row, 'spearman')} & {ci(row, 'roc_auc')} \\\\"
        )
    table.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    append_table(lines, "BootstrapTable", table)

    append_table(
        lines,
        "ConformalTable",
        [
            r"\begin{table}[!htbp]",
            r"\centering",
            r"\caption{Split-conformal interval coverage.}",
            r"\label{tab:conformal}",
            r"\begin{tabular}{lrrr}",
            r"\toprule",
            r"Split & 90\% coverage & 80\% coverage & 90\% width \\",
            r"\midrule",
            f"Calibration & {f4(conformal['calib_metrics']['ci90_coverage'])} & "
            f"{f4(conformal['calib_metrics']['ci80_coverage'])} & "
            f"{f4(conformal['calib_metrics']['ci90_width'])} \\\\",
            f"Temporal holdout & {f4(conformal['future_metrics']['ci90_coverage'])} & "
            f"{f4(conformal['future_metrics']['ci80_coverage'])} & "
            f"{f4(conformal['future_metrics']['ci90_width'])} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ],
    )

    output = PAPER_ROOT / "manuscript" / "generated" / "results_tables.tex"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="ascii")
    print(output)


if __name__ == "__main__":
    main()
