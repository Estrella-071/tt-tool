# SPDX-License-Identifier: GPL-3.0-only
"""Recognize the anonymous chest action from geometry, not game text."""
import itertools
import unittest
from pathlib import Path

import cv2
import numpy as np

from fisher.ruins_chest import chest_button_target


FIXTURES = Path(__file__).parent / 'assets' / 'ruins'
CHEST = {'chest_batch.png': (180.5, 730.), 'chest_confirm.png': (180.5, 730.),
         'chest_split.png': (265.5, 730.)}


def load(name):
    image = cv2.imdecode(np.fromfile(FIXTURES / name, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f'Fixture unavailable: {name}')
    return cv2.resize(image, (360, 800), interpolation=cv2.INTER_AREA)


class ChestButtonTests(unittest.TestCase):
    def test_both_real_anonymized_results_and_other_ruins_states(self):
        for path in sorted(FIXTURES.glob('*.png')):
            with self.subTest(name=path.name):
                target = chest_button_target(load(path.name))
                if path.name in CHEST:
                    self.assertIsNotNone(target)
                    self.assertAlmostEqual(target[0]*360, CHEST[path.name][0], delta=5)
                    self.assertAlmostEqual(target[1]*800, CHEST[path.name][1], delta=5)
                else:
                    self.assertIsNone(target)

    def test_compression_resizing_and_screen_offset_preserve_button_position(self):
        for name in CHEST:
            image = load(name)
            for quality, scale, dx, dy in itertools.product((60, 85, 100), (.95, 1., 1.05),
                                                              (-10, 0, 10), (-12, 0, 12)):
                ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
                self.assertTrue(ok)
                compressed = cv2.imdecode(data, cv2.IMREAD_COLOR)
                transform = cv2.getRotationMatrix2D((180, 725), 0, scale)
                transform[:, 2] += (dx, dy)
                shifted = cv2.warpAffine(compressed, transform, (360, 800))
                target = chest_button_target(shifted)
                expected = transform @ np.array((*CHEST[name], 1.))
                with self.subTest(name=name, quality=quality, scale=scale, dx=dx, dy=dy):
                    self.assertIsNotNone(target)
                    self.assertAlmostEqual(target[0] * 360, expected[0], delta=5)
                    self.assertAlmostEqual(target[1] * 800, expected[1], delta=5)

    def test_button_labels_and_progress_counter_are_not_required(self):
        for name in ('chest_batch.png', 'chest_confirm.png'):
            image = load(name)
            image[692:718, 145:215] = (20, 20, 20)
            image[718:745, 125:235] = image[730, 70]
            with self.subTest(name=name):
                self.assertIsNotNone(chest_button_target(image))

    def test_split_button_labels_and_count_can_change_without_ocr(self):
        image = load('chest_split.png')
        # Keep the dark capsule body while covering its digits and both button
        # labels; their shapes and language are irrelevant to the detector.
        image[698:708, 74:116] = image[713, 90]
        image[720:744, 43:145] = image[730, 30]
        image[720:744, 215:320] = image[730, 200]
        target = chest_button_target(image)
        self.assertIsNotNone(target)
        self.assertAlmostEqual(target[0]*360, 265.5, delta=5)

    def test_split_page_requires_both_aligned_buttons_and_the_capsule(self):
        original = load('chest_split.png')
        no_badge = original.copy()
        no_badge[709:717, 67:124] = original[730, 30]
        self.assertIsNone(chest_button_target(no_badge))
        missing_left = original.copy()
        missing_left[700:760, :180] = 0
        self.assertIsNone(chest_button_target(missing_left))
        missing_right = original.copy()
        missing_right[700:760, 180:] = 0
        self.assertIsNone(chest_button_target(missing_right))
        misaligned = original.copy()
        misaligned[700:760, 180:] = 0
        misaligned[718:778, 180:] = original[700:760, 180:]
        self.assertIsNone(chest_button_target(misaligned))
        bright = original.copy()
        bright[80:200, :80] = 255
        self.assertIsNone(chest_button_target(bright))

    def test_wide_green_bar_without_teal_backdrop_or_dark_overlay_is_rejected(self):
        original = load('chest_confirm.png')
        bar_only = np.zeros_like(original)
        bar_only[709:752] = original[709:752]
        self.assertIsNone(chest_button_target(bar_only))
        bright = original.copy()
        bright[80:200, :80] = 255
        self.assertIsNone(chest_button_target(bright))
        teal_only = original.copy()
        teal_only[705:760] = 0
        self.assertIsNone(chest_button_target(teal_only))
        self.assertIsNone(chest_button_target(None))
        self.assertIsNone(chest_button_target(np.zeros((360, 800, 3), np.uint8)))
        self.assertIsNone(chest_button_target(np.zeros((800, 360, 3), np.float32)))


if __name__ == '__main__':
    unittest.main()
