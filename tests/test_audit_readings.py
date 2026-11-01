"""Per-field review accounting and saved-timeline integrity without private footage."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from experiments.audit_readings import audit

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    rows = []
    for i in range(3):
        fields = {field: {'observed': value, 'value': value,
                         'status': 'confirmed', 'age': 0}
                  for field, value in [('home', 0), ('away', 1), ('clock', '00:44.6')]}
        if i:
            fields['clock'].update(observed='00:44.5' if i == 1 else None,
                                   status='held', age=i / 10)
        rows.append({'t': i / 10, 'fields': fields})
    return ({'video_sha256': 'a' * 64, 'fps': 10, 'independent_rows': rows},
            {'video_sha256': 'a' * 64, 'fps': 10, 'method': 'Exact source-frame inspection',
             'reviews': [
                 {'t': 0, 'fields': {'clock': {'unreadable': 'Mixed LED strokes'},
                                     'home': {'value': 0}, 'away': {'value': 2}}},
                 {'t': .1, 'fields': {'clock': {'value': '00:44.5'}}},
                 {'t': .2, 'fields': {'clock': {'value': '00:44.4'}}}]})


class FieldAudit(unittest.TestCase):
    def test_readability_is_separate_from_correctness_and_coverage(self):
        counts = audit(*fixture())['counts']
        clock = counts['clock']
        self.assertEqual((clock['readable'], clock['unreadable']), (2, 1))
        self.assertEqual((clock['fresh_correct'], clock['fresh_wrong']), (0, 0))
        self.assertEqual((clock['unreadable_fresh'], clock['unreadable_observed']), (1, 1))
        self.assertEqual((clock['observed_correct'], clock['observed_wrong'],
                          clock['observed_unknown']), (1, 0, 1))
        self.assertEqual((clock['readable_held'], clock['held_value_wrong']), (2, 2))
        self.assertEqual((counts['home']['fresh_correct'], counts['home']['unreviewed']), (1, 2))
        self.assertEqual((counts['away']['fresh_wrong'], counts['away']['unreviewed']), (1, 2))
        self.assertEqual((clock['all_observed_available'], clock['all_fresh_confirmed']), (2, 1))

    def test_unknown_and_unreadable_holds_are_not_errors(self):
        report, review = fixture()
        for row in report['independent_rows']:
            row['fields']['home'].update(value=None, observed=None, status='unknown', age=None)
        review['reviews'][1]['fields']['clock'] = {'unreadable': 'Blurred'}
        review['reviews'][2]['fields']['clock'] = {'value': '00:44.6'}
        c = audit(report, review)['counts']
        self.assertEqual((c['home']['readable_unknown'], c['home']['observed_unknown']), (1, 1))
        self.assertEqual((c['clock']['unreadable_held'], c['clock']['held_value_correct']), (1, 1))
        self.assertEqual(c['clock']['fresh_wrong'], 0)

    def test_observed_wrong_is_distinct_from_wrong_fresh(self):
        report, review = fixture()
        review['reviews'][1]['fields']['clock'] = {'value': '00:44.3'}
        c = audit(report, review)['counts']['clock']
        self.assertEqual((c['observed_wrong'], c['fresh_wrong']), (1, 0))

    def test_review_provenance_and_grid_are_required(self):
        for change in [lambda r: r.update(video_sha256='b' * 64),
                       lambda r: r.update(fps=20), lambda r: r.update(method=' '),
                       lambda r: r.update(reviews=[]),
                       lambda r: r['reviews'].append(copy.deepcopy(r['reviews'][0])),
                       lambda r: r['reviews'][0].update(t=.05),
                       lambda r: r['reviews'][0].update(t=-.1),
                       lambda r: r['reviews'][0].update(t=.3),
                       lambda r: r['reviews'][0].update(t=True),
                       lambda r: r['reviews'].__setitem__(0, None)]:
            report, review = fixture()
            change(review)
            with self.subTest(review=review), self.assertRaises(ValueError):
                audit(report, review)

    def test_labels_cannot_guess_unknown_truth_or_invalid_values(self):
        invalid = [{'value': None}, {'value': '00:60.0'}, {'value': '01:12.3'},
                   {'value': '44.6'}, {'unreadable': ''}, {'unreadable': None},
                   {'value': '00:44.6', 'unreadable': 'Blur'}, {}, None]
        for label in invalid:
            report, review = fixture()
            review['reviews'][0]['fields']['clock'] = label
            with self.subTest(label=label), self.assertRaises(ValueError):
                audit(report, review)
        for value in (True, -1, 10, 0.0, '0'):
            report, review = fixture()
            review['reviews'][0]['fields']['home'] = {'value': value}
            with self.subTest(score=value), self.assertRaises(ValueError):
                audit(report, review)

    def test_timeline_cannot_fabricate_values_or_refresh_held_age(self):
        changes = [{'value': '00:44.5'}, {'age': 0}, {'status': 'confirmed'},
                   {'status': 'unknown'}, {'age': None}, {'observed': '00:61'},
                   {'status': 'fresh'}, {'value': None}, {'age': True}]
        for change in changes:
            report, review = fixture()
            report['independent_rows'][1]['fields']['clock'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                audit(report, review)
        report, review = fixture()
        report['independent_rows'][0]['fields']['clock']['observed'] = None
        with self.assertRaises(ValueError):
            audit(report, review)

    def test_complete_timeline_and_well_formed_objects_are_required(self):
        for change in [lambda r: r.update(video_sha256='no hash'),
                       lambda r: r.update(fps=False),
                       lambda r: r['independent_rows'].pop(0),
                       lambda r: r['independent_rows'][1].update(t=.2),
                       lambda r: r['independent_rows'][0]['fields'].pop('clock'),
                       lambda r: r['independent_rows'].__setitem__(0, None)]:
            report, review = fixture()
            change(report)
            with self.subTest(report=report), self.assertRaises(ValueError):
                audit(report, review)
        for report, review in [(None, {}), ({}, [])]:
            with self.assertRaises(ValueError):
                audit(report, review)

    def test_cli_writes_provenance_and_preserves_inputs(self):
        report, review = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name for name in ('report.json', 'review.json', 'audit.json')]
            for path, obj in zip(paths, (report, review)):
                path.write_text(json.dumps(obj))
            original = [path.read_bytes() for path in paths[:2]]
            command = [sys.executable, str(ROOT / 'experiments/audit_readings.py'),
                       str(paths[0]), str(paths[1]), '--output']
            run = subprocess.run(command + [str(paths[2])], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(paths[2].read_text())
            for key, payload in zip(('report_sha256', 'review_sha256'), original):
                self.assertEqual(result[key], hashlib.sha256(payload).hexdigest())
            self.assertEqual(result['checks'][0]['fields']['clock']['review'],
                             {'unreadable': 'Mixed LED strokes'})
            for path in paths[:2]:
                run = subprocess.run(command + [str(path)], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn('must not overwrite', run.stderr)
            self.assertEqual([path.read_bytes() for path in paths[:2]], original)


if __name__ == '__main__':
    unittest.main()
