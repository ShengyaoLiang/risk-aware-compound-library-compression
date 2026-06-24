from __future__ import annotations

import sys
import unittest
from pathlib import Path


PAPER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PAPER_ROOT / "src"))

from stells_paper.metrics import (
    binary_ranking_metrics,
    enrichment_factor,
    ndcg_at_k,
    regression_metrics,
    roc_auc,
    spearman_correlation,
)


class MetricsTests(unittest.TestCase):
    def test_perfect_ranking(self) -> None:
        labels = [1, 1, 0, 0]
        result = binary_ranking_metrics(labels, k=2)
        self.assertEqual(result.hits, 2)
        self.assertAlmostEqual(result.hit_rate, 1.0)
        self.assertAlmostEqual(result.recall, 1.0)
        self.assertAlmostEqual(result.enrichment_factor, 2.0)
        self.assertAlmostEqual(result.ndcg, 1.0)

    def test_fraction_rounds_up(self) -> None:
        result = binary_ranking_metrics([1] + [0] * 99, fraction=0.01)
        self.assertEqual(result.k, 1)

    def test_no_positives(self) -> None:
        result = binary_ranking_metrics([0, 0, 0], k=1)
        self.assertEqual(result.enrichment_factor, 0.0)
        self.assertEqual(result.recall, 0.0)
        self.assertEqual(result.ndcg, 0.0)

    def test_invalid_labels_rejected(self) -> None:
        with self.assertRaises(ValueError):
            enrichment_factor([0, 2], 1)

    def test_ndcg_penalizes_late_positive(self) -> None:
        self.assertLess(ndcg_at_k([0, 1, 1, 0], 2), 1.0)

    def test_auc_and_spearman_perfect_order(self) -> None:
        self.assertAlmostEqual(roc_auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]), 1.0)
        self.assertAlmostEqual(spearman_correlation([1, 2, 3], [10, 20, 30]), 1.0)

    def test_regression_metrics(self) -> None:
        result = regression_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertEqual(result.total, 3)
        self.assertAlmostEqual(result.rmse, 0.0)
        self.assertAlmostEqual(result.r2, 1.0)


if __name__ == "__main__":
    unittest.main()
