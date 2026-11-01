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
    # The probe-era boxes were fitted around narrow 1s. Recover the left strokes
    # of wider glyphs, but keep the third slot clear of the physical colon.
    CLOCK_LEFT_PADDING = {'minutes_tens':.20, 'minutes_units':.12,
                          'seconds_tens':.04, 'seconds_units':.12}
    SCORE_MIN_CONTRAST = 20
    SCORE_LIGHT_FLOOR = 75
    SCORE_WHITE_LEVEL = 200
    SCORE_WHITE_FRACTION = .01
    # Keep the tail-based view stricter than the primary 95th-percentile mask,
    # without dropping moderately dimmer strokes beside bright vertical cores.
    SCORE_CORE_FRACTION = .6
    SCORE_LOCAL_KERNEL = 21
    SCORE_LOCAL_FRACTION = .45
    SCORE_LOCAL_FLOOR = 20
    SCORE_CHROMA_FRACTION = .6
    SCORE_CHROMA_MIN_CONTRAST = 20

    def __init__(self, config, template):
        import cv2
        import numpy as np
        self.cv, self.np = cv2, np
        self.template = template
        self.size = tuple(template['reference_size'])
        self.warp = cv2.getPerspectiveTransform(np.float32(config['board_corners']), np.float32(template['board_corners']))

    def _patches(self, frame):
        cv, np = self.cv, self.np
        image = cv.warpPerspective(frame, self.warp, self.size)
        patches = []
        for name in FIELDS:
            x, y, w, h = self.template['digits'][name]
            px, py = math.ceil(w*self.HORIZONTAL_PADDING), math.ceil(h*self.VERTICAL_PADDING)
            left = math.ceil(w*self.CLOCK_LEFT_PADDING.get(name,self.HORIZONTAL_PADDING))
            patch = image[max(0, y-py):min(image.shape[0], y+h+py),
                          max(0, x-left):min(image.shape[1], x+w+px)].astype(np.float32)
            patches.append(patch)
        return patches

    def masks(self, frame):
        """Primary masks for shape inspection or the separate OCR experiment."""
        return self._masks(self._patches(frame))

    def _masks(self, patches, *, score_cores=False):
        cv, np = self.cv, self.np
        # An independently thresholded blank window can promote brown panel
        # texture into LED foreground. Use the other clock slots as a brightness
        # reference too. This floor can only raise each local threshold; it never
        # declares a slot blank just because its own contrast is low.
        clock_patches = [patch for name,patch in zip(FIELDS,patches) if name in self.CLOCK_LEFT_PADDING]
        clock_low = float(np.percentile(np.concatenate([patch[:,:,0].ravel() for patch in clock_patches]),50))
        clock_high = max(float(np.percentile(patch[:,:,0],95)) for patch in clock_patches)
        clock_floor = max(150,clock_low+.6*(clock_high-clock_low))
        result = []
        for name,patch in zip(FIELDS,patches):
            r, g, b = [patch[:, :, i] for i in range(3)]
            low, high = np.percentile(r, [50, 95])
            threshold = max(150,float(low+.6*(high-low)))
            if name in self.CLOCK_LEFT_PADDING:
                threshold = max(threshold,clock_floor)
            foreground = (r >= g*.95) & (r-b > 35) & (r > threshold)
            if name in ('home','away'):
                # Red can saturate in the glow inside a hollow zero while its
                # actual LED cores become white. Red-only contrast then admits
                # the glow and removes the cores. Include their neutral light
                # when measuring contrast; retain the red brightness gate.
                neutral = np.minimum(g,b)
                light = np.maximum(r-np.maximum(g,b), (r+neutral)/2)
                low, high, tail = np.percentile(light, [50, 95, 99])
                # A narrow 1 can occupy less than 5% of its padded window.
                # Use the tail only when the usual reference has no contrast;
                # otherwise a few white peaks can erase a red digit's stem.
                if high-low < self.SCORE_MIN_CONTRAST:
                    high = tail
                if high-low < self.SCORE_MIN_CONTRAST:
                    foreground[:] = False
                elif score_cores:
                    threshold = max(self.SCORE_LIGHT_FLOOR,
                                    float(low+self.SCORE_CORE_FRACTION*(tail-low)))
                    foreground = (r >= g*.95) & (r > 150) & (light > threshold)
                elif np.mean(np.minimum(r,neutral) >= self.SCORE_WHITE_LEVEL) >= self.SCORE_WHITE_FRACTION:
                    threshold = max(self.SCORE_LIGHT_FLOOR,float(low+.6*(high-low)))
                    foreground = (r >= g*.95) & (r > 150) & (light > threshold)
            result.append(self._clean(foreground))
        return result

    def _clean(self, foreground):
        cv, np = self.cv, self.np
        mask = foreground.astype(np.uint8)*255
        mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        count, components, stats, _ = cv.connectedComponentsWithStats(mask)
        clean = np.zeros_like(mask)
        for i in range(1, count):
            if stats[i, cv.CC_STAT_AREA] >= 8:
                clean[components == i] = 255
        return clean

    def _local_scores(self, patches):
        """Complementary RGB top-hat evidence for faint, localized LED strokes."""
        cv, np = self.cv, self.np
        kernel = np.ones((self.SCORE_LOCAL_KERNEL, self.SCORE_LOCAL_KERNEL), np.uint8)
        result = {}
        for name, patch in zip(FIELDS, patches):
            if name not in ('home', 'away'):
                continue
            background = cv.morphologyEx(patch, cv.MORPH_OPEN, kernel)
            delta = np.maximum(0, patch-background)
            contrast = np.sqrt(np.sum(delta*delta, axis=2))
            tail = float(np.percentile(contrast, 99))
            threshold = max(self.SCORE_LOCAL_FLOOR, self.SCORE_LOCAL_FRACTION*tail)
            r, g = patch[:, :, 0], patch[:, :, 1]
            foreground = (r >= g*.95) & (r > 150) & (contrast > threshold)
            result[name] = {**self.inspect_digit(self._clean(foreground)),
                            'contrast_tail': round(tail, 3), 'contrast_threshold': round(threshold, 3)}
        return result

    def _chromatic_scores(self, patches, primary_masks):
        """Stronger red colour evidence within the existing primary foreground."""
        np = self.np
        result = {}
        for name, patch, primary in zip(FIELDS, patches, primary_masks):
            if name not in ('home', 'away'):
                continue
            r, g, b = [patch[:, :, i] for i in range(3)]
            chroma = r-np.maximum(g, b)
            low, high = np.percentile(chroma, [50, 99])
            threshold = max(self.SCORE_CHROMA_MIN_CONTRAST,
                            float(low+self.SCORE_CHROMA_FRACTION*(high-low)))
            foreground = ((r > 150) & (r >= g*.95) & (chroma > threshold)
                          & (high-low >= self.SCORE_CHROMA_MIN_CONTRAST)
                          & (primary != 0))
            white_fraction = float(np.mean(np.minimum(r, np.minimum(g,b)) >= self.SCORE_WHITE_LEVEL))
            inspection = self.inspect_digit(self._clean(foreground))
            # Discarding neutral LED centres can leave only coloured glow and
            # invent a competing digit. This view is inconclusive in that case.
            if white_fraction >= self.SCORE_WHITE_FRACTION:
                inspection.update(value=None, reason='neutral_cores')
            result[name] = {**inspection,
                            'white_core_fraction': round(white_fraction, 6),
                            'chroma_low': round(float(low), 3),
                            'chroma_high': round(float(high), 3),
                            'chroma_threshold': round(threshold, 3)}
        return result

    def observe(self, frame):
        """Inspect a frame, rejecting competing valid score interpretations.

        Complementary masks can veto, never replace, a primary digit. An
        unavailable shape is inconclusive, not a competing score. All
        inspections keep their crop, narrow-glyph and segment guards.
        """
        patches = self._patches(frame)
        primary_masks = self._masks(patches)
        evidence = self.inspect(primary_masks)
        cores = self.inspect(self._masks(patches, score_cores=True))
        local = self._local_scores(patches)
        chromatic = self._chromatic_scores(patches, primary_masks)
        for name in ('home', 'away'):
            item, core = evidence[name], cores[name]
            value = item['value']
            chroma = chromatic[name]
            alternative = chroma['value']
            chroma['mask_value'] = alternative
            # This view only removes primary foreground. Normalizing a thin
            # coloured rim can otherwise promote glow into a new "on" segment.
            if type(value) is int and type(alternative) is int and any(
                    a == '1' and p == '0' for a, p in zip(PATTERNS[alternative], PATTERNS[value])):
                chroma.update(value=None, reason='unsupported_added_segments')
            item.update(mask_value=value, score_core=core, score_local=local[name],
                        score_chroma=chroma)
            if type(value) is int and any(type(other['value']) is int and value != other['value']
                                          for other in (core, local[name], chromatic[name])):
                item.update(value=None, reason='score_mask_disagreement')
        return evidence

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
        """Shape-only mask diagnostics; use observe for full RGB recognition."""
        return {name: self.inspect_digit(mask) for name, mask in zip(FIELDS, masks)}

