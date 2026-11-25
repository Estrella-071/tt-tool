# SPDX-License-Identifier: GPL-3.0-only
"""Result-banner recognition without relying on Chinese glyphs."""

import itertools
import unittest
from pathlib import Path

import cv2
import numpy as np

from fisher.ruins_battle_result import is_battle_result


FIXTURES = Path(__file__).parent / 'assets' / 'ruins'
POSITIVE = ('battle_win.png', 'battle_loss.png')


def load(path):
    # Windows game screenshot paths can contain characters outside the local
    # code page, which cv2.imread does not consistently support.
    encoded = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    return cv2.resize(image, (360, 800), interpolation=cv2.INTER_AREA)


class BattleResultTests(unittest.TestCase):
    def test_real_banners_and_all_other_anonymous_fixtures(self):
        for path in sorted(FIXTURES.glob('*.png')):
            with self.subTest(name=path.name):
                self.assertEqual(is_battle_result(load(path)), path.name in POSITIVE)

    def test_jpeg_scaling_and_moderate_offsets(self):
        for name in POSITIVE:
            source = load(FIXTURES / name)
            for quality in (100, 60):
                encoded = cv2.imencode('.jpg', source,
                                       [cv2.IMWRITE_JPEG_QUALITY, quality])[1]
                image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
                for scale, dx, dy in itertools.product((.95, 1., 1.05),
                                                       (-10, 0, 10),
                                                       (-12, 0, 12)):
                    transform = cv2.getRotationMatrix2D((180, 240), 0, scale)
                    transform[:, 2] += (dx, dy)
                    moved = cv2.warpAffine(image, transform, (360, 800))
                    with self.subTest(name=name, quality=quality, scale=scale,
                                      dx=dx, dy=dy):
                        self.assertTrue(is_battle_result(moved))

    def test_center_text_can_be_removed_or_replaced(self):
        for name in POSITIVE:
            image = load(FIXTURES / name)
            image[170:285, 75:285] = 0
            with self.subTest(name=name, text='removed'):
                self.assertTrue(is_battle_result(image))
            cv2.putText(image, 'RESULT', (90, 245), cv2.FONT_HERSHEY_SIMPLEX,
                        1.3, (255, 255, 255), 3)
            with self.subTest(name=name, text='latin'):
                self.assertTrue(is_battle_result(image))

    def test_coloured_rectangles_and_bad_inputs_are_not_results(self):
        for bgr in ((0, 200, 255), (200, 60, 130)):
            image = np.zeros((800, 360, 3), dtype=np.uint8)
            image[200:280, :] = bgr
            self.assertFalse(is_battle_result(image))
        self.assertFalse(is_battle_result(None))
        self.assertFalse(is_battle_result(np.zeros((360, 800, 3), np.uint8)))

if __name__ == '__main__':
    unittest.main()
