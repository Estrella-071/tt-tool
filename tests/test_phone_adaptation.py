# SPDX-License-Identifier: GPL-3.0-only
"""Fishing localization learns offsets from confirmed controls, never guesses."""
import time
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from adb_app import PHONE_DEFAULTS
from fisher.adb import Frame
from fisher.config import ROOT
from fisher.controller import Decision
from fisher.phone_runtime import PhoneRunner
from fisher.phone_vision import PhoneDetector
from tests.fixtures import make_frame


def shifted(image, x, y):
    height, width = image.shape[:2]
    return cv2.warpAffine(image, np.float32([[1, 0, x], [0, 1, y]]),
                          (width, height), borderValue=(30, 30, 30))


class PhoneAdaptationTests(unittest.TestCase):
    def test_idle_alignment_converges_and_follows_later_timing_screen(self):
        detector = PhoneDetector(ROOT/'assets/templates')
        idle = shifted(make_frame('IDLE'), 20, 35)
        for _ in range(16):
            obs, _ = detector.detect(idle)
        self.assertEqual(obs.state, 'IDLE')
        self.assertTrue(detector.alignment_ready)
        self.assertAlmostEqual(detector.alignment[0], 20/336, places=3)
        self.assertAlmostEqual(detector.alignment[1], 35/598, places=3)
        obs, _ = detector.detect(shifted(make_frame('TIMING'), 20, 35))
        self.assertEqual(obs.state, 'TIMING')

    def test_unrecognized_image_cannot_create_a_calibration(self):
        detector = PhoneDetector(ROOT/'assets/templates')
        for _ in range(24):
            obs, _ = detector.detect(np.full((598, 336, 3), 80, np.uint8))
        self.assertEqual(obs.state, 'UNKNOWN')
        self.assertFalse(detector.alignment_ready)
        self.assertEqual(detector.alignment, (0., 0.))

    def test_manual_mode_never_learns_or_applies_a_saved_offset(self):
        detector = PhoneDetector(ROOT/'assets/templates')
        detector.set_alignment((.06, .06));detector.adaptive = False
        image = make_frame('IDLE')
        for _ in range(20):obs, _ = detector.detect(image)
        self.assertEqual(obs.state, 'IDLE')
        self.assertEqual(detector._alignment_count, 0)

    def test_wrong_saved_offset_converges_to_new_confirmed_geometry(self):
        detector = PhoneDetector(ROOT/'assets/templates')
        detector.set_alignment((.09, .08))
        idle = make_frame('IDLE')
        for _ in range(80):
            obs, _ = detector.detect(idle)
        self.assertEqual(obs.state, 'IDLE')
        self.assertLess(abs(detector.alignment[0]), .025)
        self.assertLess(abs(detector.alignment[1]), .025)

    @patch('fisher.phone_runtime.Adb')
    def test_detected_translation_adjusts_default_tap_but_not_detected_hook(self, _):
        runner = PhoneRunner('adb', 'serial', dict(PHONE_DEFAULTS), (1000, 500), 'com.game')
        runner.settings['humanize'] = False
        runner.observe_only = False;runner.active.set()
        runner.foreground_ok = True;runner.foreground_at = time.perf_counter()
        runner.controller = Mock();runner.alignment = (.04, -.03)
        now = time.perf_counter();frame = Frame(np.zeros((800, 360, 3), np.uint8), now, now, .02)
        self.assertTrue(runner._send(Decision(action='CAST'), frame, (0, 0, 360, 800)))
        x, y = runner.adb.tap.call_args.args
        self.assertAlmostEqual(x, 270);self.assertAlmostEqual(y, 825)
        runner.hook_point = (.52, .70)
        self.assertTrue(runner._send(Decision(action='HOOK'), frame, (0, 0, 360, 800)))
        x, y = runner.adb.tap.call_args.args
        self.assertAlmostEqual(x, 260);self.assertAlmostEqual(y, 700)

    @patch('fisher.phone_runtime.Adb')
    def test_live_reconfiguration_is_copied_and_does_not_end_the_session(self, _):
        runner = PhoneRunner('adb', 'serial', dict(PHONE_DEFAULTS), (1000, 500), 'com.game')
        runner.active.set();runner.session_started.set()
        requested = dict(PHONE_DEFAULTS, layout_mode='manual', crop=[.05, 0, .95, 1])
        self.assertTrue(runner.reconfigure(requested))
        requested['crop'][0] = .2
        command, settings = runner.commands.get_nowait()
        self.assertEqual((command, settings['layout_mode'], settings['crop'][0]), ('reconfigure','manual',.05))
        self.assertTrue(runner.active.is_set());self.assertTrue(runner.session_started.is_set())


if __name__ == '__main__':
    unittest.main()
