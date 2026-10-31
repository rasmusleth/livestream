"""Validate local camera profiles and inspect a preview without publishing output."""
from copy import deepcopy
import math

from reader import FrameReader

FIELDS = ('minutes_tens', 'minutes_units', 'seconds_tens', 'seconds_units', 'home', 'away')


def validate_profile(payload, reference):
    if not isinstance(payload, dict) or payload.get('reference_size') != reference['reference_size']:
        raise ValueError('Profile must match the active input resolution')
    width, height = reference['reference_size']
    result = {'reference_size': [width, height], 'sample_fps': reference['sample_fps']}
    for key in ('digits', 'segment_centers'):
        if not isinstance(payload.get(key), dict) or set(payload[key]) != set(FIELDS):
            raise ValueError('Expected all six digit fields')
        result[key] = deepcopy(payload[key])
    for name in FIELDS:
        box = result['digits'][name]
        if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box):
            raise ValueError('Digit boxes require four integer coordinates')
        x, y, w, h = box
        if w < 12 or h < 12 or x < 0 or y < 0 or x+w > width or y+h > height:
            raise ValueError('Digit box is too small or outside the input')
        centers = result['segment_centers'][name]
        if not isinstance(centers, list) or len(centers) != 7:
            raise ValueError('Each digit requires seven segment probes')
        for point in centers:
            if not isinstance(point, list) or len(point) != 2 or any(type(v) is not int for v in point):
                raise ValueError('Probe centers require integer coordinates')
            px, py = point
            if not (6 <= px < width-6 and 6 <= py < height-6):
                raise ValueError('Probe sample lies outside the input')
            if not (x <= px <= x+w and y <= py <= y+h):
                raise ValueError('Probe must lie within its digit box')
    # Recompute an even crop around all probes. A caller cannot supply filter geometry.
    points = [point for centers in result['segment_centers'].values() for point in centers]
    left = max(0, (min(p[0] for p in points)-8)//2*2)
    top = max(0, (min(p[1] for p in points)-8)//2*2)
    right = min(width, math.ceil((max(p[0] for p in points)+8)/2)*2)
    bottom = min(height, math.ceil((max(p[1] for p in points)+8)/2)*2)
    result['crop'] = [left, top, right-left, bottom-top]
    FrameReader(result)
    return result


def inspect_preview(profile, preview):
    """One observation is diagnostic evidence, never a confirmed output."""
    pixels, width, height, sequence, age = preview
    full = {**profile, 'crop': [0, 0, width*2, height*2]}
    reader = FrameReader(full)
    row = reader.read(pixels, 0)
    digits = reader.digits
    return {'raw': row['raw'], 'digits': digits, 'segments': row['segments'],
            'preview_sequence': sequence, 'preview_age': age, 'confirmed': False}
