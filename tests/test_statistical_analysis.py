from __future__ import annotations

import unittest

try:
    import numpy as np
except ImportError:
    np = None

from stells_paper.statistical_analysis import (
    DatasetArrays,
    point_metrics,
    summarize_seed_runs,
)


@unittest.skipIf(np is None, "numpy is not installed in the lightweight test environment")
class StatisticalAnalysisTests(unittest.TestCase):
    def test_point_metrics_perfect_order(self) -> None:
        result = point_metrics(
            DatasetArrays(
                observed=np.asarray([4.0, 5.0, 8.0, 9.0]),
                predicted=np.asarray([4.0, 5.0, 8.0, 9.0]),
                labels=np.asarray([0, 0, 1, 1]),
            )
        )
        self.assertAlmostEqual(result["rmse"], 0.0)
        self.assertAlmostEqual(result["spearman"], 1.0)
        self.assertAlmostEqual(result["roc_auc"], 1.0)

    def test_seed_summary(self) -> None:
        result = summarize_seed_runs(
            [
                {
                    "seed": 1,
                    "batch_size": 100,
                    "batches": 2,
                    "rows": 200,
                    "ef_1": 2.0,
                },
                {
                    "seed": 2,
                    "batch_size": 100,
                    "batches": 2,
                    "rows": 200,
                    "ef_1": 4.0,
                },
            ]
        )
        self.assertEqual(result["seeds"], [1, 2])
        self.assertAlmostEqual(result["metrics"]["ef_1"]["mean"], 3.0)


if __name__ == "__main__":
    unittest.main()
