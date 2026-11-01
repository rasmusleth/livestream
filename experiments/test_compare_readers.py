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

    def test_malformed_ocr_does_not_get_padded_into_a_reading(self):
        mask=np.zeros((100,70),np.uint8);mask[10:90,50:60]=255
        with patch('compare_readers.subprocess.run',return_value=SimpleNamespace(stdout=b'1751x\n')):
            value,digits=self.reader.ocr([mask]*6)
        self.assertIsNone(value)
        self.assertEqual(digits,[None]*6)


if __name__=='__main__':unittest.main()
