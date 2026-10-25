"""Regression checks for the supplied recording. Generate data/readings.json first."""
import json
from pathlib import Path
import unittest

from reader import recognize

ROOT = Path(__file__).resolve().parents[1]


class RecognitionSafety(unittest.TestCase):
    def test_missing_display_does_not_become_zero(self):
        self.assertIsNone(recognize([0] * 7)[0])

    def test_ambiguous_stroke_is_rejected(self):
        # An apparent zero with one stroke near the threshold must be uncertain.
        self.assertIsNone(recognize([.9, .9, .26, .9, .9, .9, 0])[0])


@unittest.skipUnless((ROOT / 'data/readings.json').exists(), 'Analyze the clip first')
class RecordingRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'data/readings.json').read_text())
        cls.rows = cls.data['readings']

    def at(self, t):
        return self.rows[round(t * self.data['fps'])]

    def test_manually_reviewed_holdout_samples(self):
        # Separate from the five frames used to position the segment probes.
        labels = {30: ('19:36', 0), 50: ('19:17', 0), 70: ('19:16', 0),
                  90: ('19:08', 0), 110: ('18:48', 0), 130: ('18:41', 1),
                  150: ('18:33', 1)}
        for t, (clock, away) in labels.items():
            with self.subTest(t=t):
                self.assertEqual(self.at(t)['raw'], {'clock': clock, 'home': 0, 'away': away})

    def test_confirmed_clock_has_no_transition_glitches(self):
        previous = None
        for row in self.rows:
            if row['status'] != 'confirmed':
                continue
            minutes, seconds = map(int, row['values']['clock'].split(':'))
            current = minutes * 60 + seconds
            if previous is not None:
                self.assertIn(previous - current, (0, 1), f"Clock glitch at {row['t']}s")
            previous = current

    def test_clock_follows_pauses(self):
        for start, end, expected in [(25, 30, '19:36'), (52, 69, '19:16'),
                                     (80, 89, '19:08'), (121, 141, '18:41')]:
            for t in range(start, end + 1):
                self.assertEqual(self.at(t)['values']['clock'], expected)

    def test_goal_is_retained_and_home_score_stays_zero(self):
        for row in self.rows:
            if row['values']:
                self.assertEqual(row['values']['home'], 0)
                self.assertIn(row['values']['away'], (0, 1))
        self.assertEqual(self.at(110)['values']['away'], 0)
        self.assertEqual(self.at(120)['values']['away'], 1)
        self.assertEqual(self.rows[-1]['values']['away'], 1)

    def test_confirmation_requires_repeated_evidence(self):
        for before, row in zip(self.rows, self.rows[1:]):
            if row['status'] == 'confirmed':
                self.assertIsNotNone(row['raw'])
                self.assertEqual(row['raw'], before['raw'])
                self.assertEqual(row['raw'], row['values'])


if __name__ == '__main__':
    unittest.main()
