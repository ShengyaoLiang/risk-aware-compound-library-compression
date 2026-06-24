"""Dependency-light ranking metrics used by the paper experiments."""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Iterable, Sequence


@dataclass(frozen=True)
class RankingMetrics:
    total: int
    positives: int
    k: int
    hits: int
    prevalence: float
    hit_rate: float
    recall: float
    enrichment_factor: float
    ndcg: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(frozen=True)
class RegressionMetrics:
    total: int
    mae: float
    rmse: float
    r2: float
    pearson: float
    spearman: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def _validate_binary_labels(labels: Sequence[int]) -> list[int]:
    normalized = [int(value) for value in labels]
    invalid = sorted({value for value in normalized if value not in (0, 1)})
    if invalid:
        raise ValueError(f"labels must be binary, found: {invalid}")
    return normalized


def _resolve_k(total: int, *, k: int | None, fraction: float | None) -> int:
    if total <= 0:
        return 0
    if (k is None) == (fraction is None):
        raise ValueError("provide exactly one of k or fraction")
    if fraction is not None:
        if not 0 < fraction <= 1:
            raise ValueError("fraction must be in (0, 1]")
        k = max(1, math.ceil(total * fraction))
    assert k is not None
    if k <= 0:
        raise ValueError("k must be positive")
    return min(int(k), total)


def dcg(relevances: Iterable[int]) -> float:
    return sum((2**int(rel) - 1) / math.log2(index + 2) for index, rel in enumerate(relevances))


def ndcg_at_k(labels: Sequence[int], k: int) -> float:
    normalized = _validate_binary_labels(labels)
    if not normalized:
        return 0.0
    resolved_k = min(max(int(k), 1), len(normalized))
    observed = normalized[:resolved_k]
    ideal = sorted(normalized, reverse=True)[:resolved_k]
    denominator = dcg(ideal)
    return dcg(observed) / denominator if denominator else 0.0


def enrichment_factor(labels: Sequence[int], k: int) -> float:
    normalized = _validate_binary_labels(labels)
    if not normalized:
        return 0.0
    resolved_k = min(max(int(k), 1), len(normalized))
    prevalence = sum(normalized) / len(normalized)
    if prevalence == 0:
        return 0.0
    return (sum(normalized[:resolved_k]) / resolved_k) / prevalence


def binary_ranking_metrics(
    labels: Sequence[int],
    *,
    k: int | None = None,
    fraction: float | None = None,
) -> RankingMetrics:
    normalized = _validate_binary_labels(labels)
    total = len(normalized)
    resolved_k = _resolve_k(total, k=k, fraction=fraction)
    positives = sum(normalized)
    hits = sum(normalized[:resolved_k]) if resolved_k else 0
    prevalence = positives / total if total else 0.0
    hit_rate = hits / resolved_k if resolved_k else 0.0
    recall = hits / positives if positives else 0.0
    ef = hit_rate / prevalence if prevalence else 0.0
    ndcg = ndcg_at_k(normalized, resolved_k) if resolved_k else 0.0
    return RankingMetrics(
        total=total,
        positives=positives,
        k=resolved_k,
        hits=hits,
        prevalence=prevalence,
        hit_rate=hit_rate,
        recall=recall,
        enrichment_factor=ef,
        ndcg=ndcg,
    )


def rankdata_average(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(float(value) for value in values), key=lambda item: item[1])
    ranks = [0.0] * len(indexed)
    start = 0
    while start < len(indexed):
        end = start + 1
        while end < len(indexed) and indexed[end][1] == indexed[start][1]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[indexed[position][0]] = average_rank
        start = end
    return ranks


def pearson_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("correlation inputs must have equal length")
    if len(left) < 2:
        return 0.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_centered = [float(value) - left_mean for value in left]
    right_centered = [float(value) - right_mean for value in right]
    numerator = sum(a * b for a, b in zip(left_centered, right_centered))
    denominator = math.sqrt(
        sum(value * value for value in left_centered)
        * sum(value * value for value in right_centered)
    )
    return numerator / denominator if denominator else 0.0


def spearman_correlation(left: Sequence[float], right: Sequence[float]) -> float:
    return pearson_correlation(rankdata_average(left), rankdata_average(right))


def roc_auc(labels: Sequence[int], scores: Sequence[float]) -> float:
    normalized = _validate_binary_labels(labels)
    if len(normalized) != len(scores):
        raise ValueError("labels and scores must have equal length")
    positives = sum(normalized)
    negatives = len(normalized) - positives
    if not positives or not negatives:
        return 0.0
    ranks = rankdata_average(scores)
    positive_rank_sum = sum(rank for rank, label in zip(ranks, normalized) if label == 1)
    return (
        positive_rank_sum - positives * (positives + 1) / 2.0
    ) / (positives * negatives)


def regression_metrics(
    observed: Sequence[float],
    predicted: Sequence[float],
) -> RegressionMetrics:
    if len(observed) != len(predicted):
        raise ValueError("observed and predicted values must have equal length")
    if not observed:
        raise ValueError("regression metrics require at least one row")
    residuals = [float(pred) - float(true) for true, pred in zip(observed, predicted)]
    mae = sum(abs(value) for value in residuals) / len(residuals)
    rmse = math.sqrt(sum(value * value for value in residuals) / len(residuals))
    observed_mean = sum(observed) / len(observed)
    denominator = sum((float(value) - observed_mean) ** 2 for value in observed)
    numerator = sum(value * value for value in residuals)
    r2 = 1.0 - numerator / denominator if denominator else 0.0
    return RegressionMetrics(
        total=len(observed),
        mae=mae,
        rmse=rmse,
        r2=r2,
        pearson=pearson_correlation(observed, predicted),
        spearman=spearman_correlation(observed, predicted),
    )
