"""Bounded, cancellable frame delivery for recorded input and macOS capture."""
import math
import os
import selectors
import subprocess
import threading
import time

from reader import FrameReader, probe_recording


def preview_dimensions(config):
    values = (*config['reference_size'], *config['crop'])
    if any(type(value) is not int or value % 2 for value in values):
        raise ValueError('Preview requires even reference dimensions and crop coordinates/sizes')
    width, height = config['reference_size']
    x, y, w, h = config['crop']
    if min(width, height, w, h) <= 0 or x < 0 or y < 0 or x+w > width or y+h > height:
        raise ValueError('Preview crop is outside the reference image')
    return width//2, height//2


def recognition_crop(frame, config):
    """Unpack the padded recognition image below the display image."""
    width, height = preview_dimensions(config)
    w, h = (value//2 for value in config['crop'][2:])
    return b''.join(frame[((height+row)*width)*3:((height+row)*width+w)*3] for row in range(h))


def frame_filter(config, *, camera=False, preview=False):
    x, y, width, height = config['crop']
    if preview:
        preview_w, preview_h = preview_dimensions(config)
        if camera:
            reference_w, reference_h = config['reference_size']
            guard = f"crop=w='if(eq(iw,{reference_w})*eq(ih,{reference_h}),iw,1000000)':h=ih:x=0:y=0,"
        else:
            guard = f"fps={config['sample_fps']},"
        # Pack an unchanged recognition crop below the preview in one raw frame.
        # Both branches share the same decoded input and capture device.
        return (f'{guard}split=2[p][r];[p]scale={preview_w}:{preview_h},format=rgb24[pv];'
                f'[r]crop={width}:{height}:{x}:{y},scale={width//2}:{height//2},'
                f'format=rgb24,pad={preview_w}:{height//2}:0:0[rv];[pv][rv]vstack=inputs=2')
    if camera:
        reference_w, reference_h = config['reference_size']
        # A mismatched source must fail rather than silently use the wrong calibration.
        crop_width = f"'if(eq(iw,{reference_w})*eq(ih,{reference_h}),{width},1000000)'"
        return f'crop=w={crop_width}:h={height}:x={x}:y={y},scale={width//2}:{height//2}'
    return f"fps={config['sample_fps']},crop={width}:{height}:{x}:{y},scale={width//2}:{height//2}"


def camera_command(config, device, capture_fps=25, *, preview=False):
    if not device or not device.strip() or ':' in device or device.isdecimal() or device in ('default', 'none'):
        raise ValueError('Select an explicit video device name, without an audio device or index')
    if not math.isfinite(capture_fps) or capture_fps <= 0:
        raise ValueError('Capture frame rate must be positive and finite')
    width, height = config['reference_size']
    return ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-nostdin',
            '-f', 'avfoundation', '-framerate', str(capture_fps), '-video_size', f'{width}x{height}',
            '-pixel_format', 'uyvy422', '-i', f'{device}:none', '-an',
            '-vf', frame_filter(config, camera=True, preview=preview), '-fps_mode', 'passthrough',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']


def recording_command(video, config, *, preview=False, realtime=True):
    probe_recording(video, config)
    return ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', *(['-re'] if realtime else []), '-i', str(video), '-an',
            '-vf', frame_filter(config, preview=preview), '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']


def capture_rows(command, config, stop, *, camera=False, diagnostic=lambda text: None, frame_timeout=10, preview=None):
    """Yield actual camera frames or sampled recording frames; terminate on stalls/stop."""
    reader = FrameReader(config)
    dimensions = preview_dimensions(config) if preview is not None else None
    frame_size = dimensions[0]*(dimensions[1]+config['crop'][3]//2)*3 if dimensions else reader.frame_size
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
            last_preview = None
            while not stop.is_set():
                if time.monotonic() - last_frame > frame_timeout:
                    raise TimeoutError('No complete input frame arrived within the capture timeout')
                if not ready.select(timeout=.1):
                    continue
                chunk = os.read(process.stdout.fileno(), frame_size - len(buffer))
                if not chunk:
                    if buffer:
                        raise ValueError('Input ended with a truncated frame')
                    code = process.wait(timeout=2)
                    errors.join(timeout=1)
                    if code:
                        raise RuntimeError(tail.decode(errors='replace') or f'FFmpeg exited with code {code}')
                    return
                buffer.extend(chunk)
                if len(buffer) == frame_size:
                    now = time.monotonic()
                    t = round(now - start, 3) if camera else round(index / config['sample_fps'], 3)
                    if dimensions and (last_preview is None or now-last_preview >= .5):
                        preview(bytes(buffer[:dimensions[0]*dimensions[1]*3]), *dimensions)
                        last_preview = now
                    frame = recognition_crop(buffer, config) if dimensions else buffer
                    yield reader.read(frame, t)
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
