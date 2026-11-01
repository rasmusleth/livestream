"""Optional experiment tests: run with the isolated OpenCV/NumPy environment."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import json
from pathlib import Path

import numpy as np
from compare_readers import assemble, confirmed_rows, RegionReader, evaluate, evaluate_fields
from candidate_state import CandidateState, LayoutPlan
from shadow import ShadowReader
from reader import PATTERNS


class ComparisonSafety(unittest.TestCase):
    def test_independent_metrics_do_not_count_held_clock_as_fresh(self):
        state=CandidateState()
        names=('minutes_tens','minutes_units','seconds_tens','seconds_units','home','away')
        evidence={name:{'value':value} for name,value in zip(names,(1,7,5,1,0,1))}
        rows=[state.update(evidence,0,layout='mmss',frame_id='a'),
              state.update(evidence,.1,layout='mmss',frame_id='b')]
        evidence['minutes_tens']={'value':None,'reason':'edge_foreground'}
        rows.append(state.update(evidence,.2,layout='mmss',frame_id='c'))
        metrics=evaluate_fields(rows,[{'t':.2,'values':{'clock':'17:50','home':0,'away':1}}],10)
        self.assertEqual(metrics['clock']['fresh_confirmed'],1)
        self.assertEqual(metrics['clock']['reviewed_fresh_wrong'],0)
        self.assertIsNone(metrics['clock']['reviewed'][0]['fresh_correct'])
        self.assertTrue(metrics['away']['reviewed'][0]['fresh_correct'])

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

    def clock_fixture(self, digits=(4,6,8,'blank')):
        # Independent full-glyph drawings, including strokes to the left of the
        # former probe boxes. Brown texture stays below the bright LED signal.
        frame=np.full((1080,1920,3),[164,105,70],np.uint8)
        frame[:,::3,0]=156;frame[:,1::3,0]=172
        strokes=[(0,0,84,12),(72,0,84,68),(72,68,84,136),(0,124,84,136),
                 (0,68,12,136),(0,0,12,68),(0,62,84,74)]
        active={4:(1,2,5,6),6:(0,2,3,4,5,6),7:(0,1,2),8:(0,1,2,3,4,5,6)}
        for value,x in zip(digits,(725,842,994,1100)):
            if value == 'blank':continue
            for segment in active[value]:
                x1,y1,x2,y2=strokes[segment]
                frame[524+y1:524+y2,x+x1:x+x2]=[255,160,70]
        return frame

    def test_clock_windows_retain_wide_left_strokes_and_reject_colon(self):
        frame=self.clock_fixture()
        # Physical colon between slots 2 and 3, deliberately outside digit ROIs.
        frame[600:610,956:968]=[255,160,70]
        frame[625:635,956:968]=[255,160,70]
        evidence=self.reader.inspect(self.reader.masks(frame))
        self.assertEqual([evidence[name]['value'] for name in list(evidence)[:4]],
                         [4,6,8,'blank'])

    def test_shared_clock_floor_rejects_blank_texture_without_weakening_edge_guard(self):
        frame=self.clock_fixture()
        evidence=self.reader.inspect(self.reader.masks(frame))
        self.assertEqual(evidence['seconds_units']['value'],'blank')
        shifted=self.reader.cv.warpAffine(frame,np.float32([[1,0,-12],[0,1,0]]),(1920,1080))
        rejected=self.reader.inspect(self.reader.masks(shifted))['minutes_tens']
        self.assertIsNone(rejected['value'])
        self.assertEqual(rejected['reason'],'edge_foreground')

    def test_missing_required_digit_never_becomes_a_different_clock_format(self):
        frame=self.clock_fixture(('blank',6,8,'blank'))
        evidence=self.reader.inspect(self.reader.masks(frame))
        state=CandidateState()
        for i in range(4):row=state.update(evidence,i/10,layout='seconds_tenths',frame_id=str(i))
        self.assertIsNone(row['fields']['clock']['value'])
        self.assertEqual(row['fields']['clock']['reason'],'layout_mismatch')

    def test_rgb_tenths_progression_confirms_observed_value_and_holds_during_loss(self):
        config=json.loads((Path(__file__).resolve().parents[1]/'calibration.json').read_text())
        reader=ShadowReader(config,config,LayoutPlan([{'start':0,'layout':'seconds_tenths'}]))
        for i,tenth in enumerate((8,7,6)):
            row=reader.read(self.clock_fixture((4,6,tenth,'blank')).tobytes(),i/10)
            self.assertIsNone(row['error'])
        self.assertEqual(row['fields']['clock']['value'],'00:46.6')
        self.assertEqual(row['fields']['clock']['status'],'confirmed')
        missing=self.clock_fixture(('blank',)*4).tobytes()
        reader.read(missing,.3)
        held=reader.read(missing,1.3)['fields']['clock']
        self.assertEqual(held['value'],'00:46.6')
        self.assertEqual(held['status'],'held')
        self.assertEqual(held['age'],1.1)

    def test_malformed_ocr_does_not_get_padded_into_a_reading(self):
        mask=np.zeros((100,70),np.uint8);mask[10:90,50:60]=255
        with patch('compare_readers.subprocess.run',return_value=SimpleNamespace(stdout=b'1751x\n')):
            value,digits=self.reader.ocr([mask]*6)
        self.assertIsNone(value)
        self.assertEqual(digits,[None]*6)

    def score_fixture(self, digit=0, color=(255,250,255), halo=False):
        # Independent slanted LED strokes, drawn as lines rather than sampled
        # from the recognizer's normalized segment rectangles. No footage.
        frame=np.full((1080,1920,3),[150,95,100],np.uint8)
        lines=[((18,8),(64,8)),((68,14),(64,48)),((63,57),(59,91)),
               ((12,98),(53,98)),((7,90),(11,56)),((12,47),(16,14)),((15,52),(58,52))]
        for x,y in ((643,724),(1319,729)):
            if halo:
                frame[y-4:y+110,x-4:x+80]=[210,95,125]
                self.reader.cv.line(frame,(x+15,y+52),(x+58,y+52),(248,95,130),8)
            for bit,(a,b) in zip(PATTERNS[digit],lines):
                if bit=='0':continue
                a,b=(x+a[0],y+a[1]),(x+b[0],y+b[1])
                if halo:self.reader.cv.line(frame,a,b,(255,95,130),18)
                self.reader.cv.line(frame,a,b,color,10)
        return frame

    def test_score_white_cores_reject_red_glow_inside_hollow_zero(self):
        frame=self.score_fixture(halo=True)
        evidence=self.reader.inspect(self.reader.masks(frame))
        # The pre-fix mask reads both as 8: red middle glow survives while the
        # white LED centres are discarded by the red-minus-blue gate.
        self.assertEqual((evidence['home']['value'],evidence['away']['value']),(0,0))
        state=CandidateState()
        for i in range(3):
            row=state.update(evidence,i/10,layout='mmss',frame_id=str(i))
        for name in ('home','away'):
            self.assertEqual(row['fields'][name]['value'],0)
            self.assertEqual(row['fields'][name]['status'],'confirmed')

    def test_all_score_digits_with_red_or_white_led_cores(self):
        for color in ((255,250,255),(255,100,0),(255,0,0)):
            for digit in range(10):
                with self.subTest(color=color,digit=digit):
                    evidence=self.reader.inspect(self.reader.masks(self.score_fixture(digit,color)))
                    self.assertEqual((evidence['home']['value'],evidence['away']['value']),(digit,digit))

    def test_low_contrast_score_texture_holds_with_age_then_recovers(self):
        config=json.loads((Path(__file__).resolve().parents[1]/'calibration.json').read_text())
        reader=ShadowReader(config,config,LayoutPlan([{'start':0,'layout':'mmss'}]))
        for i in range(2):
            frame=self.score_fixture(halo=True);frame[0,0,0]+=i
            row=reader.read(frame.tobytes(),i/10)
        self.assertEqual(row['fields']['home']['value'],0)
        for i in range(2,5):
            frame=self.score_fixture(8,(166,95,100));frame[0,0,0]+=i
            row=reader.read(frame.tobytes(),i/10)
            for name in ('home','away'):
                field=row['fields'][name]
                self.assertIsNone(field['observed'])
                self.assertEqual((field['value'],field['status']),(0,'held'))
                self.assertEqual(field['age'],round((i-1)/10,3))
        for i in range(5,8):
            frame=self.score_fixture(8);frame[0,0,0]+=i
            row=reader.read(frame.tobytes(),i/10)
        for name in ('home','away'):
            self.assertEqual((row['fields'][name]['value'],row['fields'][name]['status']),(8,'confirmed'))

    def test_white_score_cropping_keeps_the_existing_guard(self):
        frame=self.score_fixture()
        shifted=self.reader.cv.warpAffine(frame,np.float32([[1,0,0],[0,1,-40]]),(1920,1080))
        evidence=self.reader.inspect(self.reader.masks(shifted))
        for name in ('home','away'):
            self.assertIsNone(evidence[name]['value'])
            self.assertEqual(evidence[name]['reason'],'edge_foreground')


if __name__=='__main__':unittest.main()
