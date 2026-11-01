"""Validate local camera profiles and inspect a preview without publishing output."""
from copy import deepcopy
import math

from reader import FrameReader

FIELDS = ('minutes_tens', 'minutes_units', 'seconds_tens', 'seconds_units', 'home', 'away')


def validate_corners(corners, size):
    if not isinstance(corners, list) or len(corners) != 4:
        raise ValueError('Mark four panel corners: top left, top right, bottom right, bottom left')
    width, height = size
    for point in corners:
        if (not isinstance(point, list) or len(point) != 2 or
                any(type(v) is not int for v in point) or
                not (0 <= point[0] < width and 0 <= point[1] < height)):
            raise ValueError('Panel corners must be integer points inside the input')
    for i, p in enumerate(corners):
        q, r = corners[(i+1) % 4], corners[(i+2) % 4]
        if (q[0]-p[0])*(r[1]-q[1])-(q[1]-p[1])*(r[0]-q[0]) < 4:
            raise ValueError('Panel corners must form a convex outline in the requested order')
    return deepcopy(corners)


def perspective_map(source, target):
    """Fit eight homography coefficients with partial-pivot Gaussian elimination."""
    rows = []
    for (x, y), (u, v) in zip(source, target):
        rows.extend([[x, y, 1, 0, 0, 0, -u*x, -u*y, u],
                     [0, 0, 0, x, y, 1, -v*x, -v*y, v]])
    for col in range(8):
        pivot = max(range(col, 8), key=lambda i: abs(rows[i][col]))
        if abs(rows[pivot][col]) < 1e-10:
            raise ValueError('Panel outline is too degenerate to align')
        rows[col], rows[pivot] = rows[pivot], rows[col]
        divisor = rows[col][col]
        rows[col] = [v/divisor for v in rows[col]]
        for i in range(8):
            if i != col:
                factor = rows[i][col]
                rows[i] = [a-factor*b for a, b in zip(rows[i], rows[col])]
    a, b, c, d, e, f, g, h = [row[8] for row in rows]

    def mapped(point):
        x, y = point
        denominator = g*x+h*y+1
        if abs(denominator) < 1e-9:
            raise ValueError('Perspective mapping crosses infinity')
        result = [(a*x+b*y+c)/denominator, (d*x+e*y+f)/denominator]
        if not all(math.isfinite(value) for value in result):
            raise ValueError('Perspective mapping produced invalid coordinates')
        return result
    return mapped


def align_profile(reference, corners):
    """Map the active, immutable layout to a new panel outline; never compound drafts."""
    if 'board_corners' not in reference:
        raise ValueError('This legacy profile has no panel outline. Start with calibration.json or use per-digit editing.')
    source = validate_corners(reference['board_corners'], reference['reference_size'])
    target = validate_corners(corners, reference['reference_size'])
    mapped = perspective_map(source, target)
    profile = deepcopy(reference)
    profile['board_corners'] = target
    for name in FIELDS:
        x, y, w, h = reference['digits'][name]
        quad = [mapped(point) for point in ((x, y), (x+w, y), (x+w, y+h), (x, y+h))]
        # Tiny numerical errors must not grow identity bounds by a pixel.
        left, top = [math.floor(round(min(p[i] for p in quad), 6)) for i in (0, 1)]
        right, bottom = [math.ceil(round(max(p[i] for p in quad), 6)) for i in (0, 1)]
        profile['digits'][name] = [left, top, right-left, bottom-top]
        profile['segment_centers'][name] = [[round(v) for v in mapped(point)]
                                            for point in reference['segment_centers'][name]]
    return validate_profile(profile, reference)


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
    if 'board_corners' in payload:
        result['board_corners'] = validate_corners(payload['board_corners'], reference['reference_size'])
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
