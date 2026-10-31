"""Local scoreboard server with replay, continuous recording, and macOS camera input."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import mimetypes
import re
import sys
import subprocess

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
        if route == '/api/state':
            source = getattr(self.server, 'source', None)
            state = source.snapshot() if source else {**self.server.playback.snapshot(), 'mode': 'replay'}
            self.send_json(state)
            return
        continuous = getattr(self.server, 'source', None) is not None
        routes = {'/monitor.js': ROOT / 'web/monitor.js', '/overlay': ROOT / 'web/overlay.html', '/overlay.js': ROOT / 'web/overlay.js',
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
            command = (camera_command(config, args.device, args.capture_fps) if args.mode == 'camera'
                       else recording_command(args.video, config))
            source = ContinuousState(args.mode, args.device if args.mode == 'camera' else args.video.name)
            worker = InputWorker(source, lambda stop: capture_rows(command, config, stop,
                camera=args.mode == 'camera', diagnostic=source.diagnostic))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.video = None if args.mode == 'camera' else args.video.resolve()
    server.playback = PlaybackState(metadata) if metadata else None
    server.source = source
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
