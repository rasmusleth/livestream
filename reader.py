"""Calibrated seven-segment reader. Only Python's standard library and FFmpeg required."""
import argparse
import json
from pathlib import Path
import subprocess

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


def analyze(video, calibration, output):
    config = json.loads(Path(calibration).read_text())
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height:format=duration', '-of', 'json', str(video)]))
    stream = probe['streams'][0]
    if [stream['width'], stream['height']] != config['reference_size']:
        raise ValueError('Video size differs from calibration; recalibrate before reading.')
    crop = config['crop']
    width, height = crop[2] // 2, crop[3] // 2
    points = regions(config)
    for segments in points.values():
        for segment in segments:
            if not segment or any(x < 0 or x >= width or y < 0 or y >= height for x, y in segment):
                raise ValueError('Segment sample lies outside crop.')
    fps = config['sample_fps']
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(video), '-an',
        '-vf', f'fps={fps},crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]},scale={width}:{height}',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']
    rows, last, candidate, count = [], None, None, 0
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        while True:
            frame = process.stdout.read(width * height * 3)
            if not frame:
                break
            if len(frame) != width * height * 3:
                raise RuntimeError('Truncated decoded frame')
            values, confidence, evidence = {}, [], {}
            for name, segments in points.items():
                levels = []
                for segment in segments:
                    on = 0
                    for x, y in segment:
                        i = (y * width + x) * 3
                        r, g, b = frame[i:i+3]
                        on += r > 220 and g > 60 and r > g * 1.03
                    levels.append(on / len(segment))
                values[name], score = recognize(levels)
                confidence.append(score)
                evidence[name] = [round(v, 2) for v in levels]
            valid = all(v is not None for v in values.values())
            raw = None
            if valid:
                minutes = values['minutes_tens'] * 10 + values['minutes_units']
                seconds = values['seconds_tens'] * 10 + values['seconds_units']
                if seconds < 60:
                    raw = {'clock': f'{minutes:02}:{seconds:02}', 'home': values['home'], 'away': values['away']}
            # Two consecutive frames must agree. A held reading is always labelled.
            if raw is not None and raw == candidate:
                count += 1
            else:
                candidate, count = raw, 1 if raw else 0
            accepted = raw is not None and count >= 2
            t = round(len(rows) / fps, 3)
            if accepted:
                last = {'values': raw, 'at': t}
            rows.append({'t': t, 'raw': raw, 'values': last['values'] if last else None,
                         'status': 'confirmed' if accepted else 'held' if last else 'unknown',
                         'age': round(t-last['at'], 3) if last else None,
                         'confidence': round(min(confidence), 3), 'segments': evidence})
        if process.wait() != 0:
            raise RuntimeError('FFmpeg decoding failed')
    result = {'video': Path(video).name, 'duration': float(probe['format']['duration']),
              'fps': fps, 'calibration': config, 'readings': rows}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, separators=(',', ':')))
    unknown = sum(row['raw'] is None for row in rows)
    print(f'{len(rows)} samples; {unknown} unrecognized ({unknown/max(1,len(rows)):.1%}). Saved {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--calibration', default='calibration.json')
    parser.add_argument('--output', default='data/readings.json')
    args = parser.parse_args()
    analyze(args.video, args.calibration, args.output)
