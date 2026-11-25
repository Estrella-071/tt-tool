# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests for probability parsing under stream artefacts."""
import unittest
from pathlib import Path

import cv2
import numpy as np

from fisher.ruins_odds import recognize_probability


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests' / 'assets' / 'ruins'
CASES = {
    'boss90': (90, 5), 'boss90_bonus_stream': (90, 5),
    'boss80': (80, 0), 'boss80_stream': (80, 0),
    'boss80_bonus_stream': (80, 5), 'boss70_bonus_stream': (70, 5),
    'boss55_bonus_stream': (55, 5), 'boss55_bonus8_stream': (55, 8),
    'boss30_bonus_stream': (30, 5), 'boss25_bonus8_stream': (25, 8),
    'boss20_stream': (20, 0), 'boss20_bonus8_stream': (20, 8),
    'boss45': (45, 5), 'boss50_red': (50, 0),
    'boss25_bonus5_stuck': (25, 5),
}


class RuinsOddsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        atlas = cv2.imread(str(ROOT / 'assets/ruins/digits.png'), cv2.IMREAD_GRAYSCALE)
        cls.digits = [[atlas[row*20:(row+1)*20, digit*16:(digit+1)*16] > 0
                       for row in range(atlas.shape[0] // 20)] for digit in range(10)]

    def read(self, image):
        return recognize_probability(cv2.cvtColor(image, cv2.COLOR_BGR2HSV), self.digits)[:2]

    def image(self, name):
        return cv2.imread(str(FIXTURES / (name + '.png')))

    def test_captured_rates_and_bonus_are_correct(self):
        for name, expected in CASES.items():
            with self.subTest(name=name):
                self.assertEqual(self.read(self.image(name)), expected)

    def test_small_screen_translations_do_not_join_frame_and_digits(self):
        for name, expected in CASES.items():
            image = self.image(name)
            for dx in (-2, 0, 2):
                for dy in (-3, -1, 0, 1, 3):
                    shifted = cv2.warpAffine(image, np.float32([[1, 0, dx], [0, 1, dy]]), (360, 800))
                    with self.subTest(name=name, dx=dx, dy=dy):
                        self.assertEqual(self.read(shifted), expected)

    def test_compressed_eighty_percent_plus_bonus_remains_readable(self):
        image = self.image('boss80_bonus_stream')
        for quality in (75, 85, 95, 100):
            ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            self.assertTrue(ok)
            with self.subTest(quality=quality):
                self.assertEqual(self.read(cv2.imdecode(data, cv2.IMREAD_COLOR)), (80, 5))

    def test_real_stalled_twenty_five_plus_five_with_compression_and_subpixel_alignment(self):
        # Anonymous lower-screen crop from the actual 25% + 5% encounter.
        # At 75/80/85 the first percent splits across two or three components;
        # the recorded device profile also shifts x/y by around half a pixel.
        image = self.image('boss25_bonus5_stuck')
        transform = np.float32([[1, 0, -.00136766*360], [0, 1, -.00079045*800]])
        for quality in (75, 80, 85, 90, 95, 100):
            ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            self.assertTrue(ok)
            compressed = cv2.imdecode(data, cv2.IMREAD_COLOR)
            with self.subTest(quality=quality, aligned=False):
                self.assertEqual(self.read(compressed), (25, 5))
            aligned = cv2.warpAffine(compressed, transform, (360, 800), flags=cv2.INTER_LINEAR)
            with self.subTest(quality=quality, aligned=True):
                self.assertEqual(self.read(aligned), (25, 5))

    def test_compression_does_not_turn_eighty_into_fifty_or_bonus_eight_into_three(self):
        for name, dx, dy in (('boss80_bonus_stream', -.492, -3),
                             ('boss55_bonus8_stream', 1, 0)):
            expected = CASES[name]
            image = self.image(name)
            transformed = cv2.warpAffine(image, np.float32([[1, 0, dx], [0, 1, dy]]), (360, 800))
            ok, data = cv2.imencode('.jpg', transformed, [cv2.IMWRITE_JPEG_QUALITY, 75])
            self.assertTrue(ok)
            with self.subTest(name=name):
                self.assertIn(self.read(cv2.imdecode(data, cv2.IMREAD_COLOR)), (expected, (None, None)))

    def test_narrow_first_digits_on_existing_bonus_layout(self):
        atlas = cv2.imread(str(ROOT / 'assets/ruins/digits.png'), cv2.IMREAD_GRAYSCALE)
        original = cv2.cvtColor(self.image('boss20_bonus8_stream'), cv2.COLOR_BGR2HSV)
        for value, positions in ((10, ((1,254,4),(0,260,8))),
                                 (11, ((1,258,4),(1,264,4))),
                                 (100, ((1,244,4),(0,250,8),(0,260,8)))):
            hsv = original.copy()
            hsv[705:724, 230:269] = (100, 0, 55)
            for digit, x, width in positions:
                glyph = cv2.resize(atlas[:20, digit*16:(digit+1)*16],
                                   (width, 11), interpolation=cv2.INTER_NEAREST) > 0
                hsv[710:721, x:x+width][glyph] = (32, 230, 240)
            with self.subTest(value=value):
                self.assertEqual(recognize_probability(hsv, self.digits)[:2], (value, 8))

    def test_compression_with_shift_never_changes_the_known_rate(self):
        # Unknown is acceptable; a low rate must never be promoted to a high one.
        for name, expected in CASES.items():
            image = self.image(name)
            for quality in (65, 75, 85, 95, 100):
                for dx, dy in ((0, 0), (-2, -3), (2, 2), (2, 0)):
                    shifted = cv2.warpAffine(image, np.float32([[1, 0, dx], [0, 1, dy]]), (360, 800))
                    ok, data = cv2.imencode('.jpg', shifted, [cv2.IMWRITE_JPEG_QUALITY, quality])
                    self.assertTrue(ok)
                    observed = self.read(cv2.imdecode(data, cv2.IMREAD_COLOR))
                    with self.subTest(name=name, quality=quality, dx=dx, dy=dy):
                        self.assertIn(observed, (expected, (None, None)))

    def test_missing_bonus_or_plus_is_not_treated_as_zero_bonus(self):
        original = self.image('boss45')
        for x1, x2 in ((300, 324), (289, 294), (309, 324)):
            image = original.copy()
            image[706:724, x1:x2] = 0
            with self.subTest(x1=x1, x2=x2):
                self.assertEqual(self.read(image), (None, None))
        # Compression has hidden the plus and second percent simultaneously.
        image = self.image('boss55_bonus8_stream')
        image = cv2.warpAffine(image, np.float32([[1, 0, 2], [0, 1, 2]]), (360, 800))
        ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 65])
        self.assertTrue(ok)
        self.assertEqual(self.read(cv2.imdecode(data, cv2.IMREAD_COLOR)), (None, None))

    def test_missing_glyph_strokes_do_not_turn_eighty_or_ninety_into_thirty_or_ten(self):
        for name in ('boss80_bonus_stream', 'boss90_bonus_stream'):
            original = self.image(name)
            for x, width in ((249, 4), (250, 3), (251, 2), (252, 1), (252, 2)):
                image = original.copy()
                image[704:725, x:x+width] = 0
                with self.subTest(name=name, x=x, width=width):
                    self.assertEqual(self.read(image), (None, None))

        # A whole missing leading digit was previously classified as 0% with
        # confidence 1.0, causing the controller to abandon an 80% encounter.
        image = self.image('boss80_stream')
        image[706:724, 270:278] = 0
        self.assertEqual(self.read(image), (None, None))


if __name__ == '__main__':
    unittest.main()
