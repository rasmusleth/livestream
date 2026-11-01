"""Generated source truth and accounting for the optional exposure stress runner."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from audit_readings import timeline
from exposure_stress import ExposureScene, sequence, summarize
from region_reader import RegionReader
from candidate_state import LayoutPlan
from shadow import ShadowReader

ROOT = Path(__file__).resolve().parents[1]


class ExposureStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT/'calibration.json').read_text())
        cls.reader = RegionReader(cls.config, cls.config)

    def test_clean_endpoints_and_missing_recovery_use_actual_candidate(self):
        scene = ExposureScene(self.config)
        case = sequence(self.reader, scene, 0, 1, .5)
        timeline({'fps': 10, 'independent_rows': case['rows']})
        rows = case['rows']
        self.assertEqual(rows[2]['fields']['home']['value'], 0)
        self.assertEqual(rows[8]['fields']['home']['value'], 1)
        last_at = .8
        for row in rows[9:13]:
            home = row['fields']['home']
            self.assertEqual(home['status'], 'held')
            self.assertEqual(home['value'], 1)
            self.assertAlmostEqual(home['age'], row['t']-last_at)
        self.assertIsNone(rows[9]['fields']['home']['observed'])
        self.assertEqual(rows[13]['fields']['home']['status'], 'confirmed')
        self.assertEqual(rows[13]['fields']['home']['age'], 0)
        # Home loss does not disturb the clean clock or away score.
        for row in rows[1:]:
            self.assertEqual(row['fields']['clock']['value'], '17:51')
            self.assertEqual(row['fields']['clock']['status'], 'confirmed')
            self.assertEqual(row['fields']['away']['value'], 1)
            self.assertEqual(row['fields']['away']['status'], 'confirmed')

    def test_blend_keeps_both_sources_without_mutating_clean_endpoint(self):
        scene = ExposureScene(self.config)
        old, new = scene.endpoint(0).copy(), scene.endpoint(1).copy()
        mixed = scene.mixed(0, 1, .5)
        different = np.any(old != new, axis=2)
        self.assertTrue(different.any())
        self.assertTrue(np.any(mixed[different] != old[different]))
        self.assertTrue(np.any(mixed[different] != new[different]))
        np.testing.assert_array_equal(scene.endpoint(0), old)
        np.testing.assert_array_equal(scene.endpoint(1), new)
        np.testing.assert_array_equal(mixed[~different], old[~different])

    def test_mixed_renderings_have_no_correctness_label(self):
        case = sequence(self.reader, ExposureScene(self.config), 0, 1, .5)
        for row in case['rows'][3:6]:
            self.assertEqual(row['phase'], 'mixed')
            self.assertIsNone(row['expected'])
        # Verify accounting with an artificial third-digit confirmation; it
        # must never be called correct or wrong physical truth for a blend.
        row = case['rows'][3]
        row['fields']['home'].update(observed=8, value=8, status='confirmed', age=0)
        counts = summarize([case])
        self.assertEqual(counts['clean_samples'], 9)
        self.assertEqual(counts['mixed_samples'], 3)
        self.assertEqual(counts['missing_samples'], 3)
        self.assertEqual(counts['mixed_observed_neither_source'], 1)
        self.assertEqual(counts['mixed_fresh_neither_source'], 1)
        self.assertEqual(counts['clean_observed_wrong'], 0)
        self.assertEqual(counts['clean_fresh_wrong'], 0)
        self.assertNotIn('mixed_correct', counts)
        self.assertNotIn('mixed_wrong', counts)

    def test_invalid_inputs_do_not_become_a_generated_transition(self):
        scene = ExposureScene(self.config)
        for digit in (True, -1, 10, '0'):
            with self.subTest(digit=digit), self.assertRaises(ValueError):
                scene.endpoint(digit)
        for weight in (0, 1, -1, float('nan'), float('inf'), True):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                scene.mixed(0, 1, weight)
        with self.assertRaises(ValueError):
            sequence(self.reader, scene, 1, 1, .5)

    def test_cli_report_preserves_an_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'report.json'
            path.write_text('existing local evidence')
            result = subprocess.run([sys.executable, str(ROOT/'experiments/exposure_stress.py'),
                                     '--output', str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Refusing to overwrite', result.stderr)
            self.assertEqual(path.read_text(), 'existing local evidence')

    def test_cli_writes_reviewable_source_bound_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'experiments/exposure_stress.py'),
                            '--pairs', '01', '--weights', '.5', '--output', str(path)],
                           capture_output=True, text=True, check=True)
            report = json.loads(path.read_text())
            self.assertFalse(report['candidate_output_enabled'])
            self.assertEqual(report['calibration'], self.config)
            self.assertEqual(len(report['cases']), 1)
            self.assertEqual(report['summary']['clean_observed_correct'], 9)
            self.assertEqual(report['summary']['clean_fresh_wrong'], 0)
            self.assertEqual(report['summary']['missing_fresh'], 0)
            self.assertEqual(set(report['code_sha256']),
                             {'experiments/exposure_stress.py', 'region_reader.py', 'candidate_state.py'})
            timeline({'fps': report['fps'], 'independent_rows': report['cases'][0]['rows']})

    def test_competing_core_digit_rejects_mixed_one_five_and_one_six(self):
        for color in ('white', 'orange', 'red'):
            scene = ExposureScene(self.config, color)
            for new, wrong in ((5, 9), (6, 8)):
                for old, target, weight in ((1, new, .25), (1, new, .5),
                                            (new, 1, .5), (new, 1, .75)):
                    with self.subTest(color=color, old=old, new=target, weight=weight):
                        evidence = self.reader.observe(scene.mixed(old, target, weight))['home']
                        self.assertEqual(evidence['mask_value'], wrong)
                        self.assertEqual(evidence['score_core']['value'], 1)
                        self.assertIsNone(evidence['value'])
                        self.assertEqual(evidence['reason'], 'score_mask_disagreement')

    def test_shadow_disagreement_holds_age_without_replacing_with_core_digit(self):
        scene = ExposureScene(self.config)
        reader = ShadowReader(self.config, self.config, LayoutPlan([{'start': 0, 'layout': 'mmss'}]))
        frames = [scene.endpoint(1)]*3 + [scene.mixed(1, 5, .25)]*3 + [scene.endpoint(5)]*3
        for index, source in enumerate(frames):
            frame = source.copy()
            frame[0, 0] = (index, 0, 0)
            row = reader.read(frame.tobytes(), index/10)
            self.assertIsNone(row['error'])
            if 3 <= index <= 6:
                home = row['fields']['home']
                self.assertEqual((home['value'], home['status']), (1, 'held'))
                self.assertAlmostEqual(home['age'], (index-2)/10)
                if index <= 5:
                    self.assertIsNone(home['observed'])
                    self.assertEqual(home['reason'], 'score_mask_disagreement')
                self.assertEqual(row['fields']['clock']['status'], 'confirmed')
                self.assertEqual(row['fields']['away']['status'], 'confirmed')
        self.assertEqual((row['fields']['home']['value'], row['fields']['home']['status']), (5, 'confirmed'))
        self.assertEqual(row['fields']['home']['age'], 0)

    def test_full_observation_retains_all_ten_clean_digits_and_clock_evidence(self):
        for color in ('white', 'orange', 'red'):
            scene = ExposureScene(self.config, color)
            for digit in range(10):
                with self.subTest(color=color, digit=digit):
                    frame = scene.endpoint(digit)
                    primary = self.reader.inspect(self.reader.masks(frame))
                    observed = self.reader.observe(frame)
                    self.assertEqual(observed['home']['value'], digit)
                    self.assertEqual(observed['home']['score_core']['value'], digit)
                    for name in ('minutes_tens', 'minutes_units', 'seconds_tens', 'seconds_units'):
                        self.assertEqual(observed[name], primary[name])


if __name__ == '__main__':
    unittest.main()
