"""Exercise decoding and confirmation using generated lossless video, with no private footage."""
import json
from pathlib import Path
import shutil
import selectors
import subprocess
import sys
import tempfile
import unittest

from capture import capture_rows, recording_command
from live import ContinuousState, InputWorker

ROOT = Path(__file__).resolve().parents[1]
# Independent fixture drawings for the digits in this scenario; order is a,b,c,d,e,f,g.
STROKES = {0: (0, 1, 2, 3, 4, 5), 1: (1, 2), 2: (0, 1, 3, 4, 6),
           5: (0, 2, 3, 5, 6), 9: (0, 1, 2, 3, 5, 6)}


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools required')
class VideoPipeline(unittest.TestCase):
    def test_changes_missing_input_and_recovery(self):
        config = json.loads((ROOT / 'calibration.json').read_text())
        width, height = config['reference_size']
        initial = {'clock': '20:00', 'home': 0, 'away': 0}
        tick = {'clock': '19:59', 'home': 0, 'away': 0}
        goal = {'clock': '19:59', 'home': 0, 'away': 1}
        # Each source frame lasts .2s; the reader samples at 10 Hz.
        states = [initial, initial, tick, None, goal, goal]
        with tempfile.TemporaryDirectory(prefix='livestream-test-') as directory:
            folder = Path(directory)
            for number, state in enumerate(states):
                pixels = bytearray(bytes((25, 20, 20)) * width * height)
                if state is not None:
                    clock_digits = [int(n) for n in state['clock'] if n.isdigit()]
                    digits = dict(zip(('minutes_tens', 'minutes_units', 'seconds_tens', 'seconds_units'), clock_digits))
                    digits.update(home=state['home'], away=state['away'])
                    for name, digit in digits.items():
                        for segment in STROKES[digit]:
                            x, y = config['segment_centers'][name][segment]
                            for py in range(y - 9, y + 10):
                                start = (py * width + x - 9) * 3
                                pixels[start:start + 19 * 3] = bytes((255, 160, 160)) * 19
                (folder / f'{number:02}.ppm').write_bytes(f'P6\n{width} {height}\n255\n'.encode() + pixels)
            video = folder / 'generated.mkv'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-framerate', '5',
                            '-i', str(folder / '%02d.ppm'), '-c:v', 'ffv1', str(video)], check=True)
            output = folder / 'readings.json'
            subprocess.run([sys.executable, str(ROOT / 'reader.py'), str(video),
                            '--calibration', str(ROOT / 'calibration.json'), '--output', str(output)],
                           check=True, capture_output=True, text=True)
            data = json.loads(output.read_text())
            # Normal-speed streaming must deliver a row before decoding completes,
            # and retain exactly the same timestamped observations as batch mode.
            process = subprocess.Popen([sys.executable, str(ROOT / 'reader.py'), str(video),
                '--calibration', str(ROOT / 'calibration.json'), '--stream', '--realtime'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                with selectors.DefaultSelector() as ready:
                    ready.register(process.stdout, selectors.EVENT_READ)
                    self.assertTrue(ready.select(timeout=8), 'No streamed reading arrived')
                first = json.loads(process.stdout.readline())
                self.assertIsNone(process.poll(), 'Reader waited for the entire recording')
                remaining = process.stdout.read()
                errors = process.stderr.read()
                self.assertEqual(process.wait(timeout=10), 0, errors)
                streamed = [first] + [json.loads(line) for line in remaining.splitlines()]
                self.assertEqual(streamed, data['readings'])
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                process.stdout.close()
                process.stderr.close()
            state = ContinuousState('recording', 'generated fixture')
            worker = InputWorker(state, lambda stop: capture_rows(recording_command(video, config), config, stop))
            worker.start()
            worker.thread.join(timeout=8)
            if worker.thread.is_alive():
                worker.stop()
                self.fail('Continuous input failed to reach the end of the recording')
            snapshot = state.snapshot()
            self.assertIsNone(snapshot['error'])
            self.assertEqual(snapshot['values'], goal)
            self.assertFalse(snapshot['running'])
            self.assertFalse(snapshot['connected'])
            rows = data['readings']
            at = lambda t: rows[round(t * data['fps'])]
            self.assertEqual(len(rows), 12)
            self.assertEqual(at(0)['status'], 'unknown')
            self.assertIsNone(at(0)['values'])
            self.assertEqual(at(.1)['values'], initial)
            self.assertEqual(at(.4)['status'], 'held')
            self.assertEqual(at(.4)['values'], initial)
            self.assertEqual(at(.5)['values'], tick)
            for t in (.6, .7):
                self.assertIsNone(at(t)['raw'])
                self.assertEqual(at(t)['values'], tick)
                self.assertEqual(at(t)['status'], 'held')
            self.assertAlmostEqual(at(.7)['age'], .2)
            self.assertEqual(at(.8)['status'], 'held')
            self.assertEqual(at(.9)['values'], goal)
            self.assertEqual(at(.9)['status'], 'confirmed')
            self.assertEqual(at(.9)['age'], 0)
            self.assertEqual(rows[-1]['values'], goal)


if __name__ == '__main__':
    unittest.main()
