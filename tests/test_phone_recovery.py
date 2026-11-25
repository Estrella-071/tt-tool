# SPDX-License-Identifier: GPL-3.0-only
"""Phone-only recovery of acknowledged input, screens and capture streams."""
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from adb_app import PHONE_DEFAULTS
from fisher.adb import Frame
from fisher.config import DEFAULTS, ROOT
from fisher.controller import Controller, Decision
from fisher.phone_runtime import ObservationHold, PhoneRecovery, PhoneRunner
from fisher.phone_vision import PhoneDetector
from fisher.vision import Observation


class PhoneRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(DEFAULTS, continuous_fishing=True)
        self.controller = Controller(self.cfg)
        self.controller.reset(10.)
        self.recovery = PhoneRecovery()

    def step(self, obs, now):
        decision = self.controller.step(obs, now)
        return self.recovery.resolve(self.controller, obs, decision, now)

    def test_stalled_real_idle_retries_after_resume_without_resetting_counts(self):
        image = cv2.imread(str(ROOT / 'tests/assets/phone_idle_stalled.png'))
        obs, _ = PhoneDetector(ROOT / 'assets/templates', .68).detect(image)
        self.assertEqual(obs.state, 'IDLE')
        with patch('fisher.phone_runtime.Adb'):
            runner = PhoneRunner('adb', 'test', dict(PHONE_DEFAULTS), (2670,1200), 'com.game')
        runner._command('start', False, self.controller, 10.)
        self.controller.cast_count = 681; self.controller.result_count = 664
        for t in (10., 10.2):
            self.assertIsNone(self.step(obs, t).action)
        decision = self.step(obs, 10.6)
        self.assertEqual(decision.action, 'CAST')
        self.controller.commit('CAST', 10.6)
        runner._command('pause', '已暫停', self.controller, 16.)
        runner._command('start', False, self.controller, 46.)
        self.recovery.reset()
        for t in (46., 46.2, 46.4):
            decision = self.step(obs, t)
            self.assertFalse(decision.pause)
            self.assertIsNone(decision.action)
        decision = self.step(obs, 46.6)
        self.assertEqual((decision.action, decision.ack_retry), ('CAST', True))
        runner.controller = self.controller
        runner._commit_input(decision, 46.6)
        self.assertEqual((self.controller.cast_count, self.controller.result_count), (682, 664))
        self.assertEqual(self.controller.pending_ack, ('IDLE', 46.6))
        self.assertTrue(runner.active.is_set())

    def test_retry_requires_fresh_matching_frames_and_is_rate_limited(self):
        c = self.controller
        c.state = c.candidate = 'IDLE'; c.candidate_count = 2
        c.cast_count = 7; c.result_count = 6; c.commit('CAST', 10.)
        idle = Observation('IDLE', 1.)
        for t, obs in ((16., idle), (16.2, idle), (16.4, Observation()),
                       (16.5, idle), (16.7, idle), (16.9, idle)):
            decision = self.step(obs, t)
            self.assertFalse(decision.pause)
            self.assertIsNone(decision.action)
        retry = self.step(idle, 17.1)
        self.assertEqual((retry.action, retry.ack_retry), ('CAST', True))
        c.commit(retry.action, 17.1, ack_retry=retry.ack_retry)
        self.assertEqual((c.cast_count, c.result_count), (8, 6))
        for t in (17.2, 17.4, 18., 19., 21.9):
            decision = self.step(idle, t)
            self.assertFalse(decision.pause)
            self.assertIsNone(decision.action)

    def test_uncertain_retry_does_not_increment_cast_count(self):
        with patch('fisher.phone_runtime.Adb'):
            runner = PhoneRunner('adb', 'test', dict(PHONE_DEFAULTS), (2670,1200), 'com.game')
        runner.controller = self.controller
        self.controller.cast_count = 682; self.controller.pending_ack = ('IDLE', 10.)
        runner._uncertain_input(Decision(action='CAST', ack_retry=True), OSError('timeout'))
        self.assertEqual(self.controller.cast_count, 682)
        self.assertEqual(self.controller.pending_ack[0], 'IDLE')
        self.assertGreater(self.controller.pending_ack[1], 10.)

    def test_hook_retry_uses_same_bite_until_a_real_transition(self):
        c = self.controller
        c.state = c.candidate = 'BITE'; c.candidate_count = 2
        c.cast_count = 682; c.result_count = 664; c.commit('HOOK', 10.)
        obs = Observation('BITE', .92)
        for t in (16., 16.2, 16.4):
            self.assertIsNone(self.step(obs, t).action)
        retry = self.step(obs, 16.6)
        self.assertEqual((retry.action, retry.ack_retry), ('HOOK', True))
        c.commit(retry.action, 16.6, ack_retry=retry.ack_retry)
        self.assertEqual((c.cast_count, c.result_count), (682, 664))
        for t in (17., 17.2):
            self.step(Observation('WAIT', 1.), t)
        self.assertIsNone(c.pending_ack)

    def test_finite_mode_caps_cast_attempts_including_retries(self):
        c = Controller(dict(DEFAULTS, continuous_fishing=False, max_casts=2))
        c.reset(0.); recovery = PhoneRecovery(); idle = Observation('IDLE', 1.)
        for t in (0., .2, .6):
            decision = recovery.resolve(c, idle, c.step(idle, t), t)
        self.assertEqual(decision.action, 'CAST')
        c.commit('CAST', .6)
        for t in (6., 6.2, 6.4, 6.6):
            decision = recovery.resolve(c, idle, c.step(idle, t), t)
        self.assertEqual((decision.action, decision.ack_retry), ('CAST', True))
        c.commit('CAST', 6.6, ack_retry=True)
        self.assertEqual((c.cast_count, c.cast_attempt_count), (1, 2))
        for t in (12., 12.2, 12.4, 12.6):
            decision = recovery.resolve(c, idle, c.step(idle, t), t)
        self.assertTrue(decision.pause)
        self.assertEqual(decision.pause_code, 'cast_limit')
        for t in (13., 13.2):
            recovery.resolve(c, Observation('WAIT', 1.), c.step(Observation('WAIT', 1.), t), t)
        for t in (14., 14.2, 14.6):
            decision = recovery.resolve(c, idle, c.step(idle, t), t)
        self.assertTrue(decision.pause)
        self.assertEqual(decision.pause_code, 'cast_limit')

    def test_unknown_wait_and_timing_timeouts_keep_observing(self):
        c = self.controller
        for t in (11., 71.1, 132.):
            decision = self.step(Observation(), t)
            self.assertFalse(decision.pause)
            self.assertIsNone(decision.action)
        for t in (133., 133.2, 133.6):
            decision = self.step(Observation('IDLE', 1.), t)
        self.assertEqual(decision.action, 'CAST')
        c.state = c.candidate = 'WAIT'; c.candidate_count = 3; c.entered = 0.
        decision = self.step(Observation('WAIT', 1.), 140.)
        self.assertFalse(decision.pause); self.assertIsNone(decision.action)
        self.assertEqual(self.step(Observation('BITE', .92), 140.3).action, 'HOOK')
        c.state = c.candidate = 'TIMING'; c.candidate_count = 3; c.entered = 0.
        c.shot_locked = True
        decision = self.step(Observation('TIMING', 1.), 150.)
        self.assertFalse(decision.pause); self.assertIsNone(decision.action)
        self.assertFalse(c.shot_locked)
        self.assertFalse(self.step(Observation('TIMING', 1.), 150.2).pause)

    def test_explicit_limits_still_pause(self):
        c = Controller(dict(DEFAULTS, continuous_fishing=False, max_session_minutes=1))
        c.reset(0.)
        decision = self.recovery.resolve(c, Observation(), c.step(Observation(), 61.), 61.)
        self.assertTrue(decision.pause)
        self.assertEqual(decision.pause_code, 'duration_limit')

    def test_overlapping_observation_and_manual_pause_are_each_deferred_once(self):
        c = self.controller
        c.entered = 1.; c.pending_ack = ('IDLE', 1.); c.cast_count = 7; c.result_count = 6
        hold = ObservationHold()
        hold.begin(10.); hold.begin(12.)  # stream and foreground overlap
        self.assertTrue(hold.end(c, 15.))
        self.assertFalse(hold.end(c, 15.))
        with patch('fisher.phone_runtime.Adb'):
            runner = PhoneRunner('adb', 'test', dict(PHONE_DEFAULTS), (2670,1200), 'com.game')
        runner.active.set(); runner.session_started.set()
        runner._command('pause', '已暫停', c, 15.)
        runner._command('start', False, c, 25.)
        self.assertEqual((c.entered, c.pending_ack), (16., ('IDLE', 16.)))
        self.assertEqual((c.cast_count, c.result_count), (7, 6))
        self.assertTrue(runner.active.is_set())

    def test_slow_fresh_frames_can_confirm_retry_but_missing_frames_cannot(self):
        c = self.controller
        c.state = c.candidate = 'IDLE'; c.candidate_count = 2
        c.commit('CAST', 10.)
        idle = Observation('IDLE', 1.)
        for t in (16., 17.):
            self.assertIsNone(self.step(idle, t).action)
        retry = self.step(idle, 18.)
        self.assertEqual((retry.action, retry.ack_retry), ('CAST', True))
        self.recovery.reset()
        for t in (20., 23.1, 26.2):
            self.assertIsNone(self.step(idle, t).action)
        self.assertIsNone(self.step(Observation(), 26.3).action)
        for t in (27., 28.):
            self.assertIsNone(self.step(idle, t).action)
        self.assertEqual(self.step(idle, 29.).action, 'CAST')


    def test_resume_pipeline_retries_actual_idle_without_new_session(self):
        with patch('fisher.phone_runtime.Adb'):
            runner = PhoneRunner('adb', 'test', dict(PHONE_DEFAULTS, humanize=False, layout_mode='manual'),
                                 (2670,1200), 'com.game')
        c = self.controller
        c.state = c.candidate = 'IDLE'; c.candidate_count = 2
        c.cast_count = 682; c.result_count = 664; c.pending_ack = ('IDLE', 10.6)
        runner.session_started.set(); runner.paused_at = 16.; runner.commands.put(('start', False))
        runner.foreground_ok = True; runner.foreground_ready = lambda now: True
        clock, sequence, active_at_tap = [46.], [0], []
        runner.capture = Mock(); runner.capture.width = 360; runner.capture.height = 800
        frame_image = np.zeros((800,360,3), np.uint8)
        def snapshot():
            if runner.adb.tap.called:
                active_at_tap.append(runner.active.is_set()); runner.stop.set()
                return None, None
            sequence[0] += 1; clock[0] += .1; runner.foreground_at = clock[0]
            return Frame(frame_image, clock[0], clock[0], .02, sequence[0], .01), None
        runner.capture.snapshot.side_effect = snapshot
        detector = Mock(); detector.detect.return_value = (Observation('IDLE', .95), frame_image)
        c.reset = Mock()
        with patch('fisher.phone_runtime.Controller', return_value=c), \
             patch('fisher.phone_runtime.PhoneDetector', return_value=detector), \
             patch('fisher.phone_runtime.time.perf_counter', side_effect=lambda: clock[0]):
            runner._run()
        self.assertEqual(active_at_tap, [True])
        runner.adb.tap.assert_called_once()
        self.assertEqual((c.cast_count, c.result_count), (682, 664))
        self.assertGreater(c.pending_ack[1], 46.)


    def test_slow_detection_pipeline_eventually_retries_a_stuck_cast(self):
        for stream_interval in (.1, 1.):
            with self.subTest(stream_interval=stream_interval), patch('fisher.phone_runtime.Adb'):
                runner = PhoneRunner('adb', 'test', dict(PHONE_DEFAULTS, humanize=False, layout_mode='manual',
                                                       capture_interval=1.), (2670,1200), 'com.game')
                c = Controller(dict(DEFAULTS, continuous_fishing=True))
                c.state = c.candidate = 'IDLE'; c.candidate_count = 2
                c.cast_count = 682; c.result_count = 664; c.pending_ack = ('IDLE', 10.)
                c.reset = Mock()
                runner.session_started.set(); runner.active.set(); runner.observe_only = False
                runner.foreground_ok = True; runner.foreground_ready = lambda now: True
                runner.capture = Mock(); runner.capture.width = 360; runner.capture.height = 800
                image = np.zeros((800,360,3), np.uint8)
                clock, seq, previous, current = [46.], [0], [0.], [None]
                def snapshot():
                    if runner.adb.tap.called or clock[0] > 55.:
                        runner.stop.set()
                        return None, None
                    clock[0] += .1; runner.foreground_at = clock[0]
                    if current[0] is None or clock[0]-previous[0] >= stream_interval-1e-6:
                        previous[0] = clock[0]; seq[0] += 1
                        current[0] = Frame(image, clock[0], clock[0], .02, seq[0], .01)
                    return current[0], None
                runner.capture.snapshot.side_effect = snapshot
                detector = Mock(); detector.detect.return_value = (Observation('IDLE', .95), image)
                with patch('fisher.phone_runtime.Controller', return_value=c), \
                     patch('fisher.phone_runtime.PhoneDetector', return_value=detector), \
                     patch('fisher.phone_runtime.time.perf_counter', side_effect=lambda: clock[0]):
                    runner._run()
                runner.adb.tap.assert_called_once()
                self.assertEqual((c.cast_count, c.result_count), (682, 664))


if __name__ == '__main__':
    unittest.main()
