"""Local scoreboard server with replay, continuous recording, and macOS camera input."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import mimetypes
import re
import sys
import subprocess
import tempfile

from calibration import validate_profile, inspect_preview, align_profile
from capture import camera_command, capture_rows, recording_command
from live import ContinuousState, InputWorker

from playback import PlaybackState

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        if self.path.startswith('/api/') and code == 200:
            return
        super().log_request(code, size)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path in ('/api/calibration/test', '/api/calibration/save', '/api/calibration/align'):
            source = getattr(self.server, 'source', None)
            if source is None:
                self.send_error(404)
                return
            origin = self.headers.get('Origin')
            if origin and origin != f"http://{self.headers.get('Host')}":
                self.send_error(403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Content-Type') != 'application/json' or not 0 < length <= 16384:
                    raise ValueError('Expected a JSON profile up to 16 KiB')
                payload = json.loads(self.rfile.read(length))
                if self.path.endswith('/align'):
                    if not isinstance(payload, dict) or set(payload) != {'corners'}:
                        raise ValueError('Expected four panel corners')
                    self.send_json({'config': align_profile(self.server.calibration, payload['corners'])})
                    return
                profile = validate_profile(payload, self.server.calibration)
                if self.path.endswith('/test'):
                    preview = source.preview_snapshot()
                    if preview is None:
                        self.send_json({'error': 'No preview frame available'}, 409)
                        return
                    self.send_json(inspect_preview(profile, preview))
                else:
                    # Fixed ignored destination; the in-memory and tracked profiles stay unchanged.
                    target = self.server.profile_output
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, prefix='.calibration-',
                                                     suffix='.json.tmp', delete=False) as output:
                        temporary = Path(output.name)
                        output.write(json.dumps(profile, indent=2) + '\n')
                    try:
                        temporary.replace(target)
                    finally:
                        temporary.unlink(missing_ok=True)
                    self.send_json({'saved': str(target), 'active': False,
                                    'message': 'Saved locally. Restart the server with --calibration ' + str(target)})
            except (ValueError, TypeError, KeyError, UnicodeDecodeError) as error:
                self.send_json({'error': str(error)}, 400)
            except OSError:
                self.send_json({'error': 'Could not save the local profile'}, 500)
            return
        if self.path != '/api/playback':
            self.send_error(404)
            return
        if getattr(self.server, 'source', None) is not None:
            self.send_json({'error': 'The server owns this input; playback updates are disabled'}, 409)
            return
        # JSON plus an Origin check prevent a third-party page from controlling replay.
        origin = self.headers.get('Origin')
        if origin and origin != f"http://{self.headers.get('Host')}":
            self.send_error(403)
            return
        try:
            if self.headers.get('Content-Type') != 'application/json':
                raise ValueError('Expected application/json')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1024:
                raise ValueError('Invalid request size')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) != {'position'}:
                raise ValueError('Expected a position field')
            if payload['position'] is None:
                self.server.playback.stop()
            else:
                self.server.playback.update(payload['position'])
        except (ValueError, UnicodeDecodeError) as error:
            self.send_json({'error': str(error)}, 400)
            return
        self.send_json(self.server.playback.snapshot())

    def do_GET(self):
        route = self.path.split('?')[0]
        if route in ('/api/preview', '/api/calibration'):
            source = getattr(self.server, 'source', None)
            if source is None:
                self.send_error(404, 'Preview is available in continuous input modes')
                return
            if route == '/api/calibration':
                self.send_json({'profile': self.server.calibration_name, 'config': self.server.calibration})
                return
            preview = source.preview_snapshot()
            if preview is None:
                self.send_response(204)
                self.send_header('Content-Length', '0')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                return
            frame, width, height, sequence, age = preview
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(frame)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Preview-Width', str(width))
            self.send_header('X-Preview-Height', str(height))
            self.send_header('X-Preview-Sequence', str(sequence))
            self.send_header('X-Preview-Age', str(age))
            self.end_headers()
            try:
                self.wfile.write(frame)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        if route == '/api/state':
            source = getattr(self.server, 'source', None)
            state = source.snapshot() if source else {**self.server.playback.snapshot(), 'mode': 'replay'}
            self.send_json(state)
            return
        continuous = getattr(self.server, 'source', None) is not None
        routes = {'/monitor.js': ROOT / 'web/monitor.js', '/calibrate.js': ROOT / 'web/calibrate.js', '/overlay': ROOT / 'web/overlay.html', '/overlay.js': ROOT / 'web/overlay.js',
                  '/overlay.css': ROOT / 'web/overlay.css', '/': ROOT / ('web/monitor.html' if continuous else 'web/index.html'), '/app.js': ROOT / 'web/app.js',
                  '/style.css': ROOT / 'web/style.css', '/readings.json': None if continuous else ROOT / 'data/readings.json',
                  '/video': self.server.video}
        path = routes.get(route)
        if path is None or not path.is_file():
            self.send_error(404, 'Not found. Run reader.py first if readings are missing.')
            return
        size = path.stat().st_size
        start, end = 0, size - 1
        requested = self.headers.get('Range')
        if requested:
            match = re.fullmatch(r'bytes=(\d+)-(\d*)', requested)
            if not match:
                self.send_error(416)
                return
            start = int(match[1])
            end = min(int(match[2]) if match[2] else size - 1, size - 1)
            if start > end:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.end_headers()
                return
        self.send_response(206 if requested else 200)
        self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        if requested:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with path.open('rb') as source:
                source.seek(start)
                remaining = end - start + 1
                while remaining:
                    chunk = source.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--mode', choices=('replay', 'recording', 'camera'), default='replay')
    parser.add_argument('--video', type=Path, default=ROOT / 'scoreboard-2-min-clip.mp4')
    parser.add_argument('--calibration', type=Path, default=ROOT / 'calibration.json')
    parser.add_argument('--device', help='Explicit AVFoundation camera name; no default camera is selected')
    parser.add_argument('--capture-fps', type=float, default=25)
    args = parser.parse_args()
    if args.mode != 'camera' and args.device is not None:
        parser.error('--device requires --mode camera')
    if args.mode == 'camera' and (sys.platform != 'darwin' or not args.device):
        parser.error('Camera mode requires macOS and an explicit --device name')
    source = worker = metadata = None
    try:
        if args.mode == 'replay':
            metadata = json.loads((ROOT / 'data/readings.json').read_text())
            if args.video.name != metadata['video']:
                parser.error('Video filename does not match the analyzed recording.')
        else:
            config = json.loads(args.calibration.read_text())
            command = (camera_command(config, args.device, args.capture_fps, preview=True) if args.mode == 'camera'
                       else recording_command(args.video, config, preview=True))
            source = ContinuousState(args.mode, args.device if args.mode == 'camera' else args.video.name)
            worker = InputWorker(source, lambda stop: capture_rows(command, config, stop,
                camera=args.mode == 'camera', diagnostic=source.diagnostic, preview=source.update_preview))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.video = None if args.mode == 'camera' else args.video.resolve()
    server.playback = PlaybackState(metadata) if metadata else None
    server.source = source
    server.calibration = config if source else None
    server.calibration_name = args.calibration.name
    server.profile_output = ROOT / 'data/calibration.local.json'
    print(f'Open http://127.0.0.1:{args.port} — mode: {args.mode} — Ctrl+C to stop', flush=True)
    if worker:
        worker.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if worker:
            worker.stop()
        server.server_close()
