"""Generate a local controlled scoreboard MP4 and source timeline. No camera or server."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, FPS, SECONDS = 1920, 1080, 60, 120
TOTAL_FRAMES = FPS * SECONDS
LED = (255, 110, 60)
# Independent line drawing, not recognizer patterns or sampling locations.
STROKES = {0: (0, 1, 2, 3, 4, 5), 1: (1, 2), 2: (0, 1, 3, 4, 6),
           3: (0, 1, 2, 3, 6), 4: (1, 2, 5, 6), 5: (0, 2, 3, 5, 6),
           6: (0, 2, 3, 4, 5, 6), 7: (0, 1, 2),
           8: (0, 1, 2, 3, 4, 5, 6), 9: (0, 1, 2, 3, 5, 6)}
LINES = (((18, 8), (64, 8)), ((68, 14), (64, 48)), ((63, 57), (59, 91)),
         ((12, 98), (53, 98)), ((7, 90), (11, 56)), ((12, 47), (16, 14)),
         ((15, 52), (58, 52)))
# Small original bitmap font; no system fonts or image packages required.
FONT = {
    ' ': (0,0,0,0,0,0,0), '0': (14,17,17,17,17,17,14), '1': (4,12,4,4,4,4,14),
    '2': (14,17,1,2,4,8,31), '3': (30,1,1,14,1,1,30), '4': (2,6,10,18,31,2,2),
    '5': (31,16,16,30,1,1,30), '6': (14,16,16,30,17,17,14), '7': (31,1,2,4,8,8,8),
    '8': (14,17,17,14,17,17,14), '9': (14,17,17,15,1,1,14),
    'A': (14,17,17,31,17,17,17), 'B': (30,17,17,30,17,17,30),
    'C': (14,17,16,16,16,17,14), 'D': (30,17,17,17,17,17,30),
    'E': (31,16,16,30,16,16,31), 'F': (31,16,16,30,16,16,16),
    'G': (14,17,16,23,17,17,15), 'H': (17,17,17,31,17,17,17),
    'I': (14,4,4,4,4,4,14), 'J': (7,2,2,2,2,18,12),
    'K': (17,18,20,24,20,18,17), 'L': (16,16,16,16,16,16,31),
    'M': (17,27,21,21,17,17,17), 'N': (17,25,21,19,17,17,17),
    'O': (14,17,17,17,17,17,14), 'P': (30,17,17,30,16,16,16),
    'Q': (14,17,17,17,21,18,13), 'R': (30,17,17,30,20,18,17),
    'S': (15,16,16,14,1,1,30), 'T': (31,4,4,4,4,4,4),
    'U': (17,17,17,17,17,17,14), 'V': (17,17,17,17,17,10,4),
    'W': (17,17,17,21,21,21,10), 'X': (17,17,10,4,10,17,17),
    'Y': (17,17,10,4,4,4,4), 'Z': (31,1,2,4,8,16,31),
    ':': (0,4,4,0,4,4,0), '.': (0,0,0,0,0,6,6), '-': (0,0,0,31,0,0,0),
    '/': (1,2,2,4,8,8,16),
}
SECTIONS = (
    (0,10,'alignment'), (10,30,'home sweep'), (30,50,'away sweep'),
    (50,60,'countdown'), (60,70,'paused clock'), (70,90,'clock tenths'),
    (90,105,'corrections'), (105,110,'clock blank'),
    (110,115,'home covered'), (115,120,'recovery'),
)
LAYOUT_PLAN = [{'start':0,'layout':'mmss'}, {'start':70,'layout':'seconds_tenths'},
               {'start':90,'layout':'mmss'}]


def clock_text(seconds):
    return f'{seconds//60:02}:{seconds%60:02}'


def frame_state(index):
    """Intended source values and deliberately visible fields for one source frame."""
    if type(index) is not int or not 0 <= index < TOTAL_FRAMES:
        raise ValueError('Source frame outside the fixed two-minute scenario')
    section = next(name for start,end,name in SECTIONS if start*FPS <= index < end*FPS)
    clock, home, away, layout = '18:48', 8, 8, 'mmss'
    visibility = dict(clock='visible', home='visible', away='visible')
    if 10*FPS <= index < 30*FPS:
        home, away = (index-10*FPS)//(2*FPS), 0
    elif 30*FPS <= index < 50*FPS:
        home, away = 0, (index-30*FPS)//(2*FPS)
    elif 50*FPS <= index < 70*FPS:
        home, away = 2, 3
        clock = clock_text(1199-min(9,(index-50*FPS)//FPS))
    elif 70*FPS <= index < 90*FPS:
        ticks = 299-(index-70*FPS)//(FPS//10)
        clock, home, away, layout = f'00:{ticks//10:02}.{ticks%10}', 2, 3, 'seconds_tenths'
    elif 90*FPS <= index < 105*FPS:
        home, away, clock = ((6,9,'05:00'), (9,6,'05:00'), (0,0,'20:00'),
                             (1,0,'19:58'), (1,1,'19:55'))[(index-90*FPS)//(3*FPS)]
    elif 105*FPS <= index < 110*FPS:
        clock, home, away = '05:15', 3, 4
        visibility['clock'] = 'blank'
    elif 110*FPS <= index < 115*FPS:
        clock, home, away = '05:10', 3, 4
        visibility['home'] = 'covered'
    elif index >= 115*FPS:
        clock, home, away = clock_text(305-(index-115*FPS)//FPS), 3, 4
    slots = ([int(c) for c in clock if c.isdigit()] if layout == 'mmss'
             else [int(clock[3]), int(clock[4]), int(clock[6]), 'blank'])
    intended = dict(clock=clock, home=home, away=away)
    visible = {name: value if visibility[name] == 'visible' else None for name,value in intended.items()}
    return {'source_frame':index, 't':round(index/FPS,6), 'section':section, 'layout':layout,
            'intended':intended, 'visible':visible, 'visibility':visibility, 'clock_slots':slots}


class Raster:
    def __init__(self, pixels=None):
        self.pixels = bytearray(pixels) if pixels is not None else bytearray(bytes((18,18,22))*WIDTH*HEIGHT)

    def rect(self, x, y, w, h, color):
        left,right = max(0,round(x)),min(WIDTH,round(x+w))
        if right <= left:
            return
        row = bytes(color)*(right-left)
        for py in range(max(0,round(y)),min(HEIGHT,round(y+h))):
            offset = (py*WIDTH+left)*3
            self.pixels[offset:offset+len(row)] = row

    def polygon(self, points, color):
        for y in range(max(0,math.floor(min(p[1] for p in points))),
                       min(HEIGHT,math.ceil(max(p[1] for p in points)))):
            scan, intersections = y+.5, []
            for a,b in zip(points,points[1:]+points[:1]):
                if min(a[1],b[1]) <= scan < max(a[1],b[1]):
                    intersections.append(a[0]+(scan-a[1])*(b[0]-a[0])/(b[1]-a[1]))
            intersections.sort()
            for left,right in zip(intersections[::2],intersections[1::2]):
                x1,x2 = math.ceil(left-.5),math.ceil(right-.5)
                self.rect(x1,y,x2-x1,1,color)

    def circle(self, x, y, radius, color):
        for py in range(math.floor(y-radius),math.ceil(y+radius)):
            distance = radius*radius-(py+.5-y)**2
            if distance >= 0:
                dx = math.sqrt(distance)
                left,right = math.ceil(x-dx-.5),math.ceil(x+dx-.5)
                self.rect(left,py,right-left,1,color)

    def line(self, a, b, width, color):
        dx,dy = b[0]-a[0],b[1]-a[1]
        length = math.hypot(dx,dy)
        nx,ny = -dy/length*width/2,dx/length*width/2
        self.polygon([(a[0]+nx,a[1]+ny),(b[0]+nx,b[1]+ny),
                      (b[0]-nx,b[1]-ny),(a[0]-nx,a[1]-ny)],color)
        self.circle(*a,width/2,color)
        self.circle(*b,width/2,color)

    def text(self, text, x, y, scale=4, color=(240,240,240)):
        for index,char in enumerate(text.upper()):
            for row,bits in enumerate(FONT[char]):
                for col in range(5):
                    if bits & (1 << (4-col)):
                        self.rect(x+(index*6+col)*scale,y+row*scale,scale,scale,color)

    def digit(self, digit, x, y, scale=1):
        for segment in STROKES[digit]:
            a,b = LINES[segment]
            self.line((x+a[0]*scale,y+a[1]*scale),(x+b[0]*scale,y+b[1]*scale),10*scale,LED)


class Renderer:
    def __init__(self, calibration):
        if calibration['reference_size'] != [WIDTH,HEIGHT]:
            raise ValueError('Renderer requires the 1920x1080 reference geometry')
        image = Raster()
        corners = [tuple(p) for p in calibration['board_corners']]
        image.polygon(corners,(55,32,30))
        for a,b in zip(corners,corners[1:]+corners[:1]):
            image.line(a,b,5,(60,130,80))
        for x,y in corners:
            image.line((x-12,y),(x+12,y),3,(220,220,220))
            image.line((x,y-12),(x,y+12),3,(220,220,220))
        image.text('FUTSAL TEST',700,300,6)
        image.text('HOME',624,686,3,(170,170,175))
        image.text('AWAY',1300,686,3,(170,170,175))
        image.text('CONTROLLED SOURCE V1 - KEEP THE REFERENCE STRIP VISIBLE',45,60,4)
        image.rect(465,905,1010,165,(28,28,34))
        self.static, self.key, self.base = bytes(image.pixels),None,None

    def render(self, state):
        key = (state['intended']['clock'],state['intended']['home'],state['intended']['away'],
               state['layout'],tuple(state['visibility'].values()))
        if key != self.key:
            image = Raster(self.static)
            if state['visibility']['clock'] == 'visible':
                for x,digit in zip((735,845,990,1110),state['clock_slots']):
                    if digit != 'blank':
                        image.digit(digit,x,524,1.3)
                image.circle(970,640,5,LED)
                if state['layout'] == 'mmss':
                    image.circle(970,600,5,LED)
            for name,x,y in (('home',643,724),('away',1319,729)):
                image.digit(state['intended'][name],x,y)
            if state['visibility']['home'] == 'covered':
                image.rect(610,710,125,145,(90,100,110))
                image.line((620,720),(725,845),5,(125,125,130))
                image.line((725,720),(620,845),5,(125,125,130))
            self.key,self.base = key,bytes(image.pixels)
        image = Raster(self.base)
        image.text('SOURCE FRAME',490,922,3,(160,170,185))
        image.text(f"{state['source_frame']:06}",490,965,7)
        image.text(f"T {state['t']:07.3f} S",490,1030,3)
        image.text(state['section'],810,932,3)
        image.text('SOURCE VALUES',810,990,3,(160,170,185))
        clock = state['visible']['clock'] or 'BLANK'
        image.text(f'CLK {clock}',1180,932,3)
        home = state['visible']['home']
        away = state['visible']['away']
        image.text(f"HOME {home if home is not None else 'COVERED'}",1180,981,3)
        image.text(f'AWAY {away}',1180,1020,3)
        return image.pixels


def write_all(stream, data):
    view = memoryview(data)
    while view:
        written = stream.write(view)
        if not written:
            raise BrokenPipeError('Encoder stopped accepting frames')
        view = view[written:]


def probe_video(path, frames):
    result = json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames',
        '-show_entries','stream=codec_type,codec_name,width,height,avg_frame_rate,nb_read_frames:format=duration',
        '-of','json',str(path)]))
    streams = result['streams']
    if len(streams) != 1:
        raise RuntimeError('Expected exactly one video stream and no audio')
    stream = streams[0]
    if (stream['codec_type'] != 'video' or stream['codec_name'] != 'h264'
            or [stream['width'],stream['height']] != [WIDTH,HEIGHT]
            or stream['avg_frame_rate'] != f'{FPS}/1' or int(stream['nb_read_frames']) != frames
            or abs(float(result['format']['duration'])-frames/FPS) > 1/FPS):
        raise RuntimeError('Encoded video differs from the requested frame grid')
    return result


def generate(output, frames=TOTAL_FRAMES):
    if type(frames) is not int or not 1 <= frames <= TOTAL_FRAMES:
        raise ValueError('Frame count must be between 1 and 7200')
    calibration_bytes = (ROOT/'calibration.json').read_bytes()
    calibration = json.loads(calibration_bytes)
    renderer = Renderer(calibration)
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    incomplete = output/'INCOMPLETE.txt'
    incomplete.write_text('Generation has not completed. Do not use this bundle for capture.\n')
    video = output/'recording.mp4'
    command = ['ffmpeg','-hide_banner','-loglevel','error','-n','-f','rawvideo',
               '-pix_fmt','rgb24','-video_size',f'{WIDTH}x{HEIGHT}','-framerate',str(FPS),'-i','pipe:0',
               '-an','-frames:v',str(frames),'-c:v','libx264','-preset','veryfast','-crf','16',
               '-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    with (output/'ffmpeg.log').open('xb') as log:
        process = subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log,bufsize=0)
        try:
            for index in range(frames):
                write_all(process.stdin,renderer.render(frame_state(index)))
                if index % (10*FPS) == 0:
                    print(f'Rendered {index}/{frames} source frames',flush=True)
            process.stdin.close()
            if process.wait(timeout=30) != 0:
                raise RuntimeError(f'FFmpeg failed; inspect {output / "ffmpeg.log"}')
        finally:
            process.stdin.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    probe = probe_video(video,frames)
    if source_hash != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise RuntimeError('Generator changed during rendering; bundle remains incomplete')
    with video.open('rb') as source:
        video_hash = hashlib.file_digest(source,'sha256').hexdigest()
    (output/'reference-calibration.json').write_bytes(calibration_bytes)
    plan = [entry for entry in LAYOUT_PLAN if entry['start']*FPS < frames]
    (output/'source-clock-layout-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    manifest = {'schema_version':1,'kind':'controlled_scoreboard_source','scenario':'v1',
        'fps':FPS,'width':WIDTH,'height':HEIGHT,'frame_count':frames,'duration':frames/FPS,
        'planned_frames':TOTAL_FRAMES,'complete_scenario':frames == TOTAL_FRAMES,
        'video':'recording.mp4','video_sha256':video_hash,'generator_sha256':source_hash,
        'reference_calibration_sha256':hashlib.sha256(calibration_bytes).hexdigest(),
        'ffmpeg_version':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0],
        'encoding_command':command,'probe':probe,'led_rgb':LED,
        'reference_strip':[465,905,1010,165],
        'sections':[{'start_frame':start*FPS,'end_frame_exclusive':min(end*FPS,frames),'name':name}
                    for start,end,name in SECTIONS if start*FPS < frames],
        'truth_scope':'Intended and deliberately visible generated source fields only. Captured mixed/occluded/unreadable fields require independent per-field review; a clear reference counter alone does not establish captured scoreboard truth.',
        'frames':[frame_state(index) for index in range(frames)]}
    (output/'timeline.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'README.txt').write_text(
        ('FULL 120-SECOND SCENARIO\n' if frames == TOTAL_FRAMES else 'PREFIX ONLY - NOT THE FULL CAPTURE SCENARIO\n')+
        'Play recording.mp4 fullscreen and keep the central panel and bottom reference strip visible.\n'
        'Reference calibration and clock layout plan apply to the generated source, not an unmapped recapture.\n'
        'Coordinate capture ownership before opening any camera or changing existing servers.\n'
        'Inspect captured fields independently; source counter/timeline do not label mixed frames as correct.\n'
        'See docs/controlled-recording.md in the repository for capture and evaluation instructions.\n')
    incomplete.unlink()
    print(f'Verified {frames} frames; saved {video}',flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'data/controlled-recordings/v1',
                        help='New bundle directory; existing paths are never replaced')
    parser.add_argument('--frames',type=int,default=TOTAL_FRAMES,
                        help='Prefix length for smoke checks, 1..7200 (default: full 120-second scenario)')
    args = parser.parse_args()
    try:
        generate(args.output,args.frames)
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as error:
        parser.exit(1,f'{error}\n')


if __name__ == '__main__':
    main()
