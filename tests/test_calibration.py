"""Profile safety and diagnostics on displaced, scaled, and skewed synthetic digits."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from calibration import FIELDS, inspect_preview, validate_profile
from reader import FrameReader, PATTERNS

ROOT = Path(__file__).resolve().parents[1]


class CameraCalibration(unittest.TestCase):
    def setUp(self):
        self.reference = json.loads((ROOT / 'calibration.json').read_text())

    def test_invalid_profiles_are_rejected(self):
        changes = [lambda p: p.update(reference_size=[1280, 720]),
                   lambda p: p['digits'].pop('home'),
                   lambda p: p['segment_centers']['home'].pop(),
                   lambda p: p['segment_centers']['home'].__setitem__(0, [0, 0]),
                   lambda p: p['segment_centers']['home'].__setitem__(0, [float('nan'), 732]),
                   lambda p: p['segment_centers']['home'].__setitem__(0, [True, 732]),
                   lambda p: p['digits'].__setitem__('home', [621, 713, 1, 1])]
        for change in changes:
            profile = deepcopy(self.reference)
            change(profile)
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                validate_profile(profile, self.reference)

    def test_crop_is_derived_not_accepted_from_the_client(self):
        profile = deepcopy(self.reference)
        profile['crop'] = 'untrusted geometry'
        result = validate_profile(profile, self.reference)
        self.assertTrue(all(v % 2 == 0 for v in result['crop']))
        FrameReader(result)
        self.assertEqual(self.reference['crop'], [600, 500, 850, 360])

    def test_moved_digits_recognize_only_after_recalibration(self):
        shifted = deepcopy(self.reference)
        # A new camera position: shrink, translate, and shear each source point.
        transform = lambda x, y: [round(x*.7+y*.08+120), round(y*.65+35)]
        for name in FIELDS:
            x, y, w, h = shifted['digits'][name]
            left, top = transform(x, y)
            right, bottom = transform(x+w, y+h)
            shifted['digits'][name] = [left, top, right-left, bottom-top]
            shifted['segment_centers'][name] = [transform(*point) for point in shifted['segment_centers'][name]]
        profile = validate_profile(shifted, self.reference)
        width, height = [v//2 for v in profile['reference_size']]
        pixels = bytearray(width*height*3)
        expected = dict(zip(FIELDS, [1, 9, 5, 9, 2, 3]))
        # Draw independent blocks around each transformed source-pixel center.
        for name, digit in expected.items():
            for index, bit in enumerate(PATTERNS[digit]):
                if bit == '0':
                    continue
                px, py = shifted['segment_centers'][name][index]
                for y in range(round(py/2)-4, round(py/2)+5):
                    for x in range(round(px/2)-4, round(px/2)+5):
                        at = (y*width+x)*3
                        pixels[at:at+3] = bytes((255, 150, 150))
        preview = (bytes(pixels), width, height, 7, .3)
        self.assertIsNone(inspect_preview(self.reference, preview)['raw'])
        check = inspect_preview(profile, preview)
        self.assertEqual(check['digits'], expected)
        self.assertEqual(check['raw'], {'clock': '19:59', 'home': 2, 'away': 3})
        self.assertFalse(check['confirmed'])
        self.assertEqual(check['preview_sequence'], 7)
        self.assertEqual(check['preview_age'], .3)
        # The cropped production reader requires fresh repeated evidence after restart.
        x, y, w, h = profile['crop']
        cropped = b''.join(pixels[((y//2+row)*width+x//2)*3:((y//2+row)*width+(x+w)//2)*3] for row in range(h//2))
        reader = FrameReader(profile)
        self.assertIsNone(reader.read(cropped, 0)['values'])
        self.assertEqual(reader.read(cropped, .1)['values'], check['raw'])


if __name__ == '__main__':
    unittest.main()
