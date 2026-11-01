"""Calibrated seven-segment reader. Only Python's standard library and FFmpeg required."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

# Segment order: top, upper right, lower right, bottom, lower left, upper left, middle.
PATTERNS = {0: '1111110', 1: '0110000', 2: '1101101', 3: '1111001',
            4: '0110011', 5: '1011011', 6: '1011111', 7: '1110000',
            8: '1111111', 9: '1111011'}


def recognize(levels):
    """Return unknown if the segment pattern is invalid or close to the threshold."""
    bits = ''.join('1' if v >= .25 else '0' for v in levels)
    value = next((n for n, pattern in PATTERNS.items() if pattern == bits), None)
    margin = min(abs(v - .25) for v in levels)
    return (value if margin >= .055 else None), round(min(1, margin / .25), 3)


def regions(config):
    cx, cy, _, _ = config['crop']
    result = {}
    for name, centers in config['segment_centers'].items():
        result[name] = [
            [(px, py) for py in range(round((y-cy-5)/2), round((y-cy+5)/2))
             for px in range(round((x-cx-5)/2), round((x-cx+5)/2))]
            for x, y in centers]
    return result


class FrameReader:
    """Recognize and confirm one cropped RGB frame at a time, without storing a video."""

    def __init__(self, config):
        _, _, w, h = config['crop']
        self.width, self.height = w // 2, h // 2
        self.frame_size = self.width * self.height * 3
        self.points = regions(config)
        for segments in self.points.values():
            for segment in segments:
                if not segment or any(x < 0 or x >= self.width or y < 0 or y >= self.height for x, y in segment):
                    raise ValueError('Segment sample lies outside crop.')
        self.last, self.candidate, self.count = None, None, 0
        self.digits = None

    def read(self, frame, t):
        if len(frame) != self.frame_size:
            raise ValueError('Truncated decoded frame')
        values, confidence, evidence = {}, [], {}
        for name, segments in self.points.items():
            levels = []
            for segment in segments:
                on = 0
                for x, y in segment:
                    i = (y * self.width + x) * 3
                    r, g, b = frame[i:i+3]
                    on += r > 220 and g > 60 and r > g * 1.03
                levels.append(on / len(segment))
            values[name], score = recognize(levels)
            confidence.append(score)
            evidence[name] = [round(v, 2) for v in levels]
        self.digits = values
        raw = None
        if all(v is not None for v in values.values()):
            minutes = values['minutes_tens'] * 10 + values['minutes_units']
            seconds = values['seconds_tens'] * 10 + values['seconds_units']
            if seconds < 60:
                raw = {'clock': f'{minutes:02}:{seconds:02}', 'home': values['home'], 'away': values['away']}
        if raw is not None and raw == self.candidate:
            self.count += 1
        else:
            self.candidate, self.count = raw, 1 if raw else 0
        accepted = raw is not None and self.count >= 2
        if accepted:
            self.last = {'values': raw, 'at': t}
        return {'t': t, 'raw': raw, 'values': self.last['values'] if self.last else None,
                'status': 'confirmed' if accepted else 'held' if self.last else 'unknown',
                'age': round(t-self.last['at'], 3) if self.last else None,
                'confidence': round(min(confidence), 3), 'segments': evidence}


def probe_recording(video, config):
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height:format=duration', '-of', 'json', str(video)]))
    stream = probe['streams'][0]
    if [stream['width'], stream['height']] != config['reference_size']:
        raise ValueError('Video size differs from calibration; recalibrate before reading.')
    return probe


def recording_rows(video, config, *, realtime=False):
    """Yield observations as frames arrive. Call probe_recording before decoding."""
    reader = FrameReader(config)
    crop = config['crop']
    fps = config['sample_fps']
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error']
    if realtime:
        command.append('-re')
    command += ['-i', str(video), '-an',
        '-vf', f'fps={fps},crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]},scale={reader.width}:{reader.height}',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        index = 0
        while True:
            frame = process.stdout.read(reader.frame_size)
            if not frame:
                break
            yield reader.read(frame, round(index / fps, 3))
            index += 1
        if process.wait() != 0:
            raise RuntimeError('FFmpeg decoding failed')
    finally:
        # Closing a stream early or pressing Ctrl+C must not orphan the decoder.
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def analyze(video, calibration, output):
    config = json.loads(Path(calibration).read_text())
    probe = probe_recording(video, config)
    rows = list(recording_rows(video, config))
    result = {'video': Path(video).name, 'duration': float(probe['format']['duration']),
              'fps': config['sample_fps'], 'calibration': config, 'readings': rows}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, separators=(',', ':')))
    unknown = sum(row['raw'] is None for row in rows)
    print(f'{len(rows)} samples; {unknown} unrecognized ({unknown/max(1,len(rows)):.1%}). Saved {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--calibration', default='calibration.json')
    parser.add_argument('--output', default=None, help='Batch JSON destination (default: data/readings.json)')
    parser.add_argument('--stream', action='store_true', help='Emit one JSON observation per line to stdout')
    parser.add_argument('--realtime', action='store_true', help='Pace streamed recording input at normal speed')
    args = parser.parse_args()
    if args.realtime and not args.stream:
        parser.error('--realtime requires --stream')
    if args.stream and args.output is not None:
        parser.error('--output is for batch mode; redirect stdout to save a stream')
    try:
        if args.stream:
            config = json.loads(Path(args.calibration).read_text())
            probe_recording(args.video, config)
            rows = recording_rows(args.video, config, realtime=args.realtime)
            try:
                for row in rows:
                    print(json.dumps(row, separators=(',', ':')), flush=True)
            finally:
                rows.close()
        else:
            analyze(args.video, args.calibration, args.output or 'data/readings.json')
    except KeyboardInterrupt:
        sys.exit(130)
