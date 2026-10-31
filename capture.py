"""Bounded, cancellable frame delivery for recorded input and macOS capture."""
import math
import os
import selectors
import subprocess
import threading
import time

from reader import FrameReader, probe_recording


def frame_filter(config, *, camera=False):
    x, y, width, height = config['crop']
    if camera:
        reference_w, reference_h = config['reference_size']
        # A mismatched source must fail rather than silently use the wrong calibration.
        crop_width = f"'if(eq(iw,{reference_w})*eq(ih,{reference_h}),{width},1000000)'"
        return f'crop=w={crop_width}:h={height}:x={x}:y={y},scale={width//2}:{height//2}'
    return f"fps={config['sample_fps']},crop={width}:{height}:{x}:{y},scale={width//2}:{height//2}"


def camera_command(config, device, capture_fps=25):
    if not device or not device.strip() or ':' in device or device.isdecimal() or device in ('default', 'none'):
        raise ValueError('Select an explicit video device name, without an audio device or index')
    if not math.isfinite(capture_fps) or capture_fps <= 0:
        raise ValueError('Capture frame rate must be positive and finite')
    width, height = config['reference_size']
    return ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-nostdin',
            '-f', 'avfoundation', '-framerate', str(capture_fps), '-video_size', f'{width}x{height}',
            '-pixel_format', 'uyvy422', '-i', f'{device}:none', '-an',
            '-vf', frame_filter(config, camera=True), '-fps_mode', 'passthrough',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']


def recording_command(video, config):
    probe_recording(video, config)
    return ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-re', '-i', str(video), '-an',
            '-vf', frame_filter(config), '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']


def capture_rows(command, config, stop, *, camera=False, diagnostic=lambda text: None, frame_timeout=10):
    """Yield actual camera frames or sampled recording frames; terminate on stalls/stop."""
    reader = FrameReader(config)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    tail = bytearray()

    def read_errors():
        while chunk := process.stderr.read(1024):
            tail.extend(chunk)
            del tail[:-4096]
            diagnostic(tail.decode(errors='replace'))

    errors = threading.Thread(target=read_errors, daemon=True)
    errors.start()
    try:
        with selectors.DefaultSelector() as ready:
            ready.register(process.stdout, selectors.EVENT_READ)
            buffer = bytearray()
            start = last_frame = time.monotonic()
            index = 0
            while not stop.is_set():
                if time.monotonic() - last_frame > frame_timeout:
                    raise TimeoutError('No complete input frame arrived within the capture timeout')
                if not ready.select(timeout=.1):
                    continue
                chunk = os.read(process.stdout.fileno(), reader.frame_size - len(buffer))
                if not chunk:
                    if buffer:
                        raise ValueError('Input ended with a truncated frame')
                    code = process.wait(timeout=2)
                    errors.join(timeout=1)
                    if code:
                        raise RuntimeError(tail.decode(errors='replace') or f'FFmpeg exited with code {code}')
                    return
                buffer.extend(chunk)
                if len(buffer) == reader.frame_size:
                    now = time.monotonic()
                    t = round(now - start, 3) if camera else round(index / config['sample_fps'], 3)
                    yield reader.read(buffer, t)
                    buffer.clear()
                    index += 1
                    last_frame = now
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        process.stdout.close()
        errors.join(timeout=1)
        process.stderr.close()
