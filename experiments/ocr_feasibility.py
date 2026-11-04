"""Explicit local model provisioning and development-only offline OCR smoke runs.

Inference runs in a fresh macOS process denied all network access. No capture,
recognizer selection, parsing, confirmation or OBS output integration.
"""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.ocr_benchmark import digest, identity, read, verify, write_new

FIELDS = ('home', 'away', 'clock')
RUNTIME_LOCK = ROOT/'experiments/ocr/requirements-macos-arm64.txt'
SETTINGS = {'device': 'cpu', 'cpu_threads': 1, 'enable_mkldnn': False,
            'enable_hpi': False, 'engine': 'paddle_static'}
NETWORK_POLICY = '(version 1)(allow default)(deny network*)'


def check_model(spec, directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError('Model directory is missing; provision it explicitly before inference')
    expected = {f['name'] for f in spec['files']}
    if {p.name for p in directory.iterdir()} != expected:
        raise ValueError('Model file inventory differs from pinned specification')
    result = []
    for item in spec['files']:
        path = directory/item['name']
        if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise ValueError(f"Model hash mismatch: {item['name']}")
        result.append(identity(path))
    return result


def provision(spec, directory):
    # Only this explicit subcommand has network capability; never called by run.
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    if (not spec['repository'].startswith('PaddlePaddle/') or
            len(spec['revision']) != 40 or any(c not in '0123456789abcdef' for c in spec['revision'])):
        raise ValueError('Expected official repository and immutable revision')
    for item in spec['files']:
        name = item['name']
        if name not in ('README.md', 'inference.json', 'inference.pdiparams', 'inference.yml'):
            raise ValueError('Unexpected model filename')
        url = f"https://huggingface.co/{spec['repository']}/resolve/{spec['revision']}/{name}"
        with urllib.request.urlopen(url, timeout=120) as source, (directory/name).open('xb') as target:
            while block := source.read(1024*1024):
                target.write(block)
    check_model(spec, directory)


def select_samples(manifest, workload):
    """Resolve only locked development crops. No prediction or label-based selection."""
    records = {r['id']: r for r in manifest['recordings']}
    recipe = read(manifest['crop_export']['recipe']['path'])
    index = read(recipe['crop_index'])
    exported = {(e['recording_id'], e['index']): e for e in index['entries']}
    selected, seen = [], set()
    for case in workload['samples']:
        key = case['recording_id'], case['index']
        if key in seen or type(key[1]) is not int or key[1] < 0:
            raise ValueError('Duplicate/invalid workload source index')
        seen.add(key)
        if records[key[0]]['split'] != 'development':
            raise ValueError('Verification recording is forbidden in feasibility runs')
        if key not in exported:
            raise ValueError('Requested exact sample is not in frozen crop export')
        entry = exported[key]
        for field in FIELDS:
            item = entry['crops'][field]
            if identity(item['path']) != item:
                raise ValueError('Frozen crop changed')
        selected.append(entry)
    if not selected:
        raise ValueError('Workload cannot be empty')
    return selected


def native_result(result):
    text, confidence = result['rec_text'], result['rec_score']
    if not isinstance(text, str) or type(confidence) not in (int, float) or not math.isfinite(confidence):
        raise ValueError('Engine returned invalid text/confidence')
    return {'raw_text': text, 'native_confidence': confidence}


def percentile(values, fraction):
    if not values:
        raise ValueError('No measured timings')
    return sorted(values)[max(0, math.ceil(len(values)*fraction)-1)]


def timings(rows):
    values = [r['three_fields_ms'] for r in rows]
    return {'samples': len(values), 'three_fields_ms_median': percentile(values, .5),
            'three_fields_ms_p95': percentile(values, .95),
            'sustained_source_fps': len(values)*1000/sum(values)}


def runtime_versions():
    versions = {d.metadata['Name'].lower().replace('_','-'): d.version
                for d in importlib.metadata.distributions()}
    expected = {}
    for line in RUNTIME_LOCK.read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            name, version = line.split('==')
            expected[name.lower().replace('_','-')] = version
    if any(versions.get(name) != version for name,version in expected.items()):
        raise ValueError('OCR environment differs from pinned runtime lock')
    return versions


def require_network_denied():
    # Query the kernel policy without sending even a probe packet. Also protects
    # accidental direct invocation of the internal worker command.
    if sys.platform != 'darwin':
        raise ValueError('Inference requires the macOS network-deny child')
    import ctypes
    check = ctypes.CDLL('/usr/lib/libsandbox.dylib').sandbox_check
    check.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    check.restype = ctypes.c_int
    if check(os.getpid(), b'network-outbound', 0) != 1:
        raise ValueError('Network must be denied before importing the OCR runtime')


def worker(request_path, output):
    # Parent starts this process with a mandatory macOS network-deny policy.
    require_network_denied()
    started = time.perf_counter()
    cpu_start = time.process_time()
    request = read(request_path)
    spec = request['model_spec']
    model_files = check_model(spec, request['model_dir'])
    versions = runtime_versions()
    import_started = time.perf_counter()
    import cv2
    from paddleocr import TextRecognition
    import_s = time.perf_counter()-import_started
    load_started = time.perf_counter()
    model = TextRecognition(model_name=spec['model_name'], model_dir=request['model_dir'], **SETTINGS)
    load_s = time.perf_counter()-load_started
    def triplet(entry):
        t = time.perf_counter()
        fields = {}
        for field in FIELDS:
            crop = entry['crops'][field]
            image = cv2.imread(crop['path'], cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError('Cannot read frozen RGB crop')
            call = time.perf_counter()
            predictions = list(model.predict(input=image, batch_size=1))
            api_ms = (time.perf_counter()-call)*1000
            if len(predictions) != 1:
                raise ValueError('Expected one complete text result per whole field')
            fields[field] = {**native_result(predictions[0]), 'model_api_ms': api_ms,
                             'crop_sha256': crop['sha256']}
        return {'recording_id': entry['recording_id'], 'index': entry['index'], 't': entry['t'],
                'source_rgb_sha256': entry['source_rgb_sha256'], 'fields': fields,
                'three_fields_ms': (time.perf_counter()-t)*1000}
    first = triplet(request['samples'][0])
    first_ready_s = time.perf_counter()-started
    for _ in range(3):
        triplet(request['samples'][0])
    measured_started, cpu_measured = time.perf_counter(), time.process_time()
    rows = [{**triplet(e), 'pass_index': repeat}
            for repeat in range(request['repeats']) for e in request['samples']]
    measured_s, measured_cpu_s = time.perf_counter()-measured_started, time.process_time()-cpu_measured
    usage = resource.getrusage(resource.RUSAGE_SELF)
    result = {'model_spec': spec, 'model_files': model_files, 'settings': SETTINGS,
              'precision': 'FP32 native static model; no quantization/TensorRT/HPI',
              'versions': versions, 'platform': platform.platform(), 'machine': platform.machine(),
              'python': sys.version, 'import_s': import_s, 'model_load_s': load_s,
              'worker_to_first_triplet_s': first_ready_s,
              'first_triplet': first, 'warmup_triplets': 3, 'rows': rows,
              'unique_source_samples': len(request['samples']), 'repeats': request['repeats'],
              'warm_timings': timings(rows), 'measured_wall_s': measured_s,
              'measured_cpu_s': measured_cpu_s,
              'measured_cpu_core_equivalents': measured_cpu_s/measured_s,
              'peak_rss_bytes': usage.ru_maxrss if sys.platform == 'darwin' else usage.ru_maxrss*1024,
              'process_cpu_s': time.process_time()-cpu_start,
              'preprocessing': 'Original BGR-loaded colour field, no external filtering/resize. Pinned engine RecResizeImg height48/aspect-ratio resize, minimum padded width320, /255 then (x-.5)/.5; CTC decoder/full vocabulary. Model API includes native preprocessing/inference/postprocessing.',
              'excluded_costs': ['video decode', 'panel warp/crop export', 'strict parsing', 'temporal state', 'capture/OBS'],
              'pure_kernel_ms': None,
              'pure_kernel_reason': 'Model API timed as a whole; internal kernel-only time not instrumented.',
              'network': 'OS child policy denies network*; local model only; no implicit downloads',
              'output_policy': 'raw diagnostic text only; no observations/confirmed state or OBS path'}
    write_new(output, result)


def run_worker_trials(output, trials, *, python=sys.executable):
    """Run an already written request in the same network-denied OCR worker."""
    env = {**os.environ, 'PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK': 'True',
           'PADDLE_PDX_CACHE_HOME': str(output/'cache'), 'HF_HUB_OFFLINE': '1',
           'HF_HUB_DISABLE_TELEMETRY': '1', 'OMP_NUM_THREADS': '1',
           'OPENBLAS_NUM_THREADS': '1', 'VECLIB_MAXIMUM_THREADS': '1'}
    runs = []
    for trial in range(trials):
        dest = output/f'trial-{trial+1}.json'
        command = ['sandbox-exec', '-p', NETWORK_POLICY, str(python), str(Path(__file__).resolve()),
                   '_worker', '--request', str(output/'request.json'), '--output', str(dest)]
        child_started = time.perf_counter()
        with (output/f'trial-{trial+1}.log').open('x') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        runs.append({**identity(dest), 'child_process_wall_s': time.perf_counter()-child_started})
    return runs


def run(args):
    if sys.platform != 'darwin':
        raise ValueError('This feasibility runner requires the measured macOS network sandbox')
    manifest = read(args.manifest)
    workload = read(args.workload)
    if digest(args.manifest) != workload['benchmark_sha256']:
        raise ValueError('Workload does not bind this benchmark manifest')
    verify(manifest)
    samples = select_samples(manifest, workload)
    spec = read(args.model_spec)
    check_model(spec, args.model_dir)
    output = args.output.resolve()
    if output == args.model_dir.resolve() or args.model_dir.resolve() in output.parents:
        raise ValueError('Output must not modify the pinned model directory')
    output.mkdir(parents=True, exist_ok=False)
    request = {'model_spec': spec, 'model_dir': str(args.model_dir.resolve()),
               'samples': samples, 'repeats': args.repeats}
    write_new(output/'request.json', request)
    runs = run_worker_trials(output, args.trials)
    result = {'version': 1, 'manifest': identity(args.manifest), 'workload': identity(args.workload),
              'model_spec': identity(args.model_spec), 'runtime_lock': identity(RUNTIME_LOCK),
              'runner': identity(Path(__file__)), 'git_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'runs': runs, 'network_policy': NETWORK_POLICY,
              'hardware': {key: subprocess.check_output(['sysctl','-n',key],text=True).strip()
                           for key in ('hw.model', 'machdep.cpu.brand_string', 'hw.memsize')},
              'measurement_limits': 'Fresh interpreter/model start with OS disk caches uncontrolled; repeated trials reuse caches. Repeated source samples measure processing cost, never new independent recognition or freshness evidence. Pre-exported PNG reads plus three sequential native model API calls; no video decode/crop/parse/state. Not full pipeline throughput or live latency.'}
    write_new(output/'summary.json', result)
    print(f'Completed {len(runs)} offline trial(s), {len(samples)} development triplets each; output disabled')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('provision')
    p.add_argument('--model-spec', type=Path, required=True)
    p.add_argument('--model-dir', type=Path, required=True)
    p = sub.add_parser('run')
    for name in ('manifest', 'workload', 'model-spec', 'model-dir', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--trials', type=int, default=3)
    p.add_argument('--repeats', type=int, default=10)
    p = sub.add_parser('_worker')
    p.add_argument('--request', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'provision':
            provision(read(args.model_spec), args.model_dir)
            print('Verified explicit model download; no inference performed')
        elif args.action == 'run':
            if not 1 <= args.trials <= 5:
                raise ValueError('Use 1..5 isolated trials')
            if not 1 <= args.repeats <= 100:
                raise ValueError('Use 1..100 passes of the fixed workload')
            run(args)
        else:
            worker(args.request, args.output)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
