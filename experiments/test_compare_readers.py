"""Optional experiment tests: run with the isolated OpenCV/NumPy environment."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import json
from pathlib import Path

import numpy as np
from compare_readers import assemble, confirmed_rows, RegionReader, evaluate
from reader import PATTERNS


class ComparisonSafety(unittest.TestCase):
    def test_supported_formats_and_missing_values(self):
        self.assertEqual(assemble([1, 7, 5, 1, 0, 1]), {'clock':'17:51','home':0,'away':1})
        self.assertEqual(assemble(['blank', 9, 1, 7, 0, 1])['clock'], '09:17')
        self.assertEqual(assemble([4, 6, 8, 'blank', 1, 1])['clock'], '00:46.8')
        for values in ([1, 7, 7, 1, 0, 1], [None, 7, 5, 1, 0, 1],
                       ['blank']*6, [1, 7, 5, 1, 'blank', 1], [1, 7, 5, 1, True, 1]):
            self.assertIsNone(assemble(values))

    def test_invalid_annotation_timestamps_cannot_index_other_frames(self):
        rows=confirmed_rows([None,None],10)
        for t in (-.1,.05,float('nan'),True,.2):
            with self.subTest(t=t),self.assertRaises(ValueError):
                evaluate(rows,[{'t':t,'values':None}],10)

    def test_single_glitch_is_not_confirmed_and_holds_age(self):
        a={'clock':'17:51','home':0,'away':1}; b={'clock':'17:50','home':0,'away':1}
        rows=confirmed_rows([None,a,a,b,None,a,b,b],10)
        self.assertIsNone(rows[1]['values'])
        self.assertEqual(rows[3]['values'],a)
        self.assertEqual(rows[4]['status'],'held')
        self.assertEqual(rows[4]['age'],.2)
        self.assertEqual(rows[-1]['values'],b)

    def test_metrics_separate_stale_output_from_wrong_confirmation(self):
        truth={'clock':'17:50','home':0,'away':1}; old={**truth,'clock':'17:51'}
        rows=confirmed_rows([old,old,None],10)
        stats=evaluate(rows,[{'t':.1,'values':truth},{'t':.2,'values':truth}],10)
        self.assertEqual(stats['reviewed_fresh_wrong'],1)
        self.assertEqual(stats['reviewed_held'],1)


class WholeRegions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config=json.loads((Path(__file__).resolve().parents[1]/'calibration.json').read_text())
        cls.reader=RegionReader(config,config)

    def test_known_shapes_tolerate_translation_inside_the_region(self):
        # Independent drawing geometry; translated foreground must retain its reading.
        areas=[(0,0,64,10),(54,0,64,48),(54,48,64,96),(0,86,64,96),
               (0,48,10,96),(0,0,10,48),(0,43,64,53)]
        for digit,pattern in PATTERNS.items():
            mask=np.zeros((116,84),np.uint8)
            for bit,(x1,y1,x2,y2) in zip(pattern,areas):
                if bit=='1':mask[y1+10:y2+10,x1+10:x2+10]=255
            with self.subTest(digit=digit):
                self.assertEqual(self.reader.digit(mask)[0],digit)
                self.assertEqual(self.reader.digit(np.roll(mask,4,axis=1))[0],digit)

    def test_blank_is_distinct_from_unknown(self):
        self.assertEqual(self.reader.digit(np.zeros((100,70),np.uint8))[0],'blank')
        self.assertIsNone(self.reader.digit(np.full((100,70),255,np.uint8))[0])

    def test_crop_contact_is_rejected_before_shape_normalization(self):
        # A tall stroke with clear edges is a 1; cutting it on any side must
        # never turn the remainder into a publishable digit or an observed blank.
        mask=np.zeros((116,84),np.uint8);mask[10:106,60:70]=255
        self.assertEqual(self.reader.digit(mask)[0],1)
        crops=(mask[15:],mask[:100],mask[:,65:],mask[:,:65])
        for crop in crops:
            with self.subTest(shape=crop.shape):
                evidence=self.reader.inspect_digit(crop)
                self.assertIsNone(evidence['value'])
                self.assertEqual(evidence['reason'],'edge_foreground')

    def test_narrow_seven_and_borderline_aspect_are_unknown(self):
        seven=np.zeros((116,84),np.uint8)
        seven[10:25,30:70]=255;seven[25:106,60:70]=255
        self.assertEqual(self.reader.inspect_digit(seven)['reason'],'ambiguous_narrow_glyph')
        borderline=np.zeros((116,84),np.uint8)
        borderline[10:106,20:70]=255
        self.assertEqual(self.reader.inspect_digit(borderline)['reason'],'ambiguous_aspect')

    def test_faint_fragments_are_not_a_format_blank(self):
        mask=np.zeros((116,84),np.uint8);mask[20:23,40:43]=255
        evidence=self.reader.inspect_digit(mask)
        self.assertIsNone(evidence['value'])
        self.assertEqual(evidence['reason'],'insufficient_foreground')

    def test_repeated_clipped_observations_cannot_confirm_wrong_score(self):
        good={'clock':'17:51','home':0,'away':1}
        mask=np.zeros((116,84),np.uint8);mask[:96,60:70]=255
        bad=assemble([1,7,5,1,0,self.reader.digit(mask)[0]])
        rows=confirmed_rows([good,good,bad,bad,bad],10)
        self.assertIsNone(bad)
        self.assertEqual(rows[-1]['values'],good)
        self.assertEqual(rows[-1]['status'],'held')
        self.assertEqual(rows[-1]['age'],.3)

    def test_guard_recovers_a_glyph_above_the_old_box_but_rejects_larger_shift(self):
        frame=np.zeros((1080,1920,3),np.uint8)
        # Independent synthetic geometry: the top four rows were outside the
        # old away box, but the new guard can see the whole stroke.
        frame[714:834,1380:1390]=[255,100,0]
        mask=self.reader.masks(frame)[-1]
        self.assertEqual(self.reader.inspect_digit(mask)['value'],1)
        shifted=self.reader.cv.warpAffine(frame,np.float32([[1,0,0],[0,1,-25]]),(1920,1080))
        evidence=self.reader.inspect_digit(self.reader.masks(shifted)[-1])
        self.assertIsNone(evidence['value'])
        self.assertEqual(evidence['reason'],'edge_foreground')

    def test_malformed_ocr_does_not_get_padded_into_a_reading(self):
        mask=np.zeros((100,70),np.uint8);mask[10:90,50:60]=255
        with patch('compare_readers.subprocess.run',return_value=SimpleNamespace(stdout=b'1751x\n')):
            value,digits=self.reader.ocr([mask]*6)
        self.assertIsNone(value)
        self.assertEqual(digits,[None]*6)


if __name__=='__main__':unittest.main()
