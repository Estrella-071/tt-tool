# SPDX-License-Identifier: GPL-3.0-only
"""Phone runner: independent bounded capture, cancellable input, latest-only UI."""
from collections import deque
from copy import deepcopy
import queue
import random
import threading
import time
import cv2
from .adb import Adb, StreamCapture, StreamFailure, MotionGate, ForegroundMonitor, crop_frame, validate_phone_settings
from .config import DEFAULTS, ROOT
from .device_profiles import DeviceProfileStore
from .controller import Controller, Decision
from .vision import annotate, LABELS
from .phone_vision import PhoneDetector


CLASH_PACKAGE = "com.farlightgames.pgame.gp"


def preview_frame(enabled, full, frame, display, obs, prediction):
    if not enabled:
        return None
    if full:
        return frame.image
    return annotate(display, obs, prediction)


class ErrorRecoveryGate:
    """Confirm an on-screen dialog repeatedly and back off between retries."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.point = None
        self.since = None
        self.count = 0
        self.attempts = 0
        self.next_attempt = 0.

    def observe(self, point, now):
        if point is None:
            self.reset()
            return False
        if self.point is None or max(abs(a-b) for a, b in zip(point, self.point)) > .025:
            self.reset()
            self.point, self.since = point, now
        self.count += 1
        return self.count >= 3 and now-self.since >= .15 and now >= self.next_attempt

    def dispatched(self, now):
        self.attempts += 1
        self.next_attempt = now + (8. if self.attempts == 1 else 30.)


class PhoneRecovery:
    """Keep a phone session armed through recoverable observation timeouts."""
    ACK_STABLE_SECONDS = .45
    # Below the stream failure threshold; supports slow but fresh devices.
    ACK_MAX_GAP = 2.9

    def __init__(self):
        self.reset()

    def reset(self):
        self.ack = None
        self.since = self.seen = None
        self.frames = 0

    def resolve(self, controller, obs, decision, now):
        ack = controller.pending_ack
        if isinstance(ack, tuple) and len(ack) == 2 and ack[0] in ('IDLE', 'BITE') and obs.state == ack[0]:
            if (self.ack != ack or self.seen is None or now < self.seen
                    or now-self.seen > self.ACK_MAX_GAP):
                self.ack, self.since, self.frames = ack, now, 0
            self.seen = now
            self.frames += 1
        else:
            self.reset()
        if (decision.action == 'CAST' and not controller.cfg['continuous_fishing']
                and controller.cast_attempt_count >= controller.cfg['max_casts']):
            return Decision(reason='達到下鉤次數上限', pause=True, pause_code='cast_limit')
        if not decision.pause:
            return decision
        if decision.pause_code == 'action_ack_timeout':
            if (self.ack and self.frames >= 3 and self.since is not None
                    and now-self.since >= self.ACK_STABLE_SECONDS):
                action = 'CAST' if self.ack[0] == 'IDLE' else 'HOOK'
                if (action == 'CAST' and not controller.cfg['continuous_fishing']
                        and controller.cast_attempt_count >= controller.cfg['max_casts']):
                    return Decision(reason='達到下鉤次數上限', pause=True, pause_code='cast_limit')
                reason = '畫面已確認，重新下鉤' if action == 'CAST' else '畫面已確認，重新拉鉤'
                return Decision(action=action, reason=reason, ack_retry=True)
            return Decision(reason='等待畫面穩定後重試')
        if decision.pause_code == 'unknown_timeout':
            controller.unknown_since = now
            return Decision(reason='畫面未確認，持續等待')
        if decision.pause_code == 'wait_timeout':
            controller.entered = now
            return Decision(reason='等待上鉤，持續確認畫面')
        if decision.pause_code in ('timing_timeout', 'hit_ack_timeout'):
            controller.entered = now
            controller.phase = type(controller.phase)(controller.cfg, controller.latency, controller.speed)
            controller.contact = type(controller.contact)(controller.cfg, controller.latency, controller.speed)
            controller.motion.clear()
            controller.target = controller.target_candidate = controller.shot_target = None
            controller.target_count = 0
            controller.shot_locked = controller.round_reset_seen = False
            return Decision(reason='重新確認判定畫面')
        return decision


class ObservationHold:
    """Defer screen deadlines once for overlapping observation interruptions."""
    def __init__(self):
        self.since = None

    def begin(self, now):
        if self.since is None:
            self.since = now

    def end(self, controller, now):
        if self.since is None:
            return False
        controller.defer_observation_timers(max(0., now-self.since))
        self.since = None
        return True


class PhoneRunner:
    def __init__(self, executable, serial, settings, initial_shape, package=CLASH_PACKAGE, *, ffmpeg="ffmpeg"):
        self.settings = validate_phone_settings(settings)
        self.adb = Adb(executable, serial)
        self.shape = tuple(initial_shape)
        self.package = package
        self.ffmpeg = ffmpeg
        self.capture = self._create_capture()
        self.foreground_at = 0.
        self.foreground_ok = False
        self.foreground_recovered = threading.Event()
        self.foreground_note = "等待前景驗證"
        self.guard_thread = threading.Thread(target=self._guard, name="phone-foreground", daemon=True)
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.active = threading.Event()
        self.session_started = threading.Event()
        self.paused_at = None
        self.observe_only = True
        self.commands = queue.SimpleQueue()
        self.messages = queue.Queue(maxsize=2)
        self.thread = threading.Thread(target=self._run, name="phone-control", daemon=True)
        self.full_preview = threading.Event()
        self.preview = threading.Event()
        self.preview.set()
        self.gate = MotionGate()
        self.recovery = PhoneRecovery()
        self.pending = None
        self.status = "等待手機畫面"
        self.capture_times = deque(maxlen=30)
        self.action_ms = None
        self.action_point = None
        self.hook_point = None
        self.alignment = (0.0, 0.0)
        self.last_package_check = 0
        self.controller = None
        self.rng = random.Random()

    def _create_capture(self):
        return StreamCapture(self.adb, self.shape, self.settings["stream_delay_ms"]/1000,
                             self.settings["timing_uncertainty_ms"]/1000, ffmpeg=self.ffmpeg)

    def _stream_failure(self, frame, error, started, now):
        if error:
            return error if isinstance(error, StreamFailure) else StreamFailure(str(error))
        if frame is None and now-started > 6:
            return self.capture.failure("等待第一張可用畫面")
        if frame is not None and now-frame.received_at > 3:
            return self.capture.failure("手機畫面沒有更新")
        return None

    def _usable_frame(self, now, ready_message, active_message):
        self.ready.set()
        reconnecting = self.status.startswith("影像串流中斷")
        starting = self.status in ("等待手機畫面", "等待遊戲進入前景", ready_message)
        if self.active.is_set():
            if reconnecting:
                self.status = active_message
        elif starting or reconnecting:
            self.status = ready_message if self.foreground_ready(now) else "等待遊戲進入前景"

    def _fatal_stream(self, failure):
        self._pause(failure.message)
        self.emit({"error": failure.message, "diagnostic": failure.diagnostic, "fatal": True})

    def emit(self, data):
        try:
            self.messages.put_nowait(data)
        except queue.Full:
            try:
                self.messages.get_nowait()
            except queue.Empty:
                pass
            try:
                self.messages.put_nowait(data)
            except queue.Full:
                pass

    def start(self):
        self.capture.start()
        self.guard_thread.start()
        self.thread.start()

    def pause(self, reason="已暫停"):
        self.active.clear()
        self.commands.put(("pause", reason))

    def end(self, reason="已結束"):
        self.active.clear()
        self.commands.put(("end", reason))

    def arm(self, observe_only):
        self.commands.put(("start", bool(observe_only)))

    def reconfigure(self, settings, reset_calibration=False):
        """Queue a validated change for the control thread without ending a run."""
        cfg = validate_phone_settings(deepcopy(settings))
        if self.stop.is_set():
            return False
        if reset_calibration:
            cfg['_reset_calibration'] = True
        self.commands.put(('reconfigure', cfg))
        return True

    def close(self):
        self.active.clear()
        self.stop.set()
        self.ready.clear()
        self.capture.stop.set()
        self.capture.close()
        self.adb.close()

    def _guard(self):
        monitor = ForegroundMonitor(self.package)
        while not self.stop.is_set() and not self.adb.closed.is_set():
            try:
                package, error = self.adb.foreground(), None
            except OSError as exc:
                package, error = None, str(exc)
            now = time.perf_counter()
            was_foreground = self.foreground_ok
            self.foreground_ok, reason = monitor.update(now, package, error)
            if self.foreground_ok and not was_foreground:
                self.foreground_recovered.set()
            self.foreground_at = now
            self.foreground_note = monitor.last_reason
            if not self.foreground_ok:
                # No input during uncertainty; transient failures do not disarm.
                self.pending = None
                # A floating window can own focus while the game remains open.
                # Keep the session armed, but never tap until focus is verified.
            self.stop.wait(.25)

    def _pause(self, reason, now=None):
        if self.session_started.is_set() and self.paused_at is None:
            self.paused_at = time.perf_counter() if now is None else now
        self.active.clear()
        self.pending = None
        self.gate.reset()
        self.recovery.reset()
        self.status = reason

    def _command(self, name, arg, controller, now):
        if name == "pause":
            self._pause(arg, now)
        elif name == "end":
            self._pause(arg, now)
            self.session_started.clear()
            self.paused_at = None
        elif name == "start":
            if self.active.is_set():
                return
            self.observe_only = arg
            if not self.session_started.is_set():
                controller.reset(now)
                self.session_started.set()
            elif self.paused_at is not None:
                elapsed = max(0., now-self.paused_at)
                controller.started += elapsed
                controller.defer_observation_timers(elapsed)
                controller.phase = type(controller.phase)(controller.cfg, controller.latency, controller.speed)
            self.paused_at = None
            self.gate.reset()
            self.recovery.reset()
            self.pending = None
            self.active.set()
            self.status = "觀察測試中 · 不點擊" if arg else "自動釣魚中"

    def foreground_ready(self, now):
        return self.foreground_ok and now-self.foreground_at <= .8

    def _send(self, d, frame, box):
        now = time.perf_counter()
        if not self.active.is_set() or self.stop.is_set() or self.observe_only:
            return False
        if now-frame.captured_at > self.settings["max_frame_age"]:
            self.pending = None
            return False
        if d.valid_until is not None and now > d.valid_until:
            self.pending = None
            return False
        if d.action == "HIT" and not self.gate.fresh(now):
            self.pending = None
            return False
        # A separate guard refreshes foreground state; never block a hit deadline
        # on dumpsys. Reject stale foreground evidence before sending input.
        if not self.foreground_ok or now-self.foreground_at > .8:
            self.pending = None
            return False
        if self.settings["humanize"] and d.action != "HIT":
            lo, hi = (.015, .040) if d.action == "HOOK" else (.030, .090) if d.action == "CLOSE" else (.040, .120)
            until = time.perf_counter() + self.rng.uniform(lo, hi)
            while time.perf_counter() < until:
                if not self.active.is_set() or self.stop.is_set():
                    return False
                time.sleep(min(.001, max(0, until-time.perf_counter())))
        now = time.perf_counter()
        if (not self.active.is_set() or self.stop.is_set()
                or not self.foreground_ok or now-self.foreground_at > .8
                or now-frame.captured_at > self.settings["max_frame_age"]
                or (d.valid_until is not None and now > d.valid_until)):
            self.pending = None
            return False
        x, y, w, h = box
        start = time.perf_counter()
        sx = self.shape[1]/frame.image.shape[1]
        sy = self.shape[0]/frame.image.shape[0]
        point = (self.action_point if d.action in ("CLOSE", "ERROR_CLOSE") and self.action_point
                 else self.hook_point if d.action == "HOOK" and self.hook_point
                 else (min(1., max(0., self.settings["tap_x"] + self.alignment[0])),
                       min(1., max(0., self.settings["tap_y"] + self.alignment[1]))))
        px, py = (x + point[0]*w)*sx, (y + point[1]*h)*sy
        if self.settings["humanize"]:
            # A small disk around the confirmed button center, bounded by the crop.
            radius = min(w*sx, h*sy)*.008
            angle = self.rng.uniform(0, 6.283185307179586)
            distance = radius*self.rng.random()**.5
            import math
            px = min((x+w)*sx-1, max(x*sx, px+math.cos(angle)*distance))
            py = min((y+h)*sy-1, max(y*sy, py+math.sin(angle)*distance))
            # Keep yellow-bar inputs on their predicted deadline; vary location only.
            hold = None if d.action == "HIT" else self.rng.randint(35, 75)
            try:
                self.adb.tap(px, py, hold_ms=hold)
            except OSError as exc:
                return self._uncertain_input(d, exc)
        else:
            try:
                self.adb.tap(px, py)
            except OSError as exc:
                return self._uncertain_input(d, exc)
        end = time.perf_counter()
        self.action_ms = (end-start)*1000
        # ADB completion is not the actual touch timestamp. Do not learn it as such.
        self._commit_input(d, end)
        self.pending = None
        return True

    def _uncertain_input(self, decision, exc):
        # The device may have received the touch before adb failed. Never resend
        # blindly: retain the controller acknowledgement/shot lock and wait for
        # a newly recognised state transition.
        self.pending = None
        self.gate.reset()
        self._commit_input(decision, time.perf_counter())
        self.status = "ADB 輸入結果未確認，等待畫面確認：" + str(exc)
        return False

    def _commit_input(self, decision, now):
        if decision.action == 'ERROR_CLOSE':
            return
        if decision.ack_retry:
            self.controller.commit(decision.action, now, ack_retry=True)
        else:
            self.controller.commit(decision.action, now)

    def _run(self):
        cfg = dict(DEFAULTS)
        cfg.update(result_wait_s=self.settings["result_wait_s"],
                   result_retry_s=self.settings["result_retry_s"],
                   result_retry_jitter_ms=100 if self.settings["humanize"] else 0,
                   input_latency_ms=self.settings["input_latency_ms"], adaptive_latency=False,
                   continuous_fishing=self.settings["continuous"],
                   max_casts=int(self.settings["max_casts"]),
                   max_session_minutes=self.settings["max_session_minutes"])
        controller = self.controller = Controller(cfg)
        controller.reset(time.perf_counter())
        try:
            detector = PhoneDetector(ROOT / "assets/templates", cfg["template_threshold"])
        except (OSError, ValueError, cv2.error) as exc:
            self._pause("辨識資源無法載入：" + str(exc))
            self.emit({"error": self.status, "fatal": True})
            self.capture.close()
            self.adb.close()
            return
        profiles = DeviceProfileStore()
        profile_serial = self.adb.serial
        profile_crop = self.settings['crop']
        detector.adaptive = self.settings['layout_mode'] == 'auto'
        stored_alignment = profiles.load(profile_serial, self.shape, 'fishing', profile_crop) if detector.adaptive else None
        detector.set_alignment(stored_alignment)
        if stored_alignment is not None:
            self.alignment = stored_alignment
        saved_alignment = stored_alignment
        last_profile_save = 0.
        sequence, last_ui, last_frame = 0, 0., None
        last_ui_sequence = -1
        last_processed = 0.
        observation_hold = ObservationHold()
        reconnect_attempts = 0
        next_reconnect = 0.0
        started = time.perf_counter()
        decision, obs, display = Decision(), None, None
        error_gate = ErrorRecoveryGate()
        try:
            while not self.stop.is_set():
                while not self.commands.empty():
                    name, arg = self.commands.get()
                    if name == 'reconfigure':
                        reset_calibration = arg.pop('_reset_calibration', False)
                        previous = self.settings
                        self.settings = arg
                        cfg.update(result_wait_s=arg['result_wait_s'], result_retry_s=arg['result_retry_s'],
                                   result_retry_jitter_ms=100 if arg['humanize'] else 0,
                                   input_latency_ms=arg['input_latency_ms'],
                                   continuous_fishing=arg['continuous'], max_casts=int(arg['max_casts']),
                                   max_session_minutes=arg['max_session_minutes'])
                        controller.latency.base_ms = float(arg['input_latency_ms'])
                        controller.phase = type(controller.phase)(cfg, controller.latency, controller.speed)
                        controller.motion.clear();self.pending = None;self.gate.reset();self.recovery.reset()
                        controller.candidate='UNKNOWN';controller.candidate_count=0
                        self.hook_point=self.action_point=None
                        self.capture.delay=arg['stream_delay_ms']/1000
                        self.capture.uncertainty=arg['timing_uncertainty_ms']/1000
                        if reset_calibration:
                            profiles.clear(profile_serial, self.shape, 'fishing', previous['crop'])
                            profiles.clear(profile_serial, self.shape, 'fishing', arg['crop'])
                        if reset_calibration or previous['layout_mode'] != arg['layout_mode'] or previous['crop'] != arg['crop']:
                            detector = PhoneDetector(ROOT / "assets/templates", cfg["template_threshold"])
                            detector.adaptive = arg['layout_mode'] == 'auto'
                            profile_crop = arg['crop']
                            stored_alignment = profiles.load(profile_serial, self.shape, 'fishing', profile_crop) if detector.adaptive else None
                            detector.set_alignment(stored_alignment)
                            self.alignment = stored_alignment or (0., 0.)
                            saved_alignment = stored_alignment;last_profile_save = 0.
                        current, _ = self.capture.snapshot()
                        if current is not None:
                            sequence = current.sequence
                        last_frame = obs = display = None
                        error_gate.reset()
                        last_ui_sequence = -1
                        last_processed = 0.
                    else:
                        command_now = time.perf_counter()
                        if name in ('pause', 'end'):
                            observation_hold.end(controller, command_now)
                            error_gate.reset()
                        self._command(name, arg, controller, command_now)
                frame, error = self.capture.snapshot()
                now = time.perf_counter()
                if self.active.is_set() and not self.foreground_ready(now):
                    observation_hold.begin(now)
                failure = self._stream_failure(frame, error, started, now)
                if failure:
                    self.ready.clear()
                    if not failure.retry:
                        self._fatal_stream(failure)
                        break
                    self.pending = None
                    self.gate.reset()
                    self.recovery.reset()
                    if self.active.is_set():
                        observation_hold.begin(now)
                    if now < next_reconnect:
                        self.stop.wait(min(.1, next_reconnect-now))
                        continue
                    reconnect_attempts += 1
                    self.status = f"影像串流中斷，正在重連（第 {reconnect_attempts} 次）"
                    self.emit({"status": self.status, "state": "連線中斷", "reason": failure.message, "diagnostic": failure.diagnostic,
                               "active": self.active.is_set(), "casts": controller.cast_count,
                               "results": controller.result_count, "fps": 0, "capture_ms": 0,
                               "action_ms": self.action_ms, "age_ms": 0, "image": None})
                    self.capture.close()
                    self.capture.thread.join(timeout=4)
                    if self.stop.is_set():
                        break
                    if self.capture.thread.is_alive():
                        self._pause("舊影像串流無法停止，請重新連線")
                        self.emit({"error": self.status, "fatal": True})
                        break
                    self.capture = self._create_capture()
                    self.capture.start()
                    sequence, last_frame, obs, display = 0, None, None, None
                    last_ui_sequence = -1
                    self.capture_times.clear()
                    started = time.perf_counter()
                    next_reconnect = started + min(2 ** min(reconnect_attempts, 4), 10)
                    continue
                if frame and now-frame.received_at < self.settings["max_frame_age"]:
                    reconnect_attempts = 0
                if frame and frame.sequence != sequence and now-last_processed >= self.settings["capture_interval"]:
                    last_processed = now
                    sequence = frame.sequence
                    if tuple(frame.image.shape[:2]) != (self.capture.height, self.capture.width):
                        raise OSError("手機方向或解析度改變；請重新連線並框選")
                    if now-frame.captured_at > self.settings["max_frame_age"]:
                        self.pending = None
                        self.gate.reset()
                        self.recovery.reset()
                        if self.active.is_set():
                            observation_hold.begin(now)
                        if self.active.is_set():
                            self.status = "畫面延遲，等待新畫面恢復"
                        continue
                    last_frame = frame
                    if self.foreground_recovered.is_set():
                        self.foreground_recovered.clear()
                        self.pending = None
                        self.gate.reset()
                        self.recovery.reset()
                        controller.phase = type(controller.phase)(cfg, controller.latency, controller.speed)
                    raw, box = crop_frame(frame.image, self.settings["crop"])
                    obs, display = detector.detect(raw)
                    active_message = "觀察測試中 · 不點擊" if self.observe_only else "自動釣魚中"
                    self._usable_frame(now, "畫面已就緒，可以開始釣魚。", active_message)
                    alignment = getattr(detector, 'alignment', None)
                    if (getattr(detector, 'alignment_ready', False)
                            and isinstance(alignment, tuple) and len(alignment) == 2):
                        self.alignment = alignment
                        count = getattr(detector, '_alignment_count', 0)
                        if (isinstance(count, int) and count >= 6 and now-last_profile_save >= 20
                                and (saved_alignment is None
                                     or max(abs(a-b) for a, b in zip(alignment, saved_alignment)) >= .003)):
                            if profiles.save(profile_serial, self.shape, 'fishing', alignment, profile_crop):
                                saved_alignment = alignment
                            last_profile_save = now
                    self.hook_point = ((obs.scores["hook_x"], obs.scores["hook_y"])
                                       if "hook_x" in obs.scores else None)
                    self.action_point = ((obs.scores["tap_x"], obs.scores["tap_y"])
                                         if "tap_x" in obs.scores else None)
                    now = time.perf_counter()
                    self.capture_times.append(frame.received_at)
                    if obs.state != 'ERROR':
                        error_gate.reset()
                    moving = self.gate.observe(obs, frame.captured_at)
                    self.pending = None
                    if self.active.is_set() and not self.foreground_ready(now):
                        observation_hold.begin(now)
                        self.pending=None;self.gate.reset();self.recovery.reset();decision=Decision(reason='等待遊戲恢復前景')
                    elif self.active.is_set():
                        if obs.state == 'ERROR':
                            observation_hold.begin(now)
                            self.gate.reset()
                            self.recovery.reset()
                            decision = Decision(reason='正在確認遊戲錯誤提示')
                            if error_gate.observe(self.action_point, now) and not self.observe_only:
                                self._send(Decision(action='ERROR_CLOSE'), frame, box)
                                error_gate.dispatched(time.perf_counter())
                        else:
                            if observation_hold.end(controller, now):
                                self.gate.reset();self.recovery.reset();moving=False
                                controller.phase=type(controller.phase)(cfg,controller.latency,controller.speed)
                                self.status = "觀察測試中 · 不點擊" if self.observe_only else "自動釣魚中"
                            decision = controller.step(obs, frame.captured_at, now)
                            decision = self.recovery.resolve(controller, obs, decision, now)
                        if obs.state == "TIMING":
                            phase = controller.phase
                            if moving and not decision.pause and decision.action == "HIT" and phase.clock.anchor_time is not None:
                                # Bootstrap from measured motion, including a leftward start.
                                if phase.clock.direction_at(frame.captured_at) != self.gate.direction:
                                    u = phase._fraction(obs.marker)-phase.clock.left
                                    phase.clock.anchor_phase = u if self.gate.direction > 0 else 2*phase.clock.length-u
                                    phase.clock.anchor_time = frame.captured_at
                                decision = Decision(**phase.plan(now))
                            if not decision.pause and not moving:
                                decision = Decision(reason="等待連續移動樣本；停幀或方向不明時不點擊")
                            elif not decision.pause and phase.target is not None:
                                width = phase.target[1]-phase.target[0]
                                velocity = abs(decision.velocity)
                                # Bound capture-time uncertainty + configured delivery jitter.
                                uncertainty = frame.uncertainty if frame.uncertainty is not None else frame.duration/2 + .012
                                if velocity and width/(2*velocity) <= uncertainty:
                                    decision = Decision(reason="黃條窗口小於截圖時序誤差，本趟略過")
                        if decision.pause:
                            self._pause(decision.reason)
                        elif decision.action and not self.observe_only:
                            if decision.action == "HIT":
                                self.pending = decision, frame, box
                            else:
                                self._send(decision, frame, box)
                    else:
                        decision = Decision(reason=self.status)
                if self.pending and self.active.is_set():
                    d, source, box = self.pending
                    if now-source.captured_at > self.settings["max_frame_age"] or not self.gate.fresh(now):
                        self.pending = None
                    elif now >= d.send_at:
                        self._send(d, source, box)
                if last_frame and now-last_frame.received_at > self.settings["max_frame_age"]:
                    self.pending = None
                    self.gate.reset()
                    # A processed frame can age out between deliberately sparse
                    # scans even while new capture frames are arriving. Discard
                    # timed input immediately, but keep recovery evidence until
                    # the capture itself has actually stopped producing frames.
                    if frame is None or now-frame.received_at > self.recovery.ACK_MAX_GAP:
                        if self.active.is_set():
                            observation_hold.begin(now)
                            self.status = "畫面延遲，等待新畫面恢復"
                        self.recovery.reset()
                now = time.perf_counter()
                if (last_frame is not None and obs is not None and display is not None and sequence != last_ui_sequence
                        and now-last_ui >= (.010 if self.preview.is_set() else .15)):
                    times = self.capture_times
                    fps = (len(times)-1)/(times[-1]-times[0]) if len(times)>1 and times[-1]>times[0] else 0
                    self.emit({"status": self.status, "state": LABELS.get(obs.state, '遊戲錯誤提示'), "reason": ("前景確認中，暫停輸入：" + self.foreground_note
                                          if self.active.is_set() and not self.foreground_ready(now) else decision.reason),
                               "active": self.active.is_set(), "casts": controller.cast_count,
                               "results": controller.result_count, "fps": fps, "capture_fps": self.capture.fps(now),
                               "capture_ms": last_frame.duration*1000, "action_ms": self.action_ms,
                               "age_ms": (now-last_frame.captured_at)*1000,
                               "image": preview_frame(self.preview.is_set(), self.full_preview.is_set(), last_frame, display, obs, decision.predicted_x)})
                    last_ui = now
                    last_ui_sequence = sequence
                if self.pending and self.active.is_set():
                    remaining = self.pending[0].send_at-time.perf_counter()
                    if 0 < remaining < .020:
                        time.sleep(min(.001, remaining))
                        continue
                # Wake on producer publication, not a coarse Windows polling timer.
                self.capture.available.wait(.025)
        except (OSError, ValueError, cv2.error) as exc:
            self._pause(str(exc))
            self.emit({"error": str(exc), "fatal": True})
        except Exception as exc:
            self._pause(str(exc))
            self.emit({"error": "工作階段停止：" + str(exc), "fatal": True})
        finally:
            self.active.clear()
            self.ready.clear()
            self.capture.close()
            self.adb.close()
            self.capture.thread.join(timeout=4)
