"""Freeze/verify private OCR benchmark inputs; optional prediction-free RGB export.

No OCR, recognition, server, camera or network access. Paths in recipes are relative
 to the repository root (absolute paths are also accepted for portable fixtures).
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from calibration import perspective_map, validate_corners
from experiments.audit_readings import FIELDS, number, valid_value

CONTRACT = ROOT / 'experiments/benchmark/contract-v1.json'
SOURCES = ('reader.py', 'region_reader.py', 'candidate_state.py', 'calibration.py',
           'capture.py', 'experiments/compare_readers.py', 'experiments/audit_readings.py',
           'experiments/exposure_stress.py', 'experiments/ocr_benchmark.py')


def read(path):
    return json.loads(Path(path).read_text())


def resolve(path):
    return ROOT / path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(path):
    path = Path(path).resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def sample_index(t, fps=10):
    if not number(t) or t < 0 or abs(t * fps - round(t * fps)) > 1e-6:
        raise ValueError('Timestamp must be on the nonnegative 10Hz sample grid')
    return round(t * fps)


def review_inventory(review, video_hash, samples):
    if review.get('video_sha256') != video_hash or review.get('fps') != 10:
        raise ValueError('Review video hash/rate mismatch')
    if not isinstance(review.get('method'), str) or not review['method'].strip():
        raise ValueError('Review provenance is required')
    result = {}
    for row in review['reviews']:
        index = sample_index(row['t'])
        if index >= samples or index in result:
            raise ValueError('Duplicate or out-of-range review')
        labels = row['fields']
        if not labels or set(labels) - set(FIELDS):
            raise ValueError('Review has invalid fields')
        for field, label in labels.items():
            if not isinstance(label, dict):
                raise ValueError('Review labels must be objects')
            if set(label) == {'value'} and valid_value(label['value'], field):
                continue
            if set(label) == {'unreadable'} and isinstance(label['unreadable'], str) and label['unreadable'].strip():
                continue
            raise ValueError('Explicit valid value or unreadable reason required')
        result[index] = labels
    if not result:
        raise ValueError('Review cannot be empty')
    return result


def window_inventory(windows, labels, samples):
    used = set()
    result = []
    for window in windows:
        start, end = sample_index(window['start']), sample_index(window['end'])
        if window['split'] not in ('development', 'verification') or not window['scenario'].strip():
            raise ValueError('Window needs split/scenario')
        if not 0 <= start <= end < samples or used.intersection(range(start, end + 1)):
            raise ValueError('Overlapping or out-of-range windows')
        used.update(range(start, end + 1))
        counts = {f: {'readable': 0, 'unreadable': 0} for f in FIELDS}
        for index in range(start, end + 1):
            if set(labels.get(index, {})) != set(FIELDS):
                raise ValueError('Every window sample needs all three explicit field reviews')
            for f in FIELDS:
                counts[f]['readable' if 'value' in labels[index][f] else 'unreadable'] += 1
        result.append({**window, 'start_index': start, 'end_index': end, 'counts': counts})
    if len({w['id'] for w in result}) != len(result):
        raise ValueError('Window IDs must be unique')
    return result


def geometry(config, template, boxes):
    validate_corners(config['board_corners'], config['reference_size'])
    validate_corners(template['board_corners'], template['reference_size'])
    mapped = perspective_map(template['board_corners'], config['board_corners'])
    width, height = template['reference_size']
    sw, sh = config['reference_size']
    if set(boxes) != set(FIELDS):
        raise ValueError('Whole-field boxes must name home, away and clock')
    result = {}
    for field, box in boxes.items():
        if len(box) != 4 or any(type(v) is not int for v in box):
            raise ValueError('Whole-field rectangles must be integer x,y,w,h')
        x, y, w, h = box
        if not (0 <= x < x+w <= width and 0 <= y < y+h <= height):
            raise ValueError('Whole-field rectangle is outside template')
        quad = [mapped(p) for p in ((x,y), (x+w,y), (x+w,y+h), (x,y+h))]
        if any(not (0 <= px < sw and 0 <= py < sh) for px, py in quad):
            raise ValueError('Mapped whole field is outside source')
        result[field] = {'rectified_xywh': box, 'source_quad': quad}
    return result


def validate_recipe(recipe):
    if recipe.get('version') != 1 or not recipe.get('recordings'):
        raise ValueError('Expected version 1 and nonempty recording list')
    ids = [r['id'] for r in recipe['recordings']]
    if len(set(ids)) != len(ids) or any(re.fullmatch(r'[a-z][a-z0-9-]*', i) is None for i in ids):
        raise ValueError('Recording IDs must be unique filename-safe names')


def export(recipe, output):
    # Explicit optional operation. Freeze and verify need only the standard library.
    validate_recipe(recipe)
    import cv2
    import numpy as np
    from experiments.compare_readers import frames
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    entries, probes, inputs = [], {}, {}
    for record in recipe['recordings']:
        config, template = (read(resolve(record[k])) for k in ('calibration', 'template'))
        inputs[record['id']] = {key: identity(resolve(record[key])) for key in ('video', 'calibration', 'template')}
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                           '-show_streams', '-show_format', '-of', 'json', str(resolve(record['video']))], text=True))
        stream = probe['streams'][0]
        if [stream['width'], stream['height']] != config['reference_size']:
            raise ValueError('Video dimensions differ from calibration')
        probes[record['id']] = probe
        geo = geometry(config, template, record['field_boxes'])
        indices = set(record['geometry_samples'])
        for w in record['windows']:
            indices.update(range(sample_index(w['start']), sample_index(w['end'])+1))
        warp = cv2.getPerspectiveTransform(np.float32(config['board_corners']), np.float32(template['board_corners']))
        count = 0
        for index, raw in enumerate(frames(resolve(record['video']), config['reference_size'], 10)):
            count = index+1
            if index not in indices:
                continue
            image = np.frombuffer(raw, np.uint8).reshape(config['reference_size'][1], config['reference_size'][0], 3)
            rectified = cv2.warpPerspective(image, warp, tuple(template['reference_size']), flags=cv2.INTER_LINEAR)
            crops = {}
            for field, item in geo.items():
                x,y,w,h = item['rectified_xywh']
                path = output / f"{record['id']}-{index:04d}-{field}.png"
                if not cv2.imwrite(str(path), cv2.cvtColor(rectified[y:y+h,x:x+w], cv2.COLOR_RGB2BGR)):
                    raise ValueError('Could not export colour crop')
                crops[field] = identity(path)
            entries.append({'recording_id': record['id'], 'index': index, 't': index/10,
                            'source_rgb_sha256': hashlib.sha256(raw).hexdigest(), 'crops': crops})
        if count != record['samples'] or any(i < 0 or i >= count for i in indices):
            raise ValueError('Decoded sample count/selected indices differ from recipe')
    result = {'recipe': identity(recipe['_path']), 'contract': identity(CONTRACT),
              'cropper': identity(Path(__file__)), 'opencv': cv2.__version__, 'numpy': np.__version__,
              'ffmpeg': subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0],
              'inputs': inputs, 'probes': probes, 'entries': entries}
    write_new(output/'index.json', result)
    return result


def freeze(recipe):
    validate_recipe(recipe)
    records, assets = [], {}
    def asset(path):
        item = identity(resolve(path))
        assets[item['path']] = item
        return item
    contract = read(CONTRACT)
    asset(CONTRACT)
    asset(recipe['_path'])
    for source in SOURCES:
        asset(source)
    for path in recipe.get('supplemental_assets', []):
        asset(path)
    crop_index = read(resolve(recipe['crop_index']))
    asset(recipe['crop_index'])
    if (crop_index['recipe']['sha256'] != digest(recipe['_path']) or
            crop_index['cropper']['sha256'] != digest(__file__) or
            crop_index['contract']['sha256'] != digest(CONTRACT)):
        raise ValueError('Crop export recipe/cropper mismatch; re-export before freezing')
    seen = set()
    for record in recipe['recordings']:
        if record['id'] in seen:
            raise ValueError('Duplicate recording ID')
        seen.add(record['id'])
        files = {key: asset(record[key]) for key in ('video', 'calibration', 'template', 'review', 'anchors', 'layout', 'baseline_report', 'geometry_review')}
        if crop_index['inputs'][record['id']] != {k: files[k] for k in ('video', 'calibration', 'template')}:
            raise ValueError('Crop source/calibration/template changed after export')
        config, template = read(resolve(record['calibration'])), read(resolve(record['template']))
        geo = geometry(config, template, record['field_boxes'])
        samples = record['samples']
        if type(samples) is not int or samples <= 0:
            raise ValueError('Expected positive decoded sample count')
        labels = review_inventory(read(resolve(record['review'])), files['video']['sha256'], samples)
        windows = window_inventory(record['windows'], labels, samples)
        if record.get('split') not in ('development', 'verification') or any(w['split'] != record['split'] for w in windows):
            raise ValueError('Keep each recording in one OCR configuration split')
        baseline = read(resolve(record['baseline_report']))
        if baseline['video_sha256'] != files['video']['sha256'] or baseline['fps'] != 10 or len(baseline['independent_rows']) != samples:
            raise ValueError('Baseline report source/grid mismatch')
        plan = read(resolve(record['layout']))
        if baseline['calibration'] != config or baseline['template'] != template or baseline['independent_layout_plan'] != plan:
            raise ValueError('Baseline calibration/template/layout differs from frozen inputs')
        from experiments.audit_readings import audit
        audit(baseline, read(resolve(record['review'])))
        checked = read(resolve(record['geometry_review']))
        if checked.get('crop_index_sha256') != digest(resolve(recipe['crop_index'])) or checked.get('recording_id') != record['id'] or checked.get('accepted') is not True or not checked.get('method', '').strip():
            raise ValueError('Prediction-free geometry review must bind this crop export')
        selected = {e['index']: e for e in crop_index['entries'] if e['recording_id'] == record['id']}
        required = set(record['geometry_samples'])
        for w in windows:
            required.update(range(w['start_index'], w['end_index']+1))
        if set(selected) != required:
            raise ValueError('Export does not cover exact requested samples')
        for entry in selected.values():
            for field in FIELDS:
                item = entry['crops'][field]
                if asset(item['path']) != item:
                    raise ValueError('Exported crop hash mismatch')
        counts = {f: {'readable': sum('value' in row.get(f,{}) for row in labels.values()),
                      'unreadable': sum('unreadable' in row.get(f,{}) for row in labels.values()),
                      'unreviewed': samples-sum(f in row for row in labels.values())} for f in FIELDS}
        records.append({'id': record['id'], 'split': record['split'], 'samples': samples, 'files': files, 'geometry': geo,
                        'windows': windows, 'review_counts': counts,
                        'baseline_audit': audit(baseline, read(resolve(record['review'])))['counts']})
    return {'version': 1, 'contract': contract, 'recordings': records,
            'reader_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'assets': list(assets.values()), 'crop_export': {k: v for k,v in crop_index.items() if k != 'entries'}}


def verify(manifest):
    for item in manifest['assets']:
        if identity(item['path']) != item:
            raise ValueError(f"Frozen input changed: {item['path']}")
    return len(manifest['assets'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('crops', 'freeze', 'verify'))
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        data = read(args.input)
        if args.action == 'verify':
            print(f"Verified {verify(data)} frozen assets; output remains disabled")
        else:
            if args.output is None:
                raise ValueError('--output is required')
            data['_path'] = str(args.input.resolve())
            result = export(data, args.output) if args.action == 'crops' else freeze(data)
            if args.action == 'freeze':
                write_new(args.output, result)
                print(f"Frozen {len(result['recordings'])} recordings / {len(result['assets'])} assets")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
