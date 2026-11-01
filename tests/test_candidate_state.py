"""Candidate-only evidence rules; no footage or optional image packages required."""
import unittest
from candidate_state import CandidateState, LayoutPlan, clock_observation

NAMES = ('minutes_tens','minutes_units','seconds_tens','seconds_units','home','away')


def evidence(slots=(4,6,8,'blank'), home=0, away=1):
    return {name: {'value':value, 'reason':None} for name,value in zip(NAMES, (*slots,home,away))}


class ClockFormats(unittest.TestCase):
    def test_layout_plan_is_explicit_and_validated(self):
        plan=LayoutPlan([{'start':0,'layout':'mmss'},{'start':10,'layout':'seconds_tenths'}])
        self.assertEqual(plan.at(9.9),'mmss')
        self.assertEqual(plan.at(10),'seconds_tenths')
        for entries in ([],{},[{'start':1,'layout':'mmss'}],
                        [{'start':0,'layout':'auto'}],[{'start':False,'layout':'mmss'}],
                        [{'start':0,'layout':'mmss'},{'start':0,'layout':'mss'}],
                        [{'start':0,'layout':'mmss'},{'start':float('nan'),'layout':'mss'}]):
            with self.subTest(entries=entries),self.assertRaises(ValueError):LayoutPlan(entries)

    def test_explicit_layout_and_slot_validity(self):
        cases = [((1,7,5,1),'mmss','17:51',10710),
                 (('blank',9,1,7),'mss','09:17',5570),
                 ((4,6,8,'blank'),'seconds_tenths','00:46.8',468)]
        for slots,layout,text,ticks in cases:
            with self.subTest(layout=layout):
                value,reason=clock_observation(slots,layout)
                self.assertEqual((value.text,value.ticks,reason),(text,ticks,None))
                for other in ('mmss','mss','seconds_tenths'):
                    if other != layout:
                        self.assertIsNone(clock_observation(slots,other)[0])
        for slots in ((None,6,8,'blank'),('blank',6,8,'blank'),(True,6,8,'blank'),
                      (6,0,1,'blank'),(1,0,6,0),('blank',9,6,0)):
            for layout in ('mmss','mss','seconds_tenths'):
                self.assertIsNone(clock_observation(slots,layout)[0])

    def test_blank_does_not_select_a_new_layout(self):
        s=CandidateState()
        for i in range(5):
            row=s.update(evidence(),i/10,layout='mmss',frame_id=str(i))
        self.assertIsNone(row['fields']['clock']['value'])
        self.assertEqual(row['fields']['clock']['reason'],'layout_mismatch')
        self.assertEqual(row['fields']['home']['value'],0)


class IndependentEvidence(unittest.TestCase):
    def setUp(self):
        self.state=CandidateState()
        self.index=0

    def update(self, slots=(4,6,8,'blank'), home=0, away=1, t=None,
               layout='seconds_tenths', frame_id=None):
        index=self.index; self.index+=1
        return self.state.update(evidence(slots,home,away),index/10 if t is None else t,
                                 layout=layout,frame_id=str(index) if frame_id is None else frame_id)['fields']

    def test_tenths_progression_confirms_only_latest_observed_value(self):
        self.assertIsNone(self.update()['clock']['value'])
        self.assertIsNone(self.update((4,6,7,'blank'))['clock']['value'])
        row=self.update((4,6,6,'blank'))
        self.assertEqual(row['clock']['value'],'00:46.6')
        self.assertEqual(row['clock']['status'],'confirmed')
        self.assertEqual(self.state.snapshot(.8)['fields']['clock']['value'],'00:46.6')
        self.assertEqual(self.state.snapshot(.8)['fields']['clock']['age'],.6)
        self.assertEqual(self.state.snapshot(.8)['fields']['clock']['reason'],'no_new_frame')

    def test_fields_confirm_independently_and_hold_with_age(self):
        self.update(home=None)
        row=self.update(home=None)
        self.assertIsNone(row['home']['value'])
        self.assertEqual(row['away']['status'],'confirmed')
        self.assertEqual(row['clock']['value'],'00:46.8')
        self.update((None,6,8,'blank'),home=0)
        row=self.update((None,6,8,'blank'),home=0)
        self.assertEqual(row['home']['status'],'confirmed')
        self.assertEqual(row['clock']['status'],'held')
        self.assertEqual(row['clock']['age'],.2)
        self.assertEqual(row['clock']['reason'],'unknown_digit')

    def test_paused_clock_and_score_correction_use_observed_repeats(self):
        self.update();self.update()
        row=self.update(home=2)
        self.assertEqual(row['home']['value'],0)
        row=self.update(home=2)
        self.assertEqual(row['home']['value'],2)
        self.assertEqual(row['clock']['value'],'00:46.8')

    def test_clock_correction_and_reset_need_three_fresh_observations(self):
        self.update();self.update()
        for i in range(2):
            row=self.update((5,9,9,'blank'))
            self.assertEqual(row['clock']['value'],'00:46.8')
        self.assertEqual(self.update((5,9,9,'blank'))['clock']['value'],'00:59.9')
        for i in range(2):
            row=self.update((0,0,0,'blank'))
            self.assertEqual(row['clock']['value'],'00:59.9')
        self.assertEqual(self.update((0,0,0,'blank'))['clock']['value'],'00:00.0')

    def test_seconds_rollover_and_pauses_allow_quantization(self):
        self.update((0,1,0,'blank'))
        self.update((0,0,9,'blank'))
        row=self.update((0,0,8,'blank'))
        self.assertEqual(row['clock']['value'],'00:00.8')
        self.update((1,0,0,0),layout='mmss')
        self.update((0,9,5,9),layout='mmss')
        row=self.update((0,9,5,9),layout='mmss')
        # Three coherent observations establish an explicit changed layout.
        self.assertEqual(row['clock']['value'],'09:59')

    def test_impossible_rate_and_single_glitch_are_not_confirmed(self):
        self.update();self.update()
        self.update((4,0,0,'blank'))
        row=self.update((4,6,6,'blank'))
        self.assertEqual(row['clock']['value'],'00:46.8')
        # Three individually plausible one-second changes over 0.2 s must
        # also satisfy the rate bound over the entire evidence window.
        self.state=CandidateState();self.index=0
        self.update((1,0,0,3),layout='mmss')
        self.update((1,0,0,2),layout='mmss')
        self.assertIsNone(self.update((1,0,0,1),layout='mmss')['clock']['value'])

    def test_duplicate_frames_and_timestamps_do_not_refresh_evidence(self):
        self.update(frame_id='same')
        row=self.update(frame_id='same')
        self.assertIsNone(row['clock']['value'])
        self.assertEqual(row['clock']['reason'],'duplicate_frame')
        self.update();self.update()
        row=self.update(frame_id='same')
        self.assertEqual(row['clock']['status'],'held')
        self.assertEqual(row['clock']['age'],.1)
        with self.assertRaises(ValueError):
            self.update(t=.4)
        with self.assertRaises(ValueError):
            self.update(t=.1)

    def test_gaps_and_unknowns_require_new_evidence_without_invented_ticks(self):
        self.update();self.update()
        row=self.update((4,6,7,'blank'),t=2)
        self.assertEqual(row['clock']['value'],'00:46.8')
        self.assertEqual(row['clock']['age'],1.9)
        self.update((None,6,6,'blank'),t=2.1)
        self.assertEqual(self.state.snapshot(5)['fields']['clock']['value'],'00:46.8')
        self.assertEqual(self.state.snapshot(5)['fields']['clock']['age'],4.9)
        self.assertTrue(self.state.snapshot(5)['fields']['clock']['stale'])
        self.update((4,6,5,'blank'),t=5.1)
        self.update((4,6,4,'blank'),t=5.2)
        row=self.update((4,6,3,'blank'),t=5.3)
        self.assertEqual(row['clock']['value'],'00:46.3')

    def test_clock_never_combines_partial_frames(self):
        for slots in ((None,6,8,'blank'),(4,None,8,'blank'),(4,6,None,'blank'))*3:
            self.assertIsNone(self.update(slots)['clock']['value'])

    def test_unknown_breaks_repeat_and_a_changed_layout_needs_new_evidence(self):
        self.update();self.update()
        self.update((1,0,0,0),layout='mmss')
        self.update((1,0,0,0),layout='mmss')
        row=self.update((None,0,0,0),layout='mmss')
        self.assertEqual(row['clock']['value'],'00:46.8')
        for _ in range(2):
            self.assertEqual(self.update((1,0,0,0),layout='mmss')['clock']['value'],'00:46.8')
        row=self.update((1,0,0,0),layout='mmss')
        self.assertEqual(row['clock']['value'],'10:00')
        self.assertEqual(row['clock']['layout'],'mmss')

    def test_invalid_timing_and_identity_are_rejected_without_mutation(self):
        for t in (True,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):self.update(t=t)
        with self.assertRaises(ValueError):self.update(frame_id='')
        self.assertIsNone(self.state.t)


if __name__ == '__main__':
    unittest.main()
