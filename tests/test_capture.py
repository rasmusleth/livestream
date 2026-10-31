"""Verify calibration guards and decoder cleanup without opening camera hardware."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from capture import camera_command, capture_rows, frame_filter

ROOT = Path(__file__).resolve().parents[1]


class CaptureSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / 'calibration.json').read_text())

    def test_device_selection_cannot_fall_back_to_default_or_audio(self):
        for device in ('', ' ', '0', 'default', 'none', 'usb video:0'):
            with self.subTest(device=device), self.assertRaises(ValueError):
                camera_command(self.config, device)
        command = camera_command(self.config, 'usb video')
        self.assertEqual(command[command.index('-i') + 1], 'usb video:none')
        for rate in (0, -1, float('nan'), float('inf')):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                camera_command(self.config, 'usb video', rate)

    def test_unexpected_capture_resolution_is_rejected_before_reading(self):
        valid = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
            '-i', 'color=size=1920x1080:rate=5:duration=0.2', '-vf', frame_filter(self.config, camera=True),
            '-f', 'null', '-'], capture_output=True, timeout=5)
        self.assertEqual(valid.returncode, 0, valid.stderr.decode())
        result = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
            '-i', 'color=size=1280x720:rate=5:duration=0.2', '-vf', frame_filter(self.config, camera=True),
            '-f', 'null', '-'], capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)

    def test_partial_pipe_reads_are_assembled_into_complete_frames(self):
        width, height = self.config['crop'][2:]
        size = width // 2 * (height // 2) * 3
        code = f"import os; frame=bytes({size}); [os.write(1,frame[n:n+997]) for n in range(0,len(frame),997)]"
        rows = list(capture_rows([sys.executable, '-c', code], self.config, threading.Event()))
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]['values'])

    def test_timeout_terminates_decoder_instead_of_holding_device(self):
        created = []
        actual_popen = subprocess.Popen
        def start(*args, **kwargs):
            process = actual_popen(*args, **kwargs)
            created.append(process)
            return process
        with patch('capture.subprocess.Popen', side_effect=start):
            rows = capture_rows([sys.executable, '-c', 'import time; time.sleep(30)'],
                                self.config, threading.Event(), frame_timeout=.2)
            with self.assertRaises(TimeoutError):
                next(rows)
        self.assertIsNotNone(created[0].poll())


if __name__ == '__main__':
    unittest.main()
