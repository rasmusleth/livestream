"""Generated RGB exposure sequences for the diagnostic candidate; no capture or output.

A mixed rendering has two source digits, not a ground-truth score. Report fresh
confirmations on it separately from correctness on clean generated endpoints.
"""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from candidate_state import CandidateState

# Independent slanted LED drawing, not the reader's patterns or sample areas.
STROKES = {0: (0, 1, 2, 3, 4, 5), 1: (1, 2), 2: (0, 1, 3, 4, 6),
           3: (0, 1, 2, 3, 6), 4: (1, 2, 5, 6), 5: (0, 2, 3, 5, 6),
           6: (0, 2, 3, 4, 5, 6), 7: (0, 1, 2),
           8: (0, 1, 2, 3, 4, 5, 6), 9: (0, 1, 2, 3, 5, 6)}
LINES = (((18, 8), (64, 8)), ((68, 14), (64, 48)), ((63, 57), (59, 91)),
         ((12, 98), (53, 98)), ((7, 90), (11, 56)), ((12, 47), (16, 14)),
         ((15, 52), (58, 52)))
COLORS = {'white': (255, 250, 255), 'orange': (255, 100, 0), 'red': (255, 0, 0)}


class ExposureScene:
    """Fixed synthetic geometry for the tracked reference panel, not footage."""
    def __init__(self, config, color='white'):
        import cv2
        import numpy as np
        self.cv, self.np = cv2, np
        if config != json.loads((ROOT / 'calibration.json').read_text()):
            raise ValueError('Generated scene requires the tracked reference geometry')
        if color not in COLORS:
            raise ValueError('Unknown LED colour')
        self.color = color
        self.background = np.full((1080, 1920, 3), [150, 95, 100], np.uint8)
        # The clock stays 17:51 while only home changes; away remains 1.
        self.base = self.background.copy()
        for x, digit in zip((735, 845, 990, 1110), (1, 7, 5, 1)):
            self.draw(self.base, digit, x, 524, (255, 160, 70), scale=1.3)
        self.draw(self.base, 1, 1319, 729, COLORS[color])
        self.cache = {}

    def draw(self, frame, digit, x, y, rgb, scale=1):
        for stroke in STROKES[digit]:
            a, b = LINES[stroke]
            a = (x + round(a[0] * scale), y + round(a[1] * scale))
            b = (x + round(b[0] * scale), y + round(b[1] * scale))
            self.cv.line(frame, a, b, rgb, round(10 * scale))

    def endpoint(self, digit):
        if type(digit) is not int or digit not in STROKES:
            raise ValueError('Expected a one-digit generated score')
        if digit not in self.cache:
            frame = self.base.copy()
            self.draw(frame, digit, 643, 724, COLORS[self.color])
            self.cache[digit] = frame
        return self.cache[digit]

    def mixed(self, old, new, weight):
        if type(weight) not in (int, float) or not 0 < weight < 1:
            raise ValueError('Mixed exposure weight must be strictly between zero and one')
        # Linear encoded RGB is a controlled drawing, not a camera exposure model.
        return self.np.rint((1-weight)*self.endpoint(old).astype(float)
                            + weight*self.endpoint(new).astype(float)).astype(self.np.uint8)


def sequence(reader, scene, old, new, weight):
    if old == new:
        raise ValueError('An exposure sequence needs two different source scores')
    before, after = scene.endpoint(old), scene.endpoint(new)
    mixed = scene.mixed(old, new, weight)
    # Three repeated mixed frames deliberately test persistent ambiguous input.
    phases = [('before', before, old)]*3 + [('mixed', mixed, None)]*3
    phases += [('after', after, new)]*3 + [('missing', scene.base, None)]*3
    phases += [('recovery', after, new)]*3
    state = CandidateState()
    rows = []
    for index, (phase, source, expected) in enumerate(phases):
        frame = source.copy()
        # Tiny variation outside every region avoids identical-payload holds.
        # It models no particular sensor; duplicate-frame rejection stays enabled.
        frame[0, 0] = (index, 0, 0)
        evidence = reader.observe(frame)
        row = state.update(evidence, round(index/10, 3), layout='mmss',
                           frame_id=hashlib.sha256(frame.tobytes()).hexdigest())
        rows.append({'phase': phase, 'expected': expected, 'evidence': evidence, **row})
    return {'old': old, 'new': new, 'new_weight': weight, 'color': scene.color, 'rows': rows}


def summarize(cases):
    counts = Counter({key: 0 for key in (
        'clean_samples', 'clean_observed_correct', 'clean_observed_wrong', 'clean_observed_unknown',
        'clean_fresh_correct', 'clean_fresh_wrong', 'clean_held', 'clean_unknown',
        'mixed_samples', 'mixed_observed_available', 'mixed_fresh', 'mixed_held', 'mixed_unknown',
        'mixed_observed_neither_source', 'mixed_fresh_neither_source',
        'missing_samples', 'missing_observed_available', 'missing_fresh', 'missing_held', 'missing_unknown')})
    for case in cases:
        for row in case['rows']:
            field = row['fields']['home']
            observed, value, status = (field[key] for key in ('observed', 'value', 'status'))
            phase = row['phase']
            if phase in ('mixed', 'missing'):
                counts[f'{phase}_samples'] += 1
                counts[f'{phase}_observed_available'] += observed is not None
                counts[f'{phase}_' + ('fresh' if status == 'confirmed' else status)] += 1
                if phase == 'mixed':
                    sources = (case['old'], case['new'])
                    counts['mixed_observed_neither_source'] += observed is not None and observed not in sources
                    counts['mixed_fresh_neither_source'] += status == 'confirmed' and value not in sources
            else:
                expected = row['expected']
                counts['clean_samples'] += 1
                counts['clean_observed_' + ('unknown' if observed is None else
                                            'correct' if observed == expected else 'wrong')] += 1
                if status == 'confirmed':
                    counts['clean_fresh_' + ('correct' if value == expected else 'wrong')] += 1
                else:
                    counts['clean_' + status] += 1
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Ignored numeric JSON report destination')
    parser.add_argument('--color', choices=COLORS, default='white')
    pair_args = parser.add_mutually_exclusive_group()
    pair_args.add_argument('--pairs', nargs='+', default=['01', '10', '08', '80', '09', '90', '18', '81'],
                        help='Directed source-score pairs, e.g. 01 10; default covers 0/1/8/9 confusions')
    pair_args.add_argument('--all-pairs', action='store_true', help='Exercise all 90 directed score changes')
    parser.add_argument('--weights', type=float, nargs='+', default=[.25, .5, .75])
    args = parser.parse_args()
    pairs = list(itertools.permutations(range(10), 2)) if args.all_pairs else []
    if not args.all_pairs:
        for pair in args.pairs:
            if len(pair) != 2 or any(c not in '0123456789' for c in pair) or pair[0] == pair[1]:
                parser.error('Pairs must be two different ASCII digits, e.g. 01')
            pairs.append(tuple(map(int, pair)))
    if any(not 0 < weight < 1 for weight in args.weights):
        parser.error('Weights must be finite and strictly between zero and one')
    if args.output.exists():
        parser.error('Refusing to overwrite an existing report; select a new output path')
    from region_reader import RegionReader
    config = json.loads((ROOT / 'calibration.json').read_text())
    reader, scene = RegionReader(config, config), ExposureScene(config, args.color)
    cases = []
    for old, new in pairs:
        for weight in args.weights:
            cases.append(sequence(reader, scene, old, new, weight))
        print(f'{old} -> {new} processed', flush=True)
    result = {'kind': 'generated_score_exposure_stress', 'schema_version': 1,
              'fps': 10, 'calibration': config,
              'candidate_output_enabled': False,
              'versions': {'opencv': scene.cv.__version__, 'numpy': scene.np.__version__},
              'code_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in (Path(__file__).resolve(), ROOT/'region_reader.py', ROOT/'candidate_state.py')},
              'method': 'Independent slanted LED drawings blended in encoded RGB; mixed fields have no assigned physical truth. No camera or footage.',
              'summary': summarize(cases), 'cases': cases}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['summary'], indent=2), flush=True)


if __name__ == '__main__':
    main()
