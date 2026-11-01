"""Offline comparison only. Install experiments/requirements.txt; never publishes to OBS."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from calibration import FIELDS
from reader import PATTERNS, recording_rows, probe_recording


def assemble(digits):
    """Blank leading minutes are a display format; other missing digits stay unknown."""
    a, b, c, d, home, away = digits
    if any(type(v) is not int or not 0 <= v <= 9 for v in (home, away)):
        return None
    if a == 'blank' and all(type(v) is int for v in (b, c, d)) and c < 6:
        return {'clock': f'0{b}:{c}{d}', 'home': home, 'away': away}
    if all(type(v) is int for v in (a, b, c, d)) and c < 6:
        return {'clock': f'{a}{b}:{c}{d}', 'home': home, 'away': away}
    # Observed last-minute display uses first two slots for seconds and third for tenths.
    # Operator verified seconds-and-tenths semantics for this supplied scoreboard.
    if all(type(v) is int for v in (a, b, c)) and d == 'blank' and a < 6:
        return {'clock': f'00:{a}{b}.{c}', 'home': home, 'away': away}
    return None


def confirmed_rows(raw_rows, fps):
    previous = last = None
    at = None
    result = []
    for index, raw in enumerate(raw_rows):
        t = round(index/fps, 3)
        accepted = raw is not None and raw == previous
        if accepted:
            last, at = raw, t
        result.append({'t': t, 'raw': raw, 'values': last, 'status': 'confirmed' if accepted else 'held' if last else 'unknown',
                       'age': None if last is None else round(t-at, 3)})
        previous = raw
    return result


def frames(video, size, fps, limit=None):
    width, height = size
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(video), '-an',
               '-vf', f'fps={fps}', *(['-frames:v', str(limit)] if limit else []), '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        while True:
            frame = process.stdout.read(width*height*3)
            if not frame:
                break
            if len(frame) != width*height*3:
                raise ValueError('Truncated experiment frame')
            yield frame
        if process.wait() != 0:
            raise RuntimeError('Experiment decoding failed')
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()


class RegionReader:
    def __init__(self, config, template):
        import cv2
        import numpy as np
        self.cv, self.np = cv2, np
        self.template = template
        self.size = tuple(template['reference_size'])
        self.warp = cv2.getPerspectiveTransform(np.float32(config['board_corners']), np.float32(template['board_corners']))

    def masks(self, frame):
        cv, np = self.cv, self.np
        image = cv.warpPerspective(frame, self.warp, self.size)
        result = []
        for name in FIELDS:
            x, y, w, h = self.template['digits'][name]
            patch = image[y:y+h, x:x+w].astype(np.float32)
            r, g, b = [patch[:, :, i] for i in range(3)]
            low, high = np.percentile(r, [50, 95])
            mask = ((r >= g*.95) & (r-b > 35) & (r > max(150, float(low+.6*(high-low))))).astype(np.uint8)*255
            mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            count, components, stats, _ = cv.connectedComponentsWithStats(mask)
            clean = np.zeros_like(mask)
            for i in range(1, count):
                if stats[i, cv.CC_STAT_AREA] >= 8:
                    clean[components == i] = 255
            result.append(clean)
        return result

    def digit(self, mask):
        cv, np = self.cv, self.np
        ys, xs = np.where(mask != 0)
        if len(xs) < mask.size*.008:
            return 'blank', []
        if len(xs) > mask.size*.75:
            return None, []
        x, y, w, h = cv.boundingRect(mask)
        if h < mask.shape[0]*.45:
            return None, []
        if w/h < .5:
            return 1, []
        normalized = cv.resize(mask[y:y+h, x:x+w], (64, 96), interpolation=cv.INTER_AREA)/255
        # Broad stroke areas, normalized to the observed foreground extent.
        areas = [(18, 0, 46, 16), (44, 18, 64, 40), (40, 56, 60, 78),
                 (14, 80, 38, 96), (0, 56, 20, 78), (4, 18, 24, 40), (18, 40, 38, 56)]
        levels = [float(normalized[y1:y2, x1:x2].mean()) for x1, y1, x2, y2 in areas]
        peak = max(levels)
        if peak < .1:
            return None, levels
        relative = [v/peak for v in levels]
        bits = ''.join('1' if v >= .4 else '0' for v in relative)
        digit = next((n for n, pattern in PATTERNS.items() if pattern == bits), None)
        if min(abs(v-.4) for v in relative) < .04:
            digit = None
        return digit, [round(v, 3) for v in levels]

    def read(self, masks):
        evidence = [self.digit(mask) for mask in masks]
        digits = [item[0] for item in evidence]
        return assemble(digits), digits

    def ocr(self, masks, psm=13):
        cv, np = self.cv, self.np
        tiles, active = [], []
        for i, mask in enumerate(masks):
            if np.count_nonzero(mask) < mask.size*.008:
                continue
            x, y, w, h = cv.boundingRect(mask)
            scale = 100/h
            glyph = cv.resize(mask[y:y+h, x:x+w], (max(1, round(w*scale)), 100))
            tile = cv.copyMakeBorder(255-glyph, 10, 10, 10, 10, cv.BORDER_CONSTANT, value=255)
            tiles.append(tile); active.append(i)
        if not tiles:
            return None, ['blank']*6
        sheet = np.hstack(tiles)
        ok, encoded = cv.imencode('.png', sheet)
        if not ok:
            raise ValueError('Could not encode OCR input')
        result = subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', str(psm),
            '-c', 'tessedit_char_whitelist=0123456789', '-c', 'load_system_dawg=0',
            '-c', 'load_freq_dawg=0'], input=encoded.tobytes(), capture_output=True,
            env={**os.environ, 'OMP_THREAD_LIMIT': '1'}, timeout=10, check=True)
        text = re.sub(r'\s', '', result.stdout.decode())
        digits = ['blank']*6
        if not text.isdecimal() or len(text) != len(active):
            return None, [None if i in active else 'blank' for i in range(6)]
        for i, character in zip(active, text):
            digits[i] = int(character)
        return assemble(digits), digits


def evaluate(rows, labels, fps):
    stats = {'samples': len(rows), 'raw_available': sum(r['raw'] is not None for r in rows),
             'fresh_confirmed': sum(r['status'] == 'confirmed' for r in rows)}
    checks = []
    for label in labels:
        t = label['t']
        if type(t) not in (int, float) or not math.isfinite(t) or t < 0 or abs(t*fps-round(t*fps)) > 1e-6:
            raise ValueError('Labels must use nonnegative exact sample-grid timestamps')
        index = round(t*fps)
        if index >= len(rows):
            raise ValueError('Label is beyond decoded input')
        row = rows[index]
        checks.append({'t': label['t'], 'split': label.get('split', 'unspecified'), 'expected': label['values'], 'raw': row['raw'],
                       'raw_correct': None if row['raw'] is None else row['raw'] == label['values'],
                       'output': row['values'], 'status': row['status'], 'age': row['age'],
                       'output_correct': None if row['values'] is None else row['values'] == label['values']})
    stats['reviewed'] = checks
    stats['reviewed_raw_correct'] = sum(c['raw_correct'] is True for c in checks)
    stats['reviewed_raw_wrong'] = sum(c['raw_correct'] is False for c in checks)
    stats['reviewed_raw_unknown'] = sum(c['raw_correct'] is None for c in checks)
    stats['reviewed_fresh_wrong'] = sum(c['status'] == 'confirmed' and c['output_correct'] is False for c in checks)
    stats['reviewed_held'] = sum(c['status'] == 'held' for c in checks)
    longest = run = 0
    for row in rows:
        run = 0 if row['status'] == 'confirmed' else run+1
        longest = max(longest, run)
    stats['longest_without_fresh_confirmation_s'] = round(longest/fps, 3)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--calibration', required=True, type=Path)
    parser.add_argument('--template', type=Path, default=ROOT/'calibration.json')
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ocr-psm', type=int, default=13, choices=(7, 13))
    parser.add_argument('--skip-ocr', action='store_true')
    parser.add_argument('--limit', type=int, help='Development-only maximum sample count')
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error('--limit must be positive')
    import cv2
    import numpy as np
    config = json.loads(args.calibration.read_text())
    template = json.loads(args.template.read_text())
    labels = json.loads(args.labels.read_text())
    probe_recording(args.video, config)
    fps = config['sample_fps']
    start = time.perf_counter()
    baseline = list(recording_rows(args.video, config))
    baseline_seconds = time.perf_counter()-start
    if args.limit:
        baseline = baseline[:args.limit]
        labels = [item for item in labels if item['t'] < args.limit/fps]
    candidate = RegionReader(config, template)
    raw = {'regions': [], 'ocr': []}
    timings = {'regions': [], 'ocr': []}
    for index, payload in enumerate(frames(args.video, config['reference_size'], fps, args.limit)):
        if args.limit and index >= args.limit:
            break
        frame = np.frombuffer(payload, np.uint8).reshape(config['reference_size'][1], config['reference_size'][0], 3)
        before = time.perf_counter(); masks = candidate.masks(frame); shared = time.perf_counter()-before
        before = time.perf_counter(); value, _ = candidate.read(masks)
        timings['regions'].append(shared+time.perf_counter()-before); raw['regions'].append(value)
        if not args.skip_ocr:
            before = time.perf_counter(); value, _ = candidate.ocr(masks, args.ocr_psm)
            timings['ocr'].append(shared+time.perf_counter()-before); raw['ocr'].append(value)
        if index % 200 == 0:
            print(f'{index/fps:.1f}s processed', flush=True)
    rows = {'current': baseline}
    rows.update({name: confirmed_rows(values, fps) for name, values in raw.items() if values})
    if any(len(values) != len(baseline) for values in rows.values()):
        raise ValueError('Methods produced unequal sample counts')
    with args.video.open('rb') as video_file:
        video_hash = hashlib.file_digest(video_file, 'sha256').hexdigest()
    report = {'video': args.video.name, 'video_sha256': video_hash,
              'calibration': config, 'template': template, 'labels': labels, 'ocr_psm': args.ocr_psm, 'fps': fps, 'versions': {'opencv': cv2.__version__, 'numpy': np.__version__,
              'tesseract': None if args.skip_ocr else subprocess.run(['tesseract', '--version'], capture_output=True, text=True, check=True).stdout.splitlines()[0]},
              'baseline_decode_and_read_seconds': baseline_seconds,
              'metrics': {name: evaluate(values, labels, fps) for name, values in rows.items()}, 'rows': rows}
    for name, durations in timings.items():
        if durations:
            report['metrics'][name]['processing_ms_median'] = round(statistics.median(durations)*1000, 2)
            report['metrics'][name]['processing_ms_p95'] = round(float(np.percentile(durations, 95))*1000, 2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({name: {k:v for k,v in metrics.items() if k != 'reviewed'} for name, metrics in report['metrics'].items()}, indent=2), flush=True)


if __name__ == '__main__':
    main()
