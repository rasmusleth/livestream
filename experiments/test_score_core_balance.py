"""Uneven clean LED brightness through RGB recognition and shadow state."""
import json
from pathlib import Path
import unittest

import numpy as np

from candidate_state import LayoutPlan
from exposure_stress import ExposureScene, LINES, STROKES
from region_reader import RegionReader
from shadow import ShadowReader

ROOT = Path(__file__).resolve().parents[1]


class ScoreCoreBalance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT/'calibration.json').read_text())
        cls.reader = RegionReader(cls.config, cls.config)
        cls.scene = ExposureScene(cls.config)

    def uneven(self, digit, dim=(255,170,130)):
        # Independently drawn clean score: right strokes brighter than all
        # others. Encoded RGB is a fixture, not a physical camera model.
        frame = self.scene.base.copy()
        frame[690:860,610:735] = (180,130,110)
        for segment in STROKES[digit]:
            a,b = LINES[segment]
            color = (255,220,170) if segment in (1,2) else dim
            self.scene.cv.line(frame,(643+a[0],724+a[1]),(643+b[0],724+b[1]),color,10)
        return frame

    def test_old_core_threshold_loses_three_four_strokes_in_clean_rgb_fixture(self):
        former = RegionReader(self.config,self.config)
        former.SCORE_CORE_FRACTION = .8
        for digit in (3,4):
            with self.subTest(digit=digit):
                frame = self.uneven(digit)
                before,after = former.observe(frame)['home'],self.reader.observe(frame)['home']
                self.assertEqual(before['mask_value'],digit)
                self.assertEqual(before['score_local']['value'],digit)
                self.assertEqual(before['score_core']['value'],1)
                self.assertEqual(before['reason'],'score_mask_disagreement')
                self.assertIsNone(before['value'])
                self.assertEqual(after['score_core']['value'],digit)
                self.assertEqual(after['value'],digit)

    def test_all_clean_digits_retain_uneven_strokes_without_changing_other_fields(self):
        for dim in ((255,170,130),(255,180,140)):
            for digit in range(10):
                with self.subTest(dim=dim,digit=digit):
                    frame = self.uneven(digit,dim)
                    copy = frame.copy()
                    observed = self.reader.observe(frame)
                    self.assertEqual(observed['home']['value'],digit)
                    self.assertEqual(observed['home']['score_core']['value'],digit)
                    self.assertEqual(observed['away']['value'],1)
                    self.assertEqual([observed[name]['value'] for name in
                        ('minutes_tens','minutes_units','seconds_tens','seconds_units')],[1,7,5,1])
                    np.testing.assert_array_equal(frame,copy)

    def test_actual_shadow_confirms_recovered_scores_and_keeps_missing_age_explicit(self):
        shadow = ShadowReader(self.config,self.config,LayoutPlan([{'start':0,'layout':'mmss'}]))
        frames = [self.uneven(8)]*3 + [self.uneven(3)]*3
        missing = self.uneven(3);missing[690:860,610:735] = (180,130,110)
        frames += [missing]*12 + [self.uneven(4)]*3
        for index,source in enumerate(frames):
            frame = source.copy();frame[0,0] = (index,0,0)
            row = shadow.read(frame.tobytes(),index/10)
            self.assertIsNone(row['error'])
            home = row['fields']['home']
            if index == 5:
                self.assertEqual((home['value'],home['status']),(3,'confirmed'))
            if 6 <= index <= 17:
                self.assertIsNone(home['observed'])
                self.assertEqual((home['value'],home['status']),(3,'held'))
                self.assertEqual(home['age'],round((index-5)/10,3))
                self.assertEqual(home['stale'],index >= 15)
            if index:
                self.assertEqual(row['fields']['clock']['status'],'confirmed')
                self.assertEqual(row['fields']['away']['status'],'confirmed')
        self.assertEqual((home['value'],home['status'],home['age']),(4,'confirmed',0))


if __name__ == '__main__':
    unittest.main()
