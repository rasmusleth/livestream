"""Regression checks for the supplied recording. Generate data/readings.json first."""
import json
from pathlib import Path
import unittest

from reader import FrameReader, recognize

ROOT = Path(__file__).resolve().parents[1]


class RecognitionSafety(unittest.TestCase):
    def test_missing_display_does_not_become_zero(self):
        self.assertIsNone(recognize([0] * 7)[0])

    def test_ambiguous_stroke_is_rejected(self):
        # An apparent zero with one stroke near the threshold must be uncertain.
        self.assertIsNone(recognize([.9, .9, .26, .9, .9, .9, 0])[0])


class WhiteCoreSafety(unittest.TestCase):
    # Independent stroke definitions; these fixtures test RGB probe evidence,
    # not digit geometry or calibration accuracy.
    strokes = {0: (0, 1, 2, 3, 4, 5), 1: (1, 2), 2: (0, 1, 3, 4, 6),
               3: (0, 1, 2, 3, 6), 4: (1, 2, 5, 6), 5: (0, 2, 3, 5, 6),
               6: (0, 2, 3, 4, 5, 6), 7: (0, 1, 2),
               8: (0, 1, 2, 3, 4, 5, 6), 9: (0, 1, 2, 3, 5, 6)}

    def setUp(self):
        self.reader = FrameReader(json.loads((ROOT / 'calibration.json').read_text()))

    def paint(self, frame, name, segment, rgb):
        for x, y in self.reader.points[name][segment]:
            offset = (y * self.reader.width + x) * 3
            frame[offset:offset + 3] = bytes(rgb)

    def frame(self, home=0):
        frame = bytearray(bytes((25, 20, 20)) * self.reader.width * self.reader.height)
        for name, value in dict(minutes_tens=1, minutes_units=8,
                                seconds_tens=4, seconds_units=1, home=home, away=1).items():
            for segment in self.strokes[value]:
                self.paint(frame, name, segment, (255, 160, 160))
        return frame

    def test_white_zero_stroke_and_red_centre_do_not_confirm_nine(self):
        frame = self.frame()
        self.paint(frame, 'home', 4, (250, 250, 250))
        self.paint(frame, 'home', 6, (228, 97, 126))
        for t in (0, .1, .2):
            row = self.reader.read(frame, t)
            self.assertEqual(recognize(row['segments']['home'])[0], 9)
            self.assertEqual(row['white_segments']['home'][4], 1)
            self.assertEqual(row['rejections']['home'], 'white_core_on_off_probe')
            self.assertIsNone(self.reader.digits['home'])
            self.assertIsNone(row['raw'])
            self.assertIsNone(row['values'])
            self.assertIsNone(row['age'])
            self.assertEqual(row['status'], 'unknown')
            self.assertEqual(row['confidence'], 0)

    def test_rejection_holds_age_and_recovery_requires_new_evidence(self):
        frame = self.frame()
        self.reader.read(frame, 0)
        confirmed = self.reader.read(frame, .1)['values']
        conflict = self.frame()
        # The same guard applies to clock digits, without inventing a tick.
        self.paint(conflict, 'minutes_units', 4, (250, 250, 250))
        for t in (.2, 1.3):
            row = self.reader.read(conflict, t)
            self.assertIsNone(row['raw'])
            self.assertEqual(row['values'], confirmed)
            self.assertEqual(row['status'], 'held')
            self.assertAlmostEqual(row['age'], t - .1)
        row = self.reader.read(frame, 1.4)
        self.assertEqual(row['status'], 'held')
        self.assertEqual(row['age'], 1.3)
        row = self.reader.read(frame, 1.5)
        self.assertEqual(row['status'], 'confirmed')
        self.assertEqual(row['age'], 0)

    def test_all_ten_colour_digits_remain_available_and_white_is_not_guessed(self):
        for digit, strokes in self.strokes.items():
            with self.subTest(digit=digit):
                frame = self.frame(home=digit)
                row = self.reader.read(frame, digit * .2)
                self.assertEqual(row['raw']['home'], digit)
                self.assertEqual(row['rejections'], {})
                for stroke in strokes:
                    self.paint(frame, 'home', stroke, (255, 255, 255))
                row = self.reader.read(frame, digit * .2 + .1)
                self.assertIsNone(row['raw'])
                self.assertIn('home', row['rejections'])

    def test_blank_is_still_unknown(self):
        frame = bytes(self.reader.frame_size)
        row = self.reader.read(frame, 0)
        self.assertIsNone(row['raw'])
        self.assertEqual(row['status'], 'unknown')


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
