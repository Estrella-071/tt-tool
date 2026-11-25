import unittest
import os
import tempfile
from unittest.mock import patch
from fisher.sweep_profile import remember, adjusted_delay, load_biases
from fisher.sweep_calibration import calibration_consensus
from fisher.adb import StreamCapture
from fisher.bundled_tools import prepare_adb
from pathlib import Path
import numpy as np
from fisher.sweep import Observation, SweepController, detect, bottom_y

class SweepTests(unittest.TestCase):
    def test_unknown_frame_never_starts(self):
        c = SweepController()
        self.assertIsNone(c.step(detect(np.zeros((801, 360, 3), dtype=np.uint8)), 0))
        self.assertEqual(c.state, 'ready')

    def test_distinct_targets_allow_one_hit_each(self):
        c = SweepController(latency=0)
        self.assertEqual(c.step(Observation('ready'), 0), 'start')
        c.step(Observation('timing', .1, .4, .03), .1)
        for i, pos in enumerate((.15, .20, .25, .30, .35), 1):
            self.assertIsNone(c.step(Observation('timing', pos, .4, .03), .1+i*.03))
        self.assertEqual(c.step(Observation('timing', .4, .4, .03), .28), 'hit')
        for t in (.35, .40, .45, .50):
            c.step(Observation('timing', .4, .4, .03), t)
        c.step(Observation('timing', .3, .6, .03), .55)
        c.latency = 0
        for i, pos in enumerate((.35, .40, .45, .50, .55), 1):
            self.assertIsNone(c.step(Observation('timing', pos, .6, .03), .55+i*.03))
        self.assertEqual(c.step(Observation('timing', .6, .6, .03), .73), 'hit')

    def test_reversal_requires_new_motion_samples(self):
        c=SweepController(latency=.1);c.state='timing'
        for i,pos in enumerate((.3,.32,.34,.36)):
            c.step(Observation('timing',pos,.8,.02),i*.02)
        c.step(Observation('timing',.34,.8,.02),.08)
        self.assertEqual(c.direction,-1)
        self.assertEqual(len(c.motion),1)

    def test_tolerates_jitter_in_sample_times(self):
        c=SweepController(latency=.04);c.state='timing'
        samples=[(0,.20),(.021,.22),(.039,.24),(.059,.26),(.083,.28),(.101,.30)]
        for t,pos in samples:
            self.assertIsNone(c.step(Observation('timing',pos,.6,.025),t))
        self.assertGreaterEqual(len(c.motion),4)

    def test_disappearance_waits_for_next_screen(self):
        c=SweepController(); c.state='waiting'; c.last_hit_target=.5; c.hit_at=0
        for t in (0,.1,.2,.3): self.assertIsNone(c.step(Observation('unknown'), t))
        self.assertEqual(c.state,'waiting')
        self.assertIsNone(c.step(Observation('unknown'),1.6))
        self.assertEqual(c.state,'transition')
        self.assertIsNone(c.step(Observation('timing',.2,.5,.03),1.7))
        self.assertEqual(c.state,'timing')

    def test_target_flicker_does_not_rearm_stopped_marker(self):
        c=SweepController();c.state='waiting';c.hits=1;c.hit_at=0;c.last_hit_target=.5
        for t in (.1,.15,.2,.25,.3):
            c.step(Observation('timing',.4,.5,.03),t)
        self.assertTrue(c.wait_stopped)
        c.step(Observation('timing',.4,.7,.03),.32)
        self.assertEqual(c.state,'waiting')
        c.step(Observation('timing',.43,.7,.03),.34)
        self.assertEqual(c.state,'timing')

    def test_same_target_rearms_after_stop_and_restart(self):
        c=SweepController();c.state='waiting';c.hit_at=0;c.last_hit_target=.5
        for t in (.1,.15,.2,.25,.3):
            c.step(Observation('timing',.4,.5,.03),t)
        self.assertTrue(c.wait_stopped)
        c.step(Observation('timing',.43,.5,.03),.32)
        self.assertEqual(c.state,'timing')

    def test_waits_for_observed_reversal_before_predicting(self):
        c=SweepController(latency=.24);c.state='timing'
        for i,pos in enumerate((.40,.37,.34,.31,.28,.25)):
            self.assertIsNone(c.step(Observation('timing',pos,.43,.025),i*.02))
        self.assertEqual(c.direction,-1)
        c.step(Observation('timing',.27,.43,.025),.12)
        self.assertEqual(c.direction,1)

    def test_stop_timestamp_updates_device_delay(self):
        c=SweepController(latency=.263);c.hit_at=10.0
        c._learn_latency(10.225)
        self.assertAlmostEqual(c.latency,.225,places=3)

    def test_miss_corrects_latency_using_observed_velocity(self):
        c=SweepController(latency=.07);c.hit_at=10;c.hit_motion=(.43,-.8)
        c.last_hit_target=.36;c.wait_position=.38
        c._learn_latency(10.06)
        self.assertAlmostEqual(c.latency,.045,places=3)

    def test_invalid_stop_timestamp_does_not_change_delay(self):
        c=SweepController(latency=.263);c.hit_at=10.0
        c._learn_latency(10.9)
        self.assertEqual(c.latency,.263)

    def test_cancel_unsent_hit_rearms_without_counting_it(self):
        c = SweepController(); c.state = 'waiting'; c.hits = 1; c.hit_at = 5
        c.last_hit_target = .5; c.hit_motion = (.4, 1)
        c.cancel_pending_hit()
        self.assertEqual((c.state, c.hits, c.hit_at), ('timing', 0, None))
        c.cancel_pending_hit()
        self.assertEqual(c.hits, 0)

    def test_large_capture_gap_discards_velocity_samples(self):
        c = SweepController(latency=0, max_sample_gap=.035); c.state = 'timing'
        for t, p in ((0, .2), (.02, .22), (.04, .24), (.10, .30)):
            c.step(Observation('timing', p, .4, .02), t)
        self.assertEqual(len(c.motion), 1)

    def test_stopped_marker_records_visual_result_once(self):
        c = SweepController(); c.state = 'waiting'; c.hits = 1
        c.hit_at = 0; c.last_hit_target = .5; c.last_target_width = .04
        obs = Observation('timing', .51, .5, .04)
        c.step(obs, .16); c.step(obs, .30); c.step(obs, .45)
        self.assertEqual(c.results, ['黃色'])

    def test_stopped_marker_outside_yellow_is_reported(self):
        c = SweepController(); c.state = 'waiting'; c.hits = 1
        c.hit_at = 0; c.last_hit_target = .5; c.last_target_width = .04
        obs = Observation('timing', .54, .5, .04)
        c.step(obs, .16); c.step(obs, .30)
        self.assertEqual(c.results, ['未命中黃色'])

    def test_calibration_requires_agreement_between_independent_runs(self):
        self.assertIsNone(calibration_consensus([.08]))
        self.assertIsNone(calibration_consensus([.08,.25]))
        self.assertAlmostEqual(calibration_consensus([.08,.25,.09]),.085)

    def test_profile_learns_per_device_without_using_fixed_delay(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {'SWEEP_PROFILE_DIR':root}):
            self.assertEqual(adjusted_delay('one', .26), .26)
            self.assertTrue(remember('one', .26, .21))
            self.assertAlmostEqual(adjusted_delay('one', .28), .23)
            self.assertEqual(adjusted_delay('other', .28), .28)
            self.assertEqual(len(load_biases('one')),1)

    def test_schedules_near_center_and_accounts_for_wait_in_timing(self):
        c=SweepController(latency=0);c.state='timing'
        action=None
        for i,pos in enumerate((.30,.32,.34,.36,.38,.394)):
            action=c.step(Observation('timing',pos,.40,.025),i*.02)
            if action:
                self.assertGreater(c.hit_delay,0)
                self.assertLessEqual(c.hit_delay,.012)
                self.assertAlmostEqual(c.hit_at,i*.02+c.hit_delay)
                break
        self.assertEqual(action,'hit')

    def test_never_rearms_after_two_hits(self):
        c=SweepController();c.state='waiting';c.hits=2;c.hit_at=0;c.last_hit_target=.5
        for i in range(20):
            self.assertIsNone(c.step(Observation('timing',.2+i*.01,.7,.03),i*.05))
        self.assertEqual(c.state,'waiting')

    def test_closed_stream_does_not_spawn_processes(self):
        stream=StreamCapture(object(),(2670,1200))
        stream.stop.set()
        with patch('fisher.adb.subprocess.Popen') as spawn:
            stream._run()
            spawn.assert_not_called()

    def test_bundled_adb_is_copied_and_reused_from_stable_location(self):
        with tempfile.TemporaryDirectory() as root:
            source=Path(root)/'bundle';source.mkdir()
            for name in ('adb.exe','AdbWinApi.dll','AdbWinUsbApi.dll'):
                (source/name).write_bytes(name.encode())
            destination=prepare_adb(source,Path(root)/'local')
            self.assertEqual((destination/'adb.exe').read_bytes(),b'adb.exe')
            self.assertEqual(prepare_adb(source,Path(root)/'local'),destination)
            (source/'adb.exe').write_bytes(b'new version')
            self.assertNotEqual(prepare_adb(source,Path(root)/'local'),destination)

    def test_portrait_aspect_changes_preserve_bottom_anchored_timing(self):
        import cv2
        hsv = np.zeros((801, 360, 3), dtype=np.uint8)
        hsv[525:540, 150:165] = (172, 240, 240)
        hsv[510:520, 190:200] = (27, 240, 240)
        hsv[610:660, 100:240] = (85, 240, 240)
        base = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        for image in (base, base[161:], np.pad(base, ((161, 0), (0, 0), (0, 0)))):
            with self.subTest(shape=image.shape):
                observation = detect(image)
                self.assertEqual(observation.state, 'timing')
                self.assertAlmostEqual(observation.marker, 157/360, delta=.01)
        self.assertAlmostEqual(bottom_y((1920, 1080), 645), 1452)

    def test_wrong_aspect_rejected(self):
        self.assertEqual(detect(np.zeros((500,500,3),dtype=np.uint8)).state,'unknown')

if __name__=='__main__':unittest.main()
