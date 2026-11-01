"""Strong colour evidence rejects blurred mixtures without choosing a replacement."""
import json
from pathlib import Path
import unittest

import numpy as np

from candidate_state import LayoutPlan
from exposure_stress import ExposureScene, LINES, STROKES
from region_reader import RegionReader
from shadow import ShadowReader

ROOT = Path(__file__).resolve().parents[1]


class ChromaticScores(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT/'calibration.json').read_text())
        cls.reader = RegionReader(cls.config,cls.config)

    def test_blurred_orange_one_five_six_conflicts_remain_unavailable(self):
        scene = ExposureScene(self.config,'orange')
        for old,new,third in ((1,5,9),(5,1,9),(1,6,8),(6,1,8)):
            with self.subTest(old=old,new=new):
                frame = scene.transform(scene.mixed(old,new,.5),'blur')
                evidence = self.reader.observe(frame)['home']
                self.assertEqual(evidence['mask_value'],third)
                self.assertIsNone(evidence['score_core']['value'])
                self.assertEqual(evidence['score_local']['value'],third)
                self.assertEqual(evidence['score_chroma']['value'],1)
                self.assertIsNone(evidence['value'])
                self.assertEqual(evidence['reason'],'score_mask_disagreement')

    def test_clean_red_orange_and_white_are_retained_including_blur(self):
        for color in ('white','orange','red'):
            scene = ExposureScene(self.config,color)
            for digit in range(10):
                for variant in ('none','blur','dim','shift'):
                    with self.subTest(color=color,digit=digit,variant=variant):
                        frame = scene.transform(scene.endpoint(digit),variant)
                        copy = frame.copy();evidence = self.reader.observe(frame)['home']
                        self.assertEqual(evidence['value'],digit)
                        if color=='white':
                            self.assertIsNone(evidence['score_chroma']['value'])
                            self.assertEqual(evidence['score_chroma']['reason'],'neutral_cores')
                        else:
                            self.assertEqual(evidence['score_chroma']['value'],digit)
                        np.testing.assert_array_equal(frame,copy)

    def test_clean_close_colour_strokes_keep_three_and_four_available(self):
        scene = ExposureScene(self.config,'orange')
        for digit in (3,4):
            with self.subTest(digit=digit):
                frame = scene.base.copy()
                frame[690:860,610:735] = (180,130,110)
                for segment in STROKES[digit]:
                    a,b = LINES[segment]
                    color = (255,165,100) if segment in (1,2) else (255,175,120)
                    scene.cv.line(frame,(643+a[0],724+a[1]),(643+b[0],724+b[1]),color,10)
                evidence = self.reader.observe(frame)['home']
                self.assertEqual(evidence['mask_value'],digit)
                self.assertEqual(evidence['score_core']['value'],digit)
                self.assertEqual(evidence['score_chroma']['value'],digit)
                self.assertEqual(evidence['value'],digit)

    def test_shadow_holds_age_through_persistent_blur_then_confirms_clean_recovery(self):
        scene = ExposureScene(self.config,'orange')
        reader = ShadowReader(self.config,self.config,LayoutPlan([{'start':0,'layout':'mmss'}]))
        sources = [scene.endpoint(1)]*3 + [scene.transform(scene.mixed(1,5,.5),'blur')]*12 + [scene.endpoint(5)]*3
        for index,source in enumerate(sources):
            frame = source.copy();frame[0,0] = (index,0,0)
            row = reader.read(frame.tobytes(),index/10)
            self.assertIsNone(row['error'])
            home = row['fields']['home']
            if 3 <= index <= 14:
                self.assertIsNone(home['observed'])
                self.assertEqual((home['value'],home['status']),(1,'held'))
                self.assertEqual(home['age'],round((index-2)/10,3))
                self.assertEqual(home['stale'],index >= 12)
            if index:
                self.assertEqual(row['fields']['clock']['status'],'confirmed')
                self.assertEqual(row['fields']['away']['status'],'confirmed')
        self.assertEqual((home['value'],home['status'],home['age']),(5,'confirmed',0))

    def test_coloured_zero_rim_cannot_add_a_middle_segment_after_normalization(self):
        scene = ExposureScene(self.config,'orange')
        frame = scene.base.copy()
        # Thick, less saturated LED cores with a saturated outer rim. A thin
        # red middle glow is below the primary zero's on-segment support.
        for segment in range(6):
            a,b = LINES[segment]
            a,b = (643+a[0],724+a[1]),(643+b[0],724+b[1])
            scene.cv.line(frame,a,b,(255,100,0),16)
            scene.cv.line(frame,a,b,(255,180,100),10)
        scene.cv.line(frame,(658,776),(701,776),(230,90,70),4)
        evidence = self.reader.observe(frame)['home']
        self.assertEqual(evidence['mask_value'],0)
        self.assertEqual(evidence['score_chroma']['mask_value'],8)
        self.assertIsNone(evidence['score_chroma']['value'])
        self.assertEqual(evidence['score_chroma']['reason'],'unsupported_added_segments')
        self.assertEqual(evidence['value'],0)

    def test_chromatic_alternative_cannot_rescue_a_primary_crop_rejection(self):
        scene = ExposureScene(self.config,'orange')
        frame = scene.endpoint(0).copy()
        # Dim red edge texture contacts the primary crop, but not the stronger
        # chromatic mask. A valid alternative zero must still never fill it in.
        frame[740:790,616:642] = (230,170,80)
        evidence = self.reader.observe(frame)['home']
        self.assertIsNone(evidence['mask_value'])
        self.assertEqual(evidence['reason'],'edge_foreground')
        self.assertEqual(evidence['score_chroma']['value'],0)
        self.assertIsNone(evidence['value'])


if __name__ == '__main__':
    unittest.main()
