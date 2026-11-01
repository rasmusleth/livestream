"""Whole-region candidate; optional image packages are imported only on construction."""
import math
from calibration import FIELDS
from reader import PATTERNS


class RegionReader:
    # The probe-era boxes can cut through the top LED stroke even at nominal
    # alignment. Leave a guard around them, then reject foreground at that guard.
    # These are candidate heuristics for this panel, not learned accuracy bounds.
    VERTICAL_PADDING = .12
    HORIZONTAL_PADDING = .04
    EDGE_GUARD = 2

    def __init__(self, config, template):
        import cv2
        import numpy as np
        self.cv, self.np = cv2, np
        self.template = template
        self.size = tuple(template['reference_size'])
        self.warp = cv2.getPerspectiveTransform(np.float32(config['board_corners']), np.float32(template['board_corners']))

    def masks(self, frame):
        cv, np = self.cv, self.np
        image = cv.warpPerspective(frame, self.warp, self.size)
        result = []
        for name in FIELDS:
            x, y, w, h = self.template['digits'][name]
            # Keep horizontal padding smaller to avoid neighbouring digits and
            # the colon, which sit much closer than the rows above and below.
            px, py = math.ceil(w*self.HORIZONTAL_PADDING), math.ceil(h*self.VERTICAL_PADDING)
            patch = image[max(0, y-py):min(image.shape[0], y+h+py),
                          max(0, x-px):min(image.shape[1], x+w+px)].astype(np.float32)
            r, g, b = [patch[:, :, i] for i in range(3)]
            low, high = np.percentile(r, [50, 95])
            mask = ((r >= g*.95) & (r-b > 35) & (r > max(150, float(low+.6*(high-low))))).astype(np.uint8)*255
            mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            count, components, stats, _ = cv.connectedComponentsWithStats(mask)
            clean = np.zeros_like(mask)
            for i in range(1, count):
                if stats[i, cv.CC_STAT_AREA] >= 8:
                    clean[components == i] = 255
            result.append(clean)
        return result

    def inspect_digit(self, mask):
        """Return the observed digit and rejection evidence before normalization."""
        cv, np = self.cv, self.np
        result = {'value': None, 'reason': None, 'levels': [], 'bounds': None}
        ys, xs = np.where(mask != 0)
        if not len(xs):
            return {**result, 'value': 'blank', 'reason': 'no_foreground'}
        if len(xs) < mask.size*.008:
            return {**result, 'reason': 'insufficient_foreground'}
        if len(xs) > mask.size*.75:
            return {**result, 'reason': 'excess_foreground'}
        x, y, w, h = cv.boundingRect(mask)
        result['bounds'] = [x, y, w, h]
        # Resizing a clipped shape can turn it into another valid digit. Require
        # two clear pixels on every edge of the enlarged observation window.
        if min(x, y, mask.shape[1]-x-w, mask.shape[0]-y-h) < self.EDGE_GUARD:
            return {**result, 'reason': 'edge_foreground'}
        if h < mask.shape[0]*.45:
            return {**result, 'reason': 'short_foreground'}
        if w/h < .5:
            widths = np.count_nonzero(mask[y:y+h, x:x+w], axis=1)
            active = widths[widths > 0]
            # A narrow bounding box alone cannot distinguish 1 from a narrow 7
            # or a partial 9. A horizontal cap must not be ignored as a 1.
            if np.percentile(active, 90) > 2.2*np.median(active):
                return {**result, 'reason': 'ambiguous_narrow_glyph'}
            return {**result, 'value': 1}
        if w/h < .55:
            return {**result, 'reason': 'ambiguous_aspect'}
        normalized = cv.resize(mask[y:y+h, x:x+w], (64, 96), interpolation=cv.INTER_AREA)/255
        # Broad stroke areas, normalized to the observed foreground extent.
        areas = [(18, 0, 46, 16), (44, 18, 64, 40), (40, 56, 60, 78),
                 (14, 80, 38, 96), (0, 56, 20, 78), (4, 18, 24, 40), (18, 40, 38, 56)]
        levels = [float(normalized[y1:y2, x1:x2].mean()) for x1, y1, x2, y2 in areas]
        peak = max(levels)
        if peak < .1:
            return {**result, 'reason': 'weak_segments', 'levels': levels}
        relative = [v/peak for v in levels]
        bits = ''.join('1' if v >= .4 else '0' for v in relative)
        digit = next((n for n, pattern in PATTERNS.items() if pattern == bits), None)
        if min(abs(v-.4) for v in relative) < .04:
            digit = None
        return {**result, 'value': digit, 'reason': None if digit is not None else 'ambiguous_segments',
                'levels': [round(v, 3) for v in levels]}

    def digit(self, mask):
        evidence = self.inspect_digit(mask)
        return evidence['value'], evidence['levels']

    def inspect(self, masks):
        return {name: self.inspect_digit(mask) for name, mask in zip(FIELDS, masks)}

