"""Strict parsing and offline state contracts using generated native results."""
from copy import deepcopy
import unittest

from candidate_state import ClockObservation, LayoutPlan
from experiments.audit_readings import FIELDS, audit
from experiments.ocr_adapter import adapt, development_record, parse_field


class WholeFieldGrammar(unittest.TestCase):
    def test_complete_clock_layouts_and_numeric_bounds(self):
        for text, layout, canonical, ticks in (
            ('00:00', 'mmss', '00:00', 0), ('99:59', 'mmss', '99:59', 59990),
            ('0:09', 'mss', '00:09', 90), ('09.0', 'seconds_tenths', '00:09.0', 90),
        ):
            self.assertEqual(parse_field('clock', text, layout),
                             (ClockObservation(canonical, ticks, layout), None))
        for layout, text in [('mmss', '19:60'), ('mss', '9:60'), ('seconds_tenths', '60.0')]:
            self.assertEqual(parse_field('clock', text, layout), (None, 'invalid_seconds'))

    def test_no_trimming_substring_matching_or_punctuation_repairs(self):
        for text in ('19.16', '19:1', '9:16', '019:16', '19:16\n', ' 19:16',
                     '１９:１６', '19:16x', '19:160', '19:16.0', '19：16'):
            with self.subTest(text=text):
                self.assertEqual(parse_field('clock', text, 'mmss'), (None, 'clock_grammar'))
        self.assertEqual(parse_field('clock', '00:48.6', 'seconds_tenths'), (None, 'clock_grammar'))
        self.assertEqual(parse_field('clock', '48.6', 'mmss'), (None, 'clock_grammar'))

    def test_score_zero_is_observed_and_unsupported_scores_remain_explicit(self):
        self.assertEqual(parse_field('home', '0', 'mmss'), (0, None))
        for text, reason in [('', 'empty_text'), ('10', 'unsupported_score_width'),
                             ('00', 'unsupported_score_width'), ('0 1', 'score_grammar'),
                             ('1\n', 'score_grammar'), ('１', 'score_grammar'),
                             ('日', 'score_grammar'), ('+1', 'score_grammar')]:
            self.assertEqual(parse_field('home', text, 'mmss'), (None, reason))


class OfflineTimeline(unittest.TestCase):
    def fixture(self, inputs):
        record = {'id': 'generated', 'samples': len(inputs), 'split': 'development',
                  'geometry': {f: {'rectified_xywh': [0, 0, 1, 1]} for f in FIELDS},
                  'files': {'video': {'sha256': 'a'*64}}}
        samples, rows = [], []
        for i, (frame, home, away, clock) in enumerate(inputs):
            base = {'recording_id': 'generated', 'index': i, 't': i/10,
                    'source_rgb_sha256': f'{frame:064x}'}
            samples.append({**base, 'crops': {f: {'sha256': 'b'*64} for f in FIELDS}})
            rows.append({**base, 'pass_index': 0, 'three_fields_ms': 3,
                         'fields': {f: {'raw_text': text, 'native_confidence': .999,
                                        'model_api_ms': 1, 'crop_sha256': 'b'*64}
                                    for f, text in zip(FIELDS, (home, away, clock))}})
        return record, samples, {'repeats': 1, 'rows': rows}, LayoutPlan([
            {'start': 0, 'layout': 'seconds_tenths'}])

    def test_duplicate_loss_stale_recovery_progression_pause_and_correction(self):
        inputs = [(0, '0', '1', '48.8'), (1, '0', '1', '48.7'), (2, '0', '1', '48.6'),
                  (2, '0', '1', '48.6')]  # Same frame cannot refresh any field.
        inputs += [(i, '10', '1', 'X') for i in range(4, 13)]
        inputs += [(13, '2', '1', '48.0'), (14, '2', '1', '48.0')]
        inputs += [(i, '2', '1', '59.9') for i in range(15, 18)]
        record, samples, raw, plan = self.fixture(inputs)
        report = adapt(record, samples, raw, plan)
        rows = [r['fields'] for r in report['independent_rows']]
        self.assertEqual(rows[2]['clock']['value'], '00:48.6')
        self.assertTrue(all(f['reason'] == 'duplicate_frame' for f in rows[3].values()))
        self.assertEqual(rows[3]['clock']['age'], .1)
        self.assertEqual(rows[12]['home']['value'], 0)
        self.assertEqual(rows[12]['home']['status'], 'held')
        self.assertEqual(rows[12]['home']['age'], 1)
        self.assertTrue(rows[12]['home']['stale'])
        self.assertTrue(rows[12]['clock']['stale'])
        self.assertEqual(rows[12]['away']['status'], 'confirmed')
        self.assertEqual(rows[13]['home']['status'], 'held')
        self.assertEqual(rows[14]['home']['value'], 2)
        self.assertEqual(rows[14]['clock']['value'], '00:48.0')
        self.assertFalse(rows[14]['clock']['stale'])
        self.assertEqual(rows[16]['clock']['value'], '00:48.0')
        self.assertEqual(rows[17]['clock']['value'], '00:59.9')
        rejected = report['raw_rows'][12]['fields']['home']
        self.assertEqual((rejected['raw_text'], rejected['native_confidence'],
                          rejected['parsed'], rejected['rejection']),
                         ('10', .999, None, 'unsupported_score_width'))
        self.assertEqual(report['raw_rows'][2]['fields']['clock']['parsed'],
                         {'text': '00:48.6', 'layout': 'seconds_tenths', 'ticks': 486})
        review = {'video_sha256': 'a'*64, 'fps': 10, 'method': 'Generated fixture',
                  'reviews': [{'t': 1.2, 'fields': {'clock': {'unreadable': 'covered'}}}]}
        counts = audit(report, review)['counts']['clock']
        self.assertEqual((counts['unreadable_held'], counts['unreadable_fresh'], counts['unreviewed']),
                         (1, 0, 17))

    def test_rejects_partial_repeated_or_mismatched_raw_results(self):
        record, samples, raw, plan = self.fixture([(0, '0', '1', ''), (1, '0', '1', '')])
        for key, value in [('index', 0), ('t', .2), ('source_rgb_sha256', 'c'*64), ('pass_index', 1)]:
            changed = deepcopy(raw)
            changed['rows'][1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                adapt(record, samples, changed, plan)
        changed = deepcopy(raw)
        changed['rows'][1]['fields']['clock']['crop_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'crop identity'):
            adapt(record, samples, changed, plan)
        with self.assertRaisesRegex(ValueError, 'every source sample'):
            adapt(record, samples, {**raw, 'rows': raw['rows'][:1]}, plan)

    def test_verification_record_and_alias_are_rejected_before_access(self):
        record, *_ = self.fixture([(0, '0', '1', '')])
        reserved = {**record, 'id': 'reserved', 'split': 'verification'}
        manifest = {'recordings': [record, reserved]}
        with self.assertRaisesRegex(ValueError, 'reserved for Task 4'):
            development_record(manifest, 'reserved')
        with self.assertRaisesRegex(ValueError, 'aliases'):
            development_record(manifest, 'generated')
