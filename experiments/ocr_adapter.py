"""Run strict whole-field OCR and confirmation on one frozen development recording."""
import argparse
import os
from dataclasses import asdict
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from candidate_state import CandidateState, ClockObservation, LAYOUTS, LayoutPlan
from experiments.audit_readings import FIELDS, audit, number
from experiments.ocr_benchmark import export, geometry, identity, read, write_new
from experiments.ocr_feasibility import (NETWORK_POLICY, RUNTIME_LOCK, check_model,
                                         native_result, run_worker_trials)

TINY_SPEC = ROOT/'experiments/ocr/tiny-model.json'
GRAMMARS = {'mmss': r'([0-9]{2}):([0-9]{2})', 'mss': r'([0-9]):([0-9]{2})',
            'seconds_tenths': r'([0-9]{2})\.([0-9])'}
CONFIG = {'grammar_version': 1, 'minimum_native_confidence': None}


def parse_field(field, text, layout):
    """Accept complete ASCII display strings in the selected layout, without repairs."""
    if field not in FIELDS or layout not in LAYOUTS or not isinstance(text, str):
        raise ValueError('Expected a known field, explicit layout and raw string')
    if not text:
        return None, 'empty_text'
    if field != 'clock':
        if re.fullmatch('[0-9]', text):
            return int(text), None
        if re.fullmatch('[0-9]{2,}', text):
            return None, 'unsupported_score_width'
        return None, 'score_grammar'
    match = re.fullmatch(GRAMMARS[layout], text)
    if not match:
        return None, 'clock_grammar'
    a, b = map(int, match.groups())
    if layout == 'seconds_tenths':
        if a >= 60:
            return None, 'invalid_seconds'
        return ClockObservation(f'00:{a:02}.{b}', a*10+b, layout), None
    if b >= 60:
        return None, 'invalid_seconds'
    return ClockObservation(f'{a:02}:{b:02}', (a*60+b)*10, layout), None


def adapt(record, samples, raw, plan):
    """Bind worker results to the complete export, then confirm on source time."""
    rows = raw['rows']
    if raw['repeats'] != 1 or len(rows) != len(samples) or len(rows) != record['samples']:
        raise ValueError('Expected exactly one raw result for every source sample')
    state = CandidateState()
    raw_rows, independent_rows = [], []
    for index, (sample, row) in enumerate(zip(samples, rows)):
        t = index/10
        frame_id = sample['source_rgb_sha256']
        for expected in (sample, row):
            if (expected['recording_id'] != record['id'] or type(expected['index']) is not int
                    or expected['index'] != index or not number(expected['t']) or expected['t'] != t
                    or expected['source_rgb_sha256'] != frame_id):
                raise ValueError('OCR results must match the complete source grid and frame identity')
        if (not re.fullmatch('[0-9a-f]{64}', frame_id) or row['pass_index'] != 0
                or set(row['fields']) != set(FIELDS) or set(sample['crops']) != set(FIELDS)
                or not number(row['three_fields_ms']) or row['three_fields_ms'] < 0):
            raise ValueError('Invalid OCR frame metadata')
        layout = plan.at(t)
        observations, reasons, fields = {}, {}, {}
        for field in FIELDS:
            native = row['fields'][field]
            crop = sample['crops'][field]
            if (native['crop_sha256'] != crop['sha256'] or not number(native['model_api_ms'])
                    or native['model_api_ms'] < 0):
                raise ValueError('OCR result crop identity/timing mismatch')
            native_result({'rec_text': native['raw_text'], 'rec_score': native['native_confidence']})
            value, reason = parse_field(field, native['raw_text'], layout)
            observations[field], reasons[field] = value, reason
            fields[field] = {**native, 'geometry': record['geometry'][field],
                             'parsed': asdict(value) if isinstance(value, ClockObservation) else value,
                             'rejection': reason}
        raw_rows.append({**row, 'clock_layout': layout, 'fields': fields})
        independent_rows.append(state.update_observations(observations, t, reasons=reasons, frame_id=frame_id))
    return {'fps': 10, 'video_sha256': record['files']['video']['sha256'],
            'raw_rows': raw_rows, 'independent_rows': independent_rows,
            'independent_layout_plan': plan.entries, 'adapter_configuration': CONFIG}


def development_record(manifest, recording_id):
    matches = [r for r in manifest['recordings'] if r['id'] == recording_id]
    if len(matches) != 1 or matches[0]['split'] != 'development':
        raise ValueError('Select one frozen development recording; verification is reserved for Task 4')
    record = matches[0]
    if any(r['split'] != 'development' and
           r['files']['video']['sha256'] == record['files']['video']['sha256']
           for r in manifest['recordings']):
        raise ValueError('Development source aliases a reserved verification recording')
    return record


def run(args):
    if sys.platform != 'darwin':
        raise ValueError('OCR requires the macOS network sandbox')
    manifest_id = identity(args.manifest)
    manifest = read(args.manifest)
    record = development_record(manifest, args.recording)
    files = record['files']
    # Validate only the selected recording's assets. Historical source hashes
    # remain in the benchmark; this run binds its own implementation separately.
    for item in (*files.values(), manifest['crop_export']['contract'], manifest['crop_export']['recipe']):
        if identity(item['path']) != item:
            raise ValueError(f"Frozen selected input changed: {item['path']}")
    frozen_recipe = read(manifest['crop_export']['recipe']['path'])
    index_asset = next(a for a in manifest['assets'] if a['path'] == str(Path(frozen_recipe['crop_index']).resolve()))
    if identity(index_asset['path']) != index_asset:
        raise ValueError('Frozen crop index changed')
    frozen_index = read(index_asset['path'])
    frozen_entries = [e for e in frozen_index['entries'] if e['recording_id'] == record['id']]
    if not frozen_entries:
        raise ValueError('Missing frozen source/crop anchors')
    config, template, layouts, review, baseline = (
        read(files[key]['path']) for key in ('calibration', 'template', 'layout', 'review', 'baseline_report'))
    plan = LayoutPlan(layouts)
    boxes = {f: item['rectified_xywh'] for f, item in record['geometry'].items()}
    if (geometry(config, template, boxes) != record['geometry']
            or baseline['video_sha256'] != files['video']['sha256'] or baseline['fps'] != 10
            or len(baseline['independent_rows']) != record['samples']
            or baseline['independent_layout_plan'] != layouts
            or baseline['calibration'] != config or baseline['template'] != template):
        raise ValueError('Frozen baseline grid, geometry or layout mismatch')
    region_audit = audit(baseline, review)
    ocr_python = args.ocr_python.absolute()  # Keep the venv symlink path for Python.
    if not ocr_python.is_file() or not os.access(ocr_python, os.X_OK):
        raise ValueError('Expected an executable from the existing isolated OCR environment')
    spec = read(TINY_SPEC)
    check_model(spec, args.model_dir)
    output = args.output.resolve()
    if output == args.model_dir.resolve() or args.model_dir.resolve() in output.parents:
        raise ValueError('Output must not modify the pinned model directory')
    output.mkdir(parents=True, exist_ok=False)
    recipe = {'version': 1, 'recordings': [{
        'id': record['id'], 'samples': record['samples'], 'field_boxes': boxes,
        'geometry_samples': list(range(record['samples'])), 'windows': [],
        **{k: files[k]['path'] for k in ('video', 'calibration', 'template')},
    }]}
    recipe_path = output/'recipe.json'
    write_new(recipe_path, recipe)
    exported = export({**recipe, '_path': recipe_path}, output/'crops')
    samples = exported['entries']
    for anchor in frozen_entries:
        sample = samples[anchor['index']]
        if (anchor['source_rgb_sha256'] != sample['source_rgb_sha256']
                or any(anchor['crops'][f]['sha256'] != sample['crops'][f]['sha256'] for f in FIELDS)):
            raise ValueError('Complete export differs from frozen frame/crop anchors')
    write_new(output/'request.json', {'model_spec': spec, 'model_dir': str(args.model_dir.resolve()),
                                     'samples': samples, 'repeats': 1})
    trial, = run_worker_trials(output, 1, python=ocr_python)
    report = adapt(record, samples, read(trial['path']), plan)
    report.update({'recording': record, 'manifest': manifest_id, 'crop_index': identity(output/'crops/index.json'),
                   'engine': {'name': 'PaddleOCR PP-OCRv6 tiny', 'trial': trial,
                              'model_spec': identity(TINY_SPEC), 'runtime_lock': identity(RUNTIME_LOCK),
                              'network_policy': NETWORK_POLICY},
                   'implementation': [identity(ROOT/p) for p in (
                       'candidate_state.py', 'experiments/ocr_adapter.py', 'experiments/ocr_feasibility.py',
                       'experiments/audit_readings.py', 'experiments/compare_readers.py')],
                   'output_policy': 'Offline diagnostic files only'})
    ocr_audit = audit(report, review)
    write_new(output/'report.json', report)
    write_new(output/'audit.json', {'ocr_report': identity(output/'report.json'), 'review': files['review'],
                                    'frozen_region_report': files['baseline_report'],
                                    'ocr': ocr_audit, 'regions': region_audit})
    print(f"Audited {record['samples']} development samples; output disabled")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'model-dir', 'ocr-python', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--recording', required=True)
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
