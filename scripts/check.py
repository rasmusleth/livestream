"""Run the same dependency-free checks locally and in CI."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIELDS = {'minutes_tens', 'minutes_units', 'seconds_tens', 'seconds_units', 'home', 'away'}


def validate_calibration():
    config = json.loads((ROOT / 'calibration.json').read_text())
    width, height = config['reference_size']
    x, y, w, h = config['crop']
    assert all(type(v) is int and v > 0 for v in (width, height, w, h))
    assert all(type(v) is int and v >= 0 for v in (x, y))
    assert x + w <= width and y + h <= height, 'Crop outside reference image'
    assert w % 2 == 0 and h % 2 == 0, 'Crop must support the half-size reader'
    assert config['sample_fps'] > 0, 'Sample rate must be positive'
    assert set(config['digits']) == FIELDS
    assert set(config['segment_centers']) == FIELDS
    for name, (dx, dy, dw, dh) in config['digits'].items():
        assert dw > 0 and dh > 0
        assert 0 <= dx < dx + dw <= width and 0 <= dy < dy + dh <= height, name
    for name, centers in config['segment_centers'].items():
        assert len(centers) == 7, f'{name}: expected seven segment centers'
        for px, py in centers:
            assert x + 5 <= px < x + w - 5 and y + 5 <= py < y + h - 5, name
    from calibration import validate_corners
    validate_corners(config['board_corners'], config['reference_size'])
    print('Calibration structure and bounds: OK', flush=True)


def main():
    for tool in ('node', 'ffmpeg', 'ffprobe'):
        if shutil.which(tool) is None:
            raise SystemExit(f'Missing required development tool: {tool}')
    paths = list(ROOT.glob('*.py'))
    for folder in ('scripts', 'tests'):
        paths.extend((ROOT / folder).rglob('*.py'))
    for path in paths:
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
    print(f'Python syntax: {len(paths)} files OK', flush=True)
    validate_calibration()
    for path in (ROOT / 'web').glob('*.js'):
        subprocess.run(['node', '--check', str(path)], check=True, cwd=ROOT)
    print('JavaScript syntax: OK', flush=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                   cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
