"""Controlled source timeline, unavailable fields and real encoder bundle checks."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from candidate_state import clock_observation, LayoutPlan
from scripts.generate_controlled_recording import (FPS, TOTAL_FRAMES, WIDTH, HEIGHT,
    LAYOUT_PLAN, Renderer, frame_state, generate, write_all)

ROOT = Path(__file__).resolve().parents[1]


class ControlledScenario(unittest.TestCase):
    def test_full_frame_grid_and_layouts_are_consistent(self):
        plan = LayoutPlan(LAYOUT_PLAN)
        for index in range(TOTAL_FRAMES):
            state = frame_state(index)
            self.assertEqual(state['source_frame'], index)
            self.assertAlmostEqual(state['t'], index/FPS, places=5)
            self.assertEqual(state['layout'], plan.at(index/FPS))
            clock, reason = clock_observation(state['clock_slots'],state['layout'])
            self.assertIsNone(reason)
            self.assertEqual(clock.text, state['intended']['clock'])
        for bad in (-1,TOTAL_FRAMES,True,1.5):
            with self.subTest(index=bad),self.assertRaises(ValueError):
                frame_state(bad)

    def test_both_score_sweeps_show_every_digit_for_two_seconds(self):
        for field,start in [('home',10),('away',30)]:
            for digit in range(10):
                for offset in (0,2*FPS-1):
                    state = frame_state((start+digit*2)*FPS+offset)
                    self.assertEqual(state['visible'][field],digit)
                    self.assertEqual(state['visible']['away' if field=='home' else 'home'],0)

    def test_pauses_tenths_corrections_and_recovery_boundaries(self):
        at = lambda seconds: frame_state(round(seconds*FPS))
        self.assertEqual(at(50)['visible']['clock'],'19:59')
        self.assertEqual(at(59)['visible']['clock'],'19:50')
        self.assertEqual(at(60)['visible']['clock'],'19:50')
        self.assertEqual(at(69.9)['visible']['clock'],'19:50')
        self.assertEqual(at(70)['visible']['clock'],'00:29.9')
        self.assertEqual(at(70.1)['visible']['clock'],'00:29.8')
        self.assertEqual(frame_state(90*FPS-1)['visible']['clock'],'00:10.0')
        self.assertEqual(at(90)['visible'],dict(clock='05:00',home=6,away=9))
        self.assertEqual(at(93)['visible'],dict(clock='05:00',home=9,away=6))
        self.assertEqual(at(96)['visible'],dict(clock='20:00',home=0,away=0))
        self.assertEqual(at(115)['visible'],dict(clock='05:05',home=3,away=4))
        self.assertEqual(frame_state(TOTAL_FRAMES-1)['visible']['clock'],'05:01')

    def test_missing_fields_keep_intention_separate_from_visible_truth(self):
        blank,covered = frame_state(105*FPS),frame_state(110*FPS)
        self.assertEqual(blank['intended']['clock'],'05:15')
        self.assertIsNone(blank['visible']['clock'])
        self.assertEqual(blank['visibility']['clock'],'blank')
        self.assertEqual(blank['visible']['home'],3)
        self.assertEqual(covered['intended']['home'],3)
        self.assertIsNone(covered['visible']['home'])
        self.assertEqual(covered['visibility']['home'],'covered')
        self.assertEqual(covered['visible']['clock'],'05:10')

    def test_counter_changes_outside_recognition_crop_without_mutating_cached_board(self):
        renderer = Renderer(json.loads((ROOT/'calibration.json').read_text()))
        first = renderer.render(frame_state(0))
        second = renderer.render(frame_state(1))
        self.assertEqual(len(first),WIDTH*HEIGHT*3)
        self.assertNotEqual(first,second)
        # All changes in this static alignment phase are below the entire panel.
        self.assertEqual(first[:905*WIDTH*3],second[:905*WIDTH*3])
        renderer.render(frame_state(70*FPS))
        self.assertEqual(first,renderer.render(frame_state(0)))

    def test_short_pipe_writes_do_not_drop_frame_bytes(self):
        class ShortWriter:
            def __init__(self): self.result=bytearray()
            def write(self,data):
                count=min(7,len(data));self.result.extend(data[:count]);return count
        sink=ShortWriter();write_all(sink,b'frame pixels'*20)
        self.assertEqual(sink.result,b'frame pixels'*20)
        class StoppedWriter:
            def write(self,data): return 0
        with self.assertRaises(BrokenPipeError):write_all(StoppedWriter(),b'frame')


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg tools required')
class ControlledBundle(unittest.TestCase):
    def test_encoder_manifest_hashes_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'bundle with spaces'
            subprocess.run([sys.executable,str(ROOT/'scripts/generate_controlled_recording.py'),
                            '--frames','12','--output',str(output)],check=True,capture_output=True)
            manifest=json.loads((output/'timeline.json').read_text())
            self.assertFalse(manifest['complete_scenario'])
            self.assertEqual(manifest['frame_count'],12)
            self.assertEqual(manifest['duration'],.2)
            self.assertEqual(len(manifest['frames']),12)
            self.assertEqual(manifest['probe']['streams'][0]['nb_read_frames'],'12')
            self.assertEqual(manifest['video_sha256'],hashlib.sha256((output/'recording.mp4').read_bytes()).hexdigest())
            self.assertEqual(manifest['generator_sha256'],hashlib.sha256((ROOT/'scripts/generate_controlled_recording.py').read_bytes()).hexdigest())
            self.assertEqual((output/'reference-calibration.json').read_bytes(),(ROOT/'calibration.json').read_bytes())
            self.assertEqual(json.loads((output/'source-clock-layout-plan.json').read_text()),[{'start':0,'layout':'mmss'}])
            self.assertFalse((output/'INCOMPLETE.txt').exists())
            self.assertIn('PREFIX ONLY',(output/'README.txt').read_text())
            original=(output/'recording.mp4').read_bytes()
            with self.assertRaises(FileExistsError):generate(output,12)
            self.assertEqual((output/'recording.mp4').read_bytes(),original)

    def test_encoder_failure_leaves_explicit_incomplete_marker(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'failed'
            with patch('scripts.generate_controlled_recording.subprocess.Popen',side_effect=OSError('unavailable encoder')):
                with self.assertRaises(OSError):generate(output,1)
            self.assertTrue((output/'INCOMPLETE.txt').exists())
            self.assertFalse((output/'timeline.json').exists())


if __name__=='__main__':unittest.main()
