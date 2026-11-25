# SPDX-License-Identifier: GPL-3.0-only
"""Offline regressions: no attached device, no injected input."""
import dataclasses
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch, Mock
import numpy as np
from fisher.adb import Adb, AdbError, Frame, LatestCapture, MotionGate, StreamCapture, StreamFailure, crop_frame, validate_phone_settings
from fisher.controller import Decision
from fisher.phone_runtime import PhoneRunner
from fisher.phone_vision import PhoneDetector
from fisher.config import ROOT
from fisher.vision import Observation
from adb_app import PHONE_DEFAULTS
from fixtures import make_frame


class AdbTests(unittest.TestCase):
    @patch('fisher.phone_runtime.Adb')
    def test_stream_reconnect_discards_old_display_before_new_frame(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game')
        now=time.perf_counter();frame=Frame(np.zeros((800,360,3),np.uint8),now,now,.02,1,.01)
        old=Mock();old.width=360;old.height=800;old.thread.is_alive.return_value=False;r.capture=old
        states = []
        def before_reconnect():
            states.append(r.ready.is_set())
            if len(states) == 1:
                return frame,None
            return frame,'USB disconnected'
        old.snapshot.side_effect = before_reconnect
        replacement=Mock();replacement.width=360;replacement.height=800;replacement.thread.is_alive.return_value=False
        def no_frame():
            states.append(r.ready.is_set());r.stop.set();return None,None
        replacement.snapshot.side_effect=no_frame
        detector=Mock();detector.detect.return_value=(Observation('UNKNOWN'),np.zeros((800,360,3),np.uint8))
        with patch('fisher.phone_runtime.StreamCapture',return_value=replacement),patch('fisher.phone_runtime.PhoneDetector',return_value=detector):r._run()
        messages=[]
        while not r.messages.empty():messages.append(r.messages.get_nowait())
        self.assertTrue(any('正在重連' in msg.get('status','') for msg in messages))
        self.assertFalse(any('error' in msg for msg in messages));replacement.start.assert_called_once()
        self.assertEqual(states, [False, True, False])

    @patch("fisher.phone_runtime.Adb")
    def test_default_foreground_ignores_launcher_and_accepts_game(self, _):
        runner = PhoneRunner("adb", "x", dict(PHONE_DEFAULTS), (1000, 500))
        runner.adb.closed.is_set.return_value = False
        runner.adb.foreground.side_effect = ["com.android.launcher3", "com.farlightgames.pgame.gp"]
        states = []

        def tick(_):
            states.append(runner.foreground_ok)
            if len(states) == 2:
                runner.stop.set()

        with patch.object(runner.stop, "wait", side_effect=tick):
            runner._guard()
        self.assertEqual(states, [False, True])
        self.assertTrue(runner.foreground_recovered.is_set())
        runner.adb.tap.assert_not_called()

    @patch("fisher.phone_runtime.Adb")
    def test_permanent_stream_failure_reports_reason_without_restart_in_both_modes(self, _):
        from fisher.ruins_runtime import RuinsRunner
        for runner_type in (PhoneRunner, RuinsRunner):
            with self.subTest(runner=runner_type):
                runner = runner_type("adb", "x", dict(PHONE_DEFAULTS), (1000, 500))
                error = StreamFailure("缺少解碼器", "FFmpeg: Unknown decoder", retry=False)
                runner.capture = Mock()
                runner.capture.snapshot.return_value = (None, error)
                with patch.object(runner, "_create_capture") as restart:
                    runner._run()
                self.assertEqual(runner.messages.get_nowait(), {
                    "error": "缺少解碼器", "diagnostic": "FFmpeg: Unknown decoder", "fatal": True,
                })
                self.assertFalse(runner.ready.is_set())
                restart.assert_not_called()
                runner.adb.tap.assert_not_called()
    @patch('fisher.phone_runtime.Adb')
    def test_foreground_adb_error_blocks_without_disarming(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game');r.active.set()
        r.adb.closed.is_set.return_value=False;r.adb.foreground.side_effect=OSError('USB disconnected')
        monitor=Mock();monitor.update.return_value=(False,'前景驗證持續失敗');monitor.last_reason='USB disconnected'
        with patch('fisher.phone_runtime.ForegroundMonitor',return_value=monitor),patch.object(r.stop,'wait',side_effect=lambda _:r.stop.set()):r._guard()
        self.assertTrue(r.active.is_set());self.assertFalse(r.foreground_ok);self.assertTrue(r.commands.empty())
    @patch('fisher.phone_runtime.Adb')
    def test_other_app_does_not_disarm_and_game_focus_recovers(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game');r.active.set()
        r.adb.closed.is_set.return_value=False;r.adb.foreground.side_effect=['com.game','other.app','other.app','other.app','com.game']
        ticks=iter((0.,1.,2.,3.,4.));checks=[]
        def wait(_):
            checks.append((r.foreground_ok,r.active.is_set()))
            if len(checks)==5:r.stop.set()
        with patch('fisher.phone_runtime.time.perf_counter',side_effect=lambda:next(ticks)),patch.object(r.stop,'wait',side_effect=wait):r._guard()
        self.assertEqual(checks,[(True,True),(False,True),(False,True),(False,True),(True,True)])
        self.assertTrue(r.foreground_recovered.is_set());self.assertTrue(r.commands.empty());r.adb.tap.assert_not_called()

    @patch('fisher.phone_runtime.Adb')
    def test_foreground_interruption_does_not_advance_controller(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game');r.active.set();r.foreground_ok=False
        r.capture=Mock();r.capture.width=360;r.capture.height=800
        now=time.perf_counter();frame=Frame(np.zeros((800,360,3),np.uint8),now,now,.02,1,.01);r.capture.snapshot.return_value=(frame,None)
        controller=Mock();controller.cast_count=0;controller.result_count=0
        detector=Mock();detector.detect.return_value=(Observation('UNKNOWN'),np.zeros((598,336,3),np.uint8))
        r.emit=lambda data:r.stop.set()
        with patch('fisher.phone_runtime.Controller',return_value=controller),patch('fisher.phone_runtime.PhoneDetector',return_value=detector):r._run()
        controller.step.assert_not_called();r.adb.tap.assert_not_called()

    @patch('fisher.phone_runtime.Adb')
    def test_expired_foreground_sample_does_not_advance_controller(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game');r.active.set();r.foreground_ok=True;r.foreground_at=time.perf_counter()-2
        r.capture=Mock();r.capture.width=360;r.capture.height=800
        now=time.perf_counter();r.capture.snapshot.return_value=(Frame(np.zeros((800,360,3),np.uint8),now,now,.02,1,.01),None)
        controller=Mock();controller.cast_count=0;controller.result_count=0
        detector=Mock();detector.detect.return_value=(Observation('UNKNOWN'),np.zeros((598,336,3),np.uint8));r.emit=lambda data:r.stop.set()
        with patch('fisher.phone_runtime.Controller',return_value=controller),patch('fisher.phone_runtime.PhoneDetector',return_value=detector):r._run()
        controller.step.assert_not_called();r.adb.tap.assert_not_called()

    def test_foreground_wait_defers_screen_deadlines_without_resetting_counts(self):
        from fisher.controller import Controller
        from fisher.config import DEFAULTS
        c=Controller(DEFAULTS);c.reset(10);c.entered=20;c.unknown_since=21;c.pending_ack=('IDLE',22);c.next_result_press_at=23;c.last_press=24;c.cast_count=7;c.result_count=6
        c.defer_observation_timers(30)
        self.assertEqual((c.started,c.entered,c.unknown_since,c.pending_ack,c.next_result_press_at,c.last_press),(10,50,51,('IDLE',52),53,54))
        self.assertEqual((c.cast_count,c.result_count),(7,6))

    @patch('fisher.phone_runtime.Adb')
    def test_controller_resumes_when_other_app_returns_focus(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game');r.active.set();r.foreground_ok=False
        r.capture=Mock();r.capture.width=360;r.capture.height=800;count=[0]
        def snapshot():
            time.sleep(.012)
            count[0]+=1
            if count[0]>=3:r.foreground_ok=True;r.foreground_at=time.perf_counter()
            if count[0]>=4:r.stop.set()
            now=time.perf_counter();return Frame(np.zeros((800,360,3),np.uint8),now,now,.02,count[0],.01),None
        r.capture.snapshot.side_effect=snapshot
        controller=Mock();controller.cast_count=0;controller.result_count=0;controller.step.return_value=Decision()
        detector=Mock();detector.detect.return_value=(Observation('UNKNOWN'),np.zeros((598,336,3),np.uint8))
        with patch('fisher.phone_runtime.Controller',return_value=controller),patch('fisher.phone_runtime.PhoneDetector',return_value=detector):r._run()
        controller.defer_observation_timers.assert_called_once();self.assertGreaterEqual(controller.step.call_count,1);r.adb.tap.assert_not_called()
    def test_config_rejects_nan_invalid_crop_and_fractional_limit(self):
        for extra in ({'tap_x':float('nan')}, {'tap_y':1.01}, {'crop':[0,0,2,1]},
                      {'capture_interval':0}, {'max_casts':1.5}, {'continuous':'true'},
                      {'input_latency_ms':True}, {'stream_delay_ms':-1}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_phone_settings(dict(PHONE_DEFAULTS, **extra))

    def test_crop_preserves_mapping(self):
        image=np.zeros((1000,500,3),np.uint8)
        crop,box=crop_frame(image,[.1,.2,.8,.7])
        self.assertEqual(crop.shape,(700,400,3))
        self.assertEqual(box,(50,200,400,700))
        with self.assertRaises(ValueError):crop_frame(image,[0,0,.01,.01])

    @patch('fisher.adb.shutil.which',return_value='adb.exe')
    def test_device_selection_never_implicit(self,_):
        adb=Adb()
        with self.assertRaises(AdbError):adb.capture()
        adb.close()
        with self.assertRaises(AdbError):adb.devices()

    @patch('fisher.adb.shutil.which',return_value='adb.exe')
    def test_enumerates_all_states_without_choosing(self,_):
        adb=Adb()
        with patch.object(adb,'call',return_value=b'List of devices attached\na device model:X\nb unauthorized\nc offline\n'):
            self.assertEqual([(d.serial,d.state) for d in adb.devices()], [('a','device'),('b','unauthorized'),('c','offline')])
        self.assertIsNone(adb.serial)

    @patch('fisher.adb.shutil.which',return_value='adb.exe')
    def test_foreground_parsing_and_rotation_guard(self,_):
        adb=Adb(serial='x')
        with patch.object(adb,'call',return_value=b'mCurrentFocus=Window{abc u0 com.game/.Main}\n mRotation=0 mDeferred=0'):
            self.assertEqual(adb.foreground(),'com.game')
        with patch.object(adb,'call',return_value=b'mCurrentFocus=Window{abc u0 com.game/.Main}\n mRotation=1 mDeferred=0'):
            with self.assertRaises(AdbError):adb.foreground()
        with patch.object(adb,'call',return_value=b'mCurrentFocus=null'):
            with self.assertRaises(AdbError):adb.foreground()

    @patch('fisher.adb.shutil.which',return_value='adb.exe')
    def test_host_command_uses_argument_vector_and_selected_serial(self,_):
        adb=Adb(serial='device-one')
        process=Mock();process.communicate.return_value=(b'ok',b'');process.returncode=0
        with patch('fisher.adb.subprocess.Popen',return_value=process) as spawn:
            adb.tap(123.9,456.8)
        args=spawn.call_args.args[0]
        self.assertEqual(args[1:],['-s','device-one','shell','input','tap','123','456'])
        self.assertNotIn('shell',spawn.call_args.kwargs)

    @patch('fisher.adb.shutil.which',return_value='adb.exe')
    def test_timeout_kills_process_without_retrying_tap(self,_):
        adb=Adb(serial='x');p=Mock();p.communicate.side_effect=[subprocess.TimeoutExpired('adb',2),(b'',b'')]
        with patch('fisher.adb.subprocess.Popen',return_value=p) as spawn:
            with self.assertRaises(AdbError):adb.tap(1,2)
        p.kill.assert_called_once();spawn.assert_called_once()
        self.assertEqual(adb._processes,set())

    @patch('fisher.adb.shutil.which',return_value='adb.exe')
    def test_capture_rejects_invalid_binary(self,_):
        adb=Adb(serial='x')
        with patch.object(adb,'call',return_value=b'error'):
            with self.assertRaises(AdbError):adb.capture()

    def test_latest_capture_has_no_frame_backlog_and_stops_on_error(self):
        adb=Mock();image=np.zeros((120,120,3),np.uint8)
        adb.capture.side_effect=[Frame(image,0,0,.1), Frame(image,1,1,.1), AdbError('offline')]
        c=LatestCapture(adb,0);c.start();c.thread.join(2)
        frame,error=c.snapshot()
        self.assertEqual(frame.sequence,2);self.assertIn('offline',error)
        self.assertFalse(c.thread.is_alive())

    def test_stall_and_direction_gate(self):
        gate=MotionGate()
        for i,x in enumerate((180,175,170)):
            ready=gate.observe(Observation('TIMING',marker=x),i*.05)
        self.assertTrue(ready);self.assertEqual(gate.direction,-1)
        self.assertFalse(gate.fresh(1))
        self.assertFalse(gate.observe(Observation('TIMING',marker=170),.5))
        self.assertFalse(gate.observe(Observation('UNKNOWN'),.6))
        self.assertEqual(gate.confirmed,0)

    def test_tall_phone_keeps_template_scale(self):
        detector=PhoneDetector(ROOT/'assets/templates')
        original=make_frame('IDLE')
        tall=np.concatenate((np.full((150,336,3),220,np.uint8),original))
        obs,frame=detector.detect(tall)
        self.assertEqual(obs.state,'IDLE');self.assertEqual(frame.shape,(598,336,3))

    @patch('fisher.phone_runtime.Adb')
    def test_dispatch_cancellation_stale_frame_and_foreground_fail_closed(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game')
        r.settings["humanize"]=False
        r.observe_only=False;r.active.set();r.foreground_ok=True;r.foreground_at=time.perf_counter()
        r.controller=Mock()
        image=np.zeros((800,360,3),np.uint8)
        old=Frame(image,time.perf_counter()-2,time.perf_counter()-2,.1)
        self.assertFalse(r._send(Decision(action='CAST'),old,(0,0,360,800)))
        frame=Frame(image,time.perf_counter(),time.perf_counter(),.1)
        r.foreground_ok=False
        self.assertFalse(r._send(Decision(action='CAST'),frame,(0,0,360,800)))
        r.adb.tap.assert_not_called()

    @patch('fisher.phone_runtime.Adb')
    def test_dispatch_maps_stream_pixels_to_physical_phone(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game')
        r.settings["humanize"]=False
        r.observe_only=False;r.active.set();r.foreground_ok=True;r.foreground_at=time.perf_counter()
        r.controller=Mock()
        frame=Frame(np.zeros((800,360,3),np.uint8),time.perf_counter(),time.perf_counter(),.02)
        self.assertTrue(r._send(Decision(action='CAST'),frame,(0,0,360,800)))
        x,y=r.adb.tap.call_args.args
        self.assertAlmostEqual(x,250);self.assertAlmostEqual(y,855)
        r.controller.commit.assert_called_once()
        r.pause();r.adb.tap.reset_mock()
        self.assertFalse(r._send(Decision(action='CAST'),frame,(0,0,360,800)))
        r.adb.tap.assert_not_called()

    def test_record_modal_can_move_between_vertical_anchors(self):
        detector=PhoneDetector(ROOT/'assets/templates')
        original=make_frame('RESULT','purple')
        tall=np.full((748,336,3),25,np.uint8)
        tall[102:700]=original
        obs,_=detector.detect(tall)
        self.assertEqual((obs.state,obs.variant),('RESULT','record'))

    def test_claim_geometry_requires_dark_backdrop_and_gold_heading(self):
        import cv2
        detector=PhoneDetector(ROOT/'assets/templates')
        image=np.full((748,336,3),20,np.uint8)
        cv2.rectangle(image,(95,650),(240,680),(40,220,90),-1)
        cv2.putText(image,'CLAIM',(120,671),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),2)
        # A green button alone does not qualify.
        obs,_=detector.detect(image)
        self.assertNotEqual(obs.state,'RESULT')
        cv2.putText(image,'REWARD',(70,90),cv2.FONT_HERSHEY_SIMPLEX,1,(20,210,255),3)
        obs,_=detector.detect(image)
        self.assertEqual((obs.state,obs.variant),('RESULT','claim'))
        self.assertGreater(obs.scores['tap_y'],.8)

    def test_error_dialog_recognition_stops_when_the_dialog_disappears(self):
        from fisher.vision import read_image
        detector=PhoneDetector(ROOT/'assets/templates')
        image=read_image(ROOT/'tests/assets/ruins/error_dialog.png')
        for _ in range(4):
            obs,_=detector.detect(image)
        self.assertEqual(obs.state,'ERROR')
        self.assertAlmostEqual(obs.scores['tap_x'],.5,delta=.02)
        self.assertAlmostEqual(obs.scores['tap_y'],.643,delta=.02)
        image[275:330,:]=0
        self.assertNotEqual(detector.detect(image)[0].state,'ERROR')

    def test_error_recovery_requires_stable_dialog_and_backs_off(self):
        from fisher.phone_runtime import ErrorRecoveryGate
        gate=ErrorRecoveryGate(); point=(.5,.64)
        self.assertFalse(gate.observe(point,10.))
        self.assertFalse(gate.observe(point,10.1))
        self.assertTrue(gate.observe(point,10.16))
        gate.dispatched(10.16)
        self.assertFalse(gate.observe(point,18.))
        self.assertTrue(gate.observe(point,18.17))
        gate.dispatched(18.17)
        self.assertFalse(gate.observe(point,40.))
        self.assertFalse(gate.observe(None,40.1))
        self.assertFalse(gate.observe(point,40.2))

    @patch('fisher.phone_runtime.Adb')
    def test_error_confirmation_uses_observed_point_without_changing_fishing_counts(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game')
        r.settings['humanize']=False
        r.observe_only=False;r.active.set();r.foreground_ok=True;r.foreground_at=time.perf_counter()
        r.controller=Mock();r.action_point=(.5,.643)
        frame=Frame(np.zeros((800,360,3),np.uint8),time.perf_counter(),time.perf_counter(),.02)
        self.assertTrue(r._send(Decision(action='ERROR_CLOSE'),frame,(0,0,360,800)))
        x,y=r.adb.tap.call_args.args
        self.assertAlmostEqual(x,250);self.assertAlmostEqual(y,643)
        r.controller.commit.assert_not_called()

    @patch('fisher.phone_runtime.Adb')
    def test_unknown_or_paused_controller_does_not_get_overridden_by_predictor(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game')
        r.capture=Mock();r.capture.width=360;r.capture.height=800
        now=time.perf_counter()
        frame=Frame(np.zeros((800,360,3),np.uint8),now,now,.02,1,.01)
        r.capture.snapshot.return_value=(frame,None)
        r.active.set();r.foreground_ok=True;r.foreground_at=now
        ctrl=Mock();ctrl.step.return_value=Decision(pause=True,reason='timing timeout')
        ctrl.cast_count=0;ctrl.result_count=0
        detector=Mock();detector.detect.return_value=(Observation('TIMING',1,170,(160,180),402,True,
            track_left=79,track_right=263),np.zeros((598,336,3),np.uint8))
        def emit(data):
            r.stop.set()
        r.emit=emit
        with patch('fisher.phone_runtime.Controller',return_value=ctrl), patch('fisher.phone_runtime.PhoneDetector',return_value=detector):
            r._run()
        self.assertEqual(r.status,'timing timeout')
        self.assertFalse(r.active.is_set())
        ctrl.phase.plan.assert_not_called()
        r.adb.tap.assert_not_called()

    @patch('fisher.phone_runtime.Adb')
    def test_missing_assets_stop_capture_and_report_failure(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game')
        r.capture=Mock()
        with patch('fisher.phone_runtime.PhoneDetector',side_effect=ValueError('missing template')):
            r._run()
        self.assertIn('missing template',r.messages.get_nowait()['error'])
        self.assertFalse(r.active.is_set())
        r.capture.close.assert_called_once()
        r.adb.close.assert_called_once()

    def test_real_phone_reel_prompt_is_actionable_without_text_matching(self):
        from fisher.vision import read_image
        image=np.full((598,336,3),170,np.uint8)
        image[330:545,65:265]=read_image(ROOT/'tests/assets/phone_bite.png')
        detector=PhoneDetector(ROOT/'assets/templates')
        obs,_=detector.detect(image)
        self.assertEqual(obs.state,'BITE')
        from fisher.controller import Controller
        from fisher.config import DEFAULTS
        c=Controller(DEFAULTS)
        decision=c.step(obs,10.,10.)
        self.assertEqual(decision.action,'HOOK')
        # Erase the title text, preserving the panel; no language dependency.
        image[342:367,80:255]=(180,70,150)
        obs,_=detector.detect(image)
        self.assertEqual(obs.state,'BITE')

    def test_reel_needs_progress_panel_and_button_together(self):
        from fisher.vision import read_image
        detector=PhoneDetector(ROOT/'assets/templates')
        original=np.full((598,336,3),170,np.uint8)
        original[330:545,65:265]=read_image(ROOT/'tests/assets/phone_bite.png')
        for region in ((slice(330,415),slice(65,265)), (slice(425,545),slice(100,240))):
            image=original.copy();image[region]=(170,170,170)
            obs,_=detector.detect(image)
            self.assertNotEqual(obs.state,'BITE')

    def test_capture_publication_wakes_consumer(self):
        from fisher.adb import LatestCapture
        adb=Mock();image=np.zeros((120,120,3),np.uint8)
        adb.capture.side_effect=[Frame(image,0,0,.1),AdbError('offline')]
        capture=LatestCapture(adb,0);capture.start()
        self.assertTrue(capture.available.wait(1))
        capture.thread.join(2)
        frame,error=capture.snapshot()
        self.assertEqual(frame.sequence,1)
        self.assertFalse(capture.available.is_set())

    def test_reel_detector_does_not_replace_yellow_timing_with_hook(self):
        detector=PhoneDetector(ROOT/'assets/templates')
        image=make_frame('TIMING')
        obs,_=detector.detect(image)
        self.assertEqual(obs.state,'TIMING')
        for width in (40,90,150):
            changed=image.copy()
            changed[397:408,110:110+width]=(0,235,255)
            obs,_=detector.detect(changed)
            self.assertNotEqual(obs.state,'BITE')

    def test_moving_gold_record_accepts_bronze_weight_icon(self):
        from fisher.vision import read_image
        image=make_frame('RESULT','gold')
        image[365:388,104:122]=read_image(ROOT/'tests/assets/phone_weight_bronze.png')
        tall=np.full((748,336,3),25,np.uint8)
        tall[102:700]=image
        obs,_=PhoneDetector(ROOT/'assets/templates').detect(tall)
        self.assertEqual((obs.state,obs.variant),('RESULT','record'))

    def test_phone_result_wait_and_retries_are_short_but_confirmed(self):
        from fisher.config import DEFAULTS
        from fisher.controller import Controller
        cfg=validate_phone_settings(dict(PHONE_DEFAULTS))
        c=Controller(dict(DEFAULTS,result_wait_s=cfg['result_wait_s'],
                          result_retry_s=cfg['result_retry_s'],result_retry_jitter_ms=0))
        obs=Observation('RESULT',.9,variant='claim')
        self.assertIsNone(c.step(obs,0).action)
        self.assertIsNone(c.step(obs,.02).action)
        self.assertIsNone(c.step(obs,1.01).action)
        d=c.step(obs,1.03)
        self.assertEqual(d.action,'CLOSE')
        c.commit('CLOSE',1.03)
        self.assertIsNone(c.step(obs,1.35).action)
        self.assertEqual(c.step(obs,1.39).action,'CLOSE')
        self.assertIsNone(c.step(Observation('UNKNOWN'),1.4).action)

    def test_old_phone_settings_gain_result_timing_without_resetting_other_fields(self):
        old=dict(PHONE_DEFAULTS,capture_interval=.04)
        old.pop('result_wait_s');old.pop('result_retry_s')
        cfg=validate_phone_settings(old)
        self.assertEqual(cfg['capture_interval'],.04)
        self.assertEqual(cfg['result_wait_s'],1.0)
        self.assertEqual(cfg['result_retry_s'],.35)

    @patch('fisher.phone_runtime.Adb')
    def test_humanized_hit_varies_position_without_delaying_deadline(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS,humanize=True),(1000,500),'com.game')
        r.active.set();r.observe_only=False;r.foreground_ok=True
        r.foreground_at=time.perf_counter();r.controller=Mock();r.gate.fresh=Mock(return_value=True)
        r.rng.seed(20)
        frame=Frame(np.zeros((800,360,3),np.uint8),time.perf_counter(),time.perf_counter(),.02)
        with patch('fisher.phone_runtime.time.sleep',side_effect=AssertionError('HIT delayed')):
            for i in range(12):
                self.assertTrue(r._send(Decision(action='HIT',valid_until=time.perf_counter()+.2),frame,(0,0,360,800)))
        points=[call.args for call in r.adb.tap.call_args_list]
        self.assertGreater(len(set(points)),1)
        for x,y in points:
            self.assertLessEqual((x-250)**2+(y-855)**2,4**2+.001)
        self.assertTrue(all(call.kwargs['hold_ms'] is None for call in r.adb.tap.call_args_list))

    @patch('fisher.adb.shutil.which',return_value='adb.exe')
    def test_short_press_is_bounded_and_has_no_drag(self,_):
        adb=Adb(serial='x')
        with patch.object(adb,'call') as call:
            adb.tap(100,200,hold_ms=55)
            self.assertEqual(call.call_args.args[0],['shell','input','swipe','100','200','100','200','55'])
            with self.assertRaises(ValueError):adb.tap(100,200,hold_ms=500)

    @patch('fisher.phone_runtime.Adb')
    def test_pause_during_human_reaction_cancels_input(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS,humanize=True),(1000,500),'com.game')
        r.active.set();r.observe_only=False;r.foreground_ok=True
        r.foreground_at=time.perf_counter();r.controller=Mock()
        frame=Frame(np.zeros((800,360,3),np.uint8),time.perf_counter(),time.perf_counter(),.02)
        with patch('fisher.phone_runtime.time.sleep',side_effect=lambda _:r.active.clear()):
            self.assertFalse(r._send(Decision(action='CAST'),frame,(0,0,360,800)))
        r.adb.tap.assert_not_called()

    def test_transient_foreground_query_failure_blocks_but_does_not_pause(self):
        from fisher.adb import ForegroundMonitor
        m=ForegroundMonitor('com.game')
        self.assertEqual(m.update(0,'com.game'),(True,None))
        self.assertEqual(m.update(.25,error='query timeout'),(False,None))
        self.assertEqual(m.update(.5,'com.game'),(True,None))
        self.assertEqual(m.update(10,error='no focus'),(False,None))
        allowed,reason=m.update(13.1,error='query timeout')
        self.assertFalse(allowed);self.assertIn('驗證持續失敗',reason)
        self.assertNotIn('離開遊戲',reason)

    def test_other_app_requires_sustained_matching_evidence(self):
        from fisher.adb import ForegroundMonitor
        m=ForegroundMonitor('com.game')
        self.assertEqual(m.update(0,'com.android.systemui'),(False,None))
        self.assertEqual(m.update(.25,'com.game'),(True,None))
        self.assertEqual(m.update(1,'com.other'),(False,None))
        self.assertEqual(m.update(1.5,'com.other'),(False,None))
        allowed,reason=m.update(2.1,'com.other')
        self.assertFalse(allowed);self.assertIn('com.other',reason)

    @patch('fisher.phone_runtime.Adb')
    def test_stale_foreground_evidence_blocks_without_disarming_then_recovers(self,_):
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS,humanize=False),(1000,500),'com.game')
        r.active.set();r.observe_only=False;r.foreground_ok=True;r.controller=Mock()
        frame=Frame(np.zeros((800,360,3),np.uint8),time.perf_counter(),time.perf_counter(),.02)
        r.foreground_at=time.perf_counter()-2
        self.assertFalse(r._send(Decision(action='CAST'),frame,(0,0,360,800)))
        self.assertTrue(r.active.is_set());r.adb.tap.assert_not_called()
        r.foreground_at=time.perf_counter()
        self.assertTrue(r._send(Decision(action='CAST'),frame,(0,0,360,800)))
        r.adb.tap.assert_called_once()

    @patch('fisher.phone_runtime.Adb')
    def test_ambiguous_adb_timeout_never_blindly_repeats_cast(self,_):
        from fisher.adb import AdbError
        r=PhoneRunner('adb','x',dict(PHONE_DEFAULTS,humanize=False),(1000,500),'com.game')
        r.active.set();r.observe_only=False;r.foreground_ok=True
        r.foreground_at=time.perf_counter();r.controller=Mock()
        r.adb.tap.side_effect=AdbError('timeout')
        frame=Frame(np.zeros((800,360,3),np.uint8),time.perf_counter(),time.perf_counter(),.02)
        self.assertFalse(r._send(Decision(action='CAST'),frame,(0,0,360,800)))
        r.adb.tap.assert_called_once()
        self.assertEqual(r.controller.commit.call_args.args[0],'CAST')
        self.assertTrue(r.active.is_set())
        self.assertIn('未確認',r.status)

    def test_voice_assistant_blocks_input_without_ending_short_interruption(self):
        from fisher.adb import ForegroundMonitor
        m=ForegroundMonitor('com.game')
        self.assertEqual(m.update(0,'com.game'),(True,None))
        for t in (.1,.6,1.2,4.0):
            self.assertEqual(m.update(t,'com.google.android.googlequicksearchbox'),(False,None))
        self.assertEqual(m.update(4.1,'com.game'),(True,None))
        self.assertEqual(m.update(5,'com.google.android.googlequicksearchbox'),(False,None))
        m.update(5.5,'com.google.android.googlequicksearchbox')
        self.assertIsNotNone(m.update(35.1,'com.google.android.googlequicksearchbox')[1])

    def test_full_phone_preview_preserves_uncropped_frame(self):
        from fisher.phone_runtime import preview_frame
        image=np.zeros((800,360,3),np.uint8)
        image[0,:,0]=255;image[-1,:,1]=255
        frame=Frame(image,0,0,.01)
        output=preview_frame(True,True,frame,np.zeros((598,336,3),np.uint8),Observation(),None)
        self.assertEqual(output.shape,(800,360,3))
        self.assertTrue((output[0,:,0]==255).all())
        self.assertTrue((output[-1,:,1]==255).all())
        self.assertIsNone(preview_frame(False,True,frame,None,None,None))


class StreamDiagnosticsTests(unittest.TestCase):
    def test_stderr_is_drained_bounded_and_classifies_only_stable_failures(self):
        adb = Mock(executable="adb", serial="PRIVATE-SERIAL")
        popen = subprocess.Popen

        def run_fixture(source_error, decoder_error):
            stream = StreamCapture(adb, (1000, 500), ffmpeg="custom-ffmpeg")
            command = []

            def spawn(args, **kwargs):
                command.append(args)
                error = source_error if len(command) == 1 else decoder_error
                script = "import sys; sys.stderr.buffer.write(b'x' * 128_000 + b'\\n' + " + repr(error) + ")"
                if len(command) == 2:
                    script += "; sys.stdin.buffer.read()"
                return popen([sys.executable, "-c", script], **kwargs)

            with patch("fisher.adb.shutil.which", return_value="custom-ffmpeg") as resolve:
                with patch("fisher.adb.subprocess.Popen", side_effect=spawn):
                    stream.start()
                    try:
                        self.assertTrue(stream.available.wait(5))
                    finally:
                        stream.close()
                        stream.thread.join(timeout=4)
                resolve.assert_called_once_with("custom-ffmpeg")
            self.assertFalse(stream.thread.is_alive())
            self.assertEqual(command[0], [
                "adb", "-s", "PRIVATE-SERIAL", "exec-out", "screenrecord",
                "--output-format=h264", "--size", "360x720",
                "--bit-rate", "1500000", "--time-limit", "0", "-",
            ])
            self.assertEqual(command[1][0], "custom-ffmpeg")
            return stream.snapshot()[1]

        errors = (
            (b"screenrecord: not found", b"Invalid data found when processing input", False, "手機不支援"),
            (b"", b"Unrecognized option 'fps_mode'", False, "FFmpeg 無法解碼"),
            (b"error: device 'PRIVATE-SERIAL' offline", b"Invalid data found when processing input", True, "影像串流結束"),
        )
        for source, decoder, retry, reason in errors:
            with self.subTest(reason=reason):
                error = run_fixture(source, decoder)
                self.assertEqual(error.retry, retry)
                self.assertTrue(error.message.startswith(reason))
                self.assertIn("ADB:", error.diagnostic)
                self.assertIn("FFmpeg:", error.diagnostic)
                self.assertNotIn("PRIVATE-SERIAL", error.diagnostic)
                if source:
                    self.assertIn(source.decode().replace("PRIVATE-SERIAL", "[device]"), error.diagnostic)
                self.assertIn(decoder.decode(), error.diagnostic)
                self.assertLessEqual(len(error.diagnostic), 820)

class SessionAndCaptureTests(unittest.TestCase):
    def test_pause_resume_preserves_counts_and_freezes_session_time(self):
        from fisher.controller import Controller
        from fisher.config import DEFAULTS
        runner=PhoneRunner('adb','x',dict(PHONE_DEFAULTS),(1000,500),'com.game')
        controller=Controller(dict(DEFAULTS))
        runner._command('start',False,controller,10.)
        controller.cast_count=7;controller.result_count=6;controller.pending_ack=('IDLE',12.)
        runner._command('pause','已暫停',controller,20.)
        runner._command('start',False,controller,50.)
        self.assertEqual((controller.cast_count,controller.result_count),(7,6))
        self.assertEqual(controller.started,40.)
        self.assertEqual(controller.pending_ack,('IDLE',42.))
        runner._command('end','已結束',controller,60.)
        self.assertEqual((controller.cast_count,controller.result_count),(7,6))
        runner._command('start',False,controller,70.)
        self.assertEqual((controller.cast_count,controller.result_count),(0,0))
        self.assertEqual(controller.started,70.)
    def test_capture_fps_uses_published_frames_and_expires(self):
        from fisher.adb import StreamCapture
        stream=StreamCapture(object(),(1000,500))
        stream.frame_times.extend((1.,1.1,1.2))
        self.assertAlmostEqual(stream.fps(1.2),10.)
        self.assertEqual(stream.fps(1.8),0.)

if __name__=='__main__':unittest.main()
