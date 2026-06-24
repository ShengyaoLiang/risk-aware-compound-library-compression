"""Statistical summaries for frozen molecular-ranking predictions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class DatasetArrays:
    observed: Any
    predicted: Any
    labels: Any


def _dependencies() -> tuple[Any, Any, Any]:
    try:
        import numpy as np
        from scipy.stats import rankdata
        from sklearn.metrics import roc_auc_score
    except ImportError as exc:
        raise RuntimeError(
            "Statistical analysis requires numpy, scipy, and scikit-learn. "
            "Run it with the stells backend Docker image."
        ) from exc
    return np, rankdata, roc_auc_score


def point_metrics(data: DatasetArrays, *, ef_fraction: float = 0.01) -> dict[str, float]:
    np, rankdata, roc_auc_score = _dependencies()
    observed = np.asarray(data.observed, dtype=np.float64)
    predicted = np.asarray(data.predicted, dtype=np.float64)
    labels = np.asarray(data.labels, dtype=np.int8)
    residual = predicted - observed
    rmse = float(np.sqrt(np.mean(residual * residual)))
    observed_rank = rankdata(observed, method="average")
    predicted_rank = rankdata(predicted, method="average")
    spearman = float(np.corrcoef(observed_rank, predicted_rank)[0, 1])
    auc = float(roc_auc_score(labels, predicted))
    order = np.argsort(-predicted, kind="stable")
    k = max(1, int(math.ceil(len(labels) * ef_fraction)))
    prevalence = float(labels.mean())
    hit_rate = float(labels[order[:k]].mean())
    return {
        "rmse": rmse,
        "spearman": spearman,
        "roc_auc": auc,
        "ef_1": hit_rate / prevalence if prevalence else 0.0,
        "hit_rate_1": hit_rate,
    }


def paired_bootstrap(
    data: DatasetArrays,
    *,
    replicates: int,
    seed: int,
    include_ef: bool,
) -> dict[str, Any]:
    np, _, _ = _dependencies()
    observed = np.asarray(data.observed, dtype=np.float64)
    predicted = np.asarray(data.predicted, dtype=np.float64)
    labels = np.asarray(data.labels, dtype=np.int8)
    if not (len(observed) == len(predicted) == len(labels)):
        raise ValueError("observed, predicted, and labels must have equal length")
    if len(observed) < 2:
        raise ValueError("bootstrap requires at least two rows")

    rng = np.random.default_rng(seed)
    metric_names = ["rmse", "spearman", "roc_auc"]
    if include_ef:
        metric_names.extend(["ef_1", "hit_rate_1"])
    samples: dict[str, list[float]] = {name: [] for name in metric_names}

    for _ in range(replicates):
        indices = rng.integers(0, len(observed), size=len(observed))
        boot_labels = labels[indices]
        if int(boot_labels.min()) == int(boot_labels.max()):
            continue
        metrics = point_metrics(
            DatasetArrays(
                observed=observed[indices],
                predicted=predicted[indices],
                labels=boot_labels,
            )
        )
        for name in metric_names:
            samples[name].append(float(metrics[name]))

    output: dict[str, Any] = {
        "rows": int(len(observed)),
        "replicates_requested": int(replicates),
        "replicates_completed": min(len(values) for values in samples.values()),
        "seed": int(seed),
        "point": point_metrics(data),
        "intervals": {},
    }
    for name, values in samples.items():
        array = np.asarray(values, dtype=np.float64)
        output["intervals"][name] = {
            "lower_95": float(np.quantile(array, 0.025)),
            "upper_95": float(np.quantile(array, 0.975)),
            "bootstrap_mean": float(array.mean()),
            "bootstrap_sd": float(array.std(ddof=1)),
        }
    return output


def _ndcg_continuous(observed: Any, predicted: Any, fraction: float) -> float:
    np, _, _ = _dependencies()
    k = max(1, int(math.ceil(len(observed) * fraction)))
    predicted_order = np.argsort(-predicted, kind="stable")[:k]
    ideal_order = np.argsort(-observed, kind="stable")[:k]
    discounts = 1.0 / np.log2(np.arange(2, k + 2, dtype=np.float64))
    dcg = float(np.sum(observed[predicted_order] * discounts))
    idcg = float(np.sum(observed[ideal_order] * discounts))
    return dcg / idcg if idcg else 0.0


def virtual_batch_metrics(
    data: DatasetArrays,
    *,
    batch_size: int,
    seed: int,
    fractions: Iterable[float] = (0.01, 0.05, 0.10),
) -> dict[str, float | int]:
    np, _, _ = _dependencies()
    observed = np.asarray(data.observed, dtype=np.float64)
    predicted = np.asarray(data.predicted, dtype=np.float64)
    labels = np.asarray(data.labels, dtype=np.int8)
    permutation = np.random.default_rng(seed).permutation(len(observed))

    ef_values = {fraction: [] for fraction in fractions}
    hit_values = {fraction: [] for fraction in fractions}
    ndcg_values: list[float] = []
    batches = 0
    for start in range(0, len(permutation), batch_size):
        indices = permutation[start : start + batch_size]
        if len(indices) < 2:
            continue
        batch_observed = observed[indices]
        batch_predicted = predicted[indices]
        batch_labels = labels[indices]
        prevalence = float(batch_labels.mean())
        order = np.argsort(-batch_predicted, kind="stable")
        for fraction in fractions:
            k = max(1, int(math.ceil(len(indices) * fraction)))
            hit_rate = float(batch_labels[order[:k]].mean())
            hit_values[fraction].append(hit_rate)
            if prevalence:
                ef_values[fraction].append(hit_rate / prevalence)
        ndcg_values.append(_ndcg_continuous(batch_observed, batch_predicted, 0.10))
        batches += 1

    result: dict[str, float | int] = {
        "seed": int(seed),
        "batch_size": int(batch_size),
        "batches": int(batches),
        "rows": int(len(observed)),
        "ndcg_10": float(np.mean(ndcg_values)),
    }
    for fraction in fractions:
        tag = int(round(fraction * 100))
        result[f"ef_{tag}"] = float(np.mean(ef_values[fraction]))
        result[f"hit_rate_{tag}"] = float(np.mean(hit_values[fraction]))
    return result


def summarize_seed_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    np, _, _ = _dependencies()
    if not runs:
        raise ValueError("at least one seed run is required")
    metric_names = sorted(
        key
        for key, value in runs[0].items()
        if isinstance(value, float)
    )
    summary: dict[str, Any] = {
        "rows": int(runs[0]["rows"]),
        "batch_size": int(runs[0]["batch_size"]),
        "batches_per_seed": int(runs[0]["batches"]),
        "seeds": [int(run["seed"]) for run in runs],
        "metrics": {},
    }
    for name in metric_names:
        values = np.asarray([float(run[name]) for run in runs], dtype=np.float64)
        summary["metrics"][name] = {
            "mean": float(values.mean()),
            "sd": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            "min": float(values.min()),
            "max": float(values.max()),
        }
    return summary
