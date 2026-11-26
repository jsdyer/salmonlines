import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from profiles import main_measure, metrics_for, number


class ProfileTests(unittest.TestCase):
    def test_estimates_stay_on_one_measure_and_zero_counts(self):
        rows = [[y, 0 if y % 2 == 0 else None, 12 if y % 2 else None, None, None, 0, 0] for y in range(2000, 2010)]
        self.assertIsNone(main_measure(metrics_for(rows)))
        for row in rows:
            row[1] = 0
            row[4] = 20
        values = metrics_for(rows)
        self.assertEqual(main_measure(values), 1)
        rows.append([2010, None, None, None, 15, 0, 0])
        self.assertEqual(main_measure(metrics_for(rows)), 4)
        self.assertEqual(number(0), "0")

    def test_duplicate_observations_for_year_require_source_review(self):
        row = [2000, 10, None, None, None, 0, 0]
        with self.assertRaisesRegex(ValueError, "Multiple observations"):
            metrics_for([row, row])
