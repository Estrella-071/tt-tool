# SPDX-License-Identifier: GPL-3.0-only
"""ADB Ruins Adventure runner; one verified action at a time."""
from collections import deque
import time
import cv2
from .adb import StreamCapture, crop_frame
from .phone_runtime import PhoneRunner
from .ruins import RuinsController, RuinsDetector
from .ruins_diagnostics import BossDiagnostics
from .ruins_geometry import RuinsGeometry
from .device_profiles import DeviceProfileStore


class RuinsRunner(PhoneRunner):
    def _detector_for(self, settings, reset_calibration=False):
        """Build the selected layout without touching auto profiles in manual mode."""
        adaptive = settings.get('layout_mode', 'auto') == 'auto'
        profiles = DeviceProfileStore() if adaptive else None
        if profiles is not None and reset_calibration:
            profiles.clear(self.adb.serial, self.shape, 'ruins', crop=settings['crop'])
        saved_offset = (profiles.load(self.adb.serial, self.shape, 'ruins', crop=settings['crop'])
                        if profiles is not None and not reset_calibration else None)
        return RuinsDetector(offset=saved_offset, adaptive=adaptive), profiles, saved_offset

    def _apply_reconfigure(self, controller, detector, profiles, settings, reset_calibration=False):
        """Called on the control thread after receiving a reconfigure command."""
        old = self.settings
        rebuild = (reset_calibration or old.get('layout_mode', 'auto') != settings.get('layout_mode', 'auto')
                   or old['crop'] != settings['crop'])
        saved_offset = None
        if rebuild:
            detector, profiles, saved_offset = self._detector_for(settings, reset_calibration)
        self.settings = settings
        controller.reconfigure(settings)
        self.capture.delay = settings.get('stream_delay_ms', 60)/1000
        self.capture.uncertainty = settings.get('timing_uncertainty_ms', 12)/1000
        return detector, profiles, saved_offset, rebuild

    def _run(self):
        controller = self.controller = RuinsController(self.settings, self.rng)
        diagnostics = BossDiagnostics()
        try:
            crop = self.settings['crop']
            detector, profiles, saved_offset = self._detector_for(self.settings)
        except (OSError, ValueError, cv2.error) as exc:
            self._pause('遺跡辨識資源無法載入：' + str(exc))
            self.emit({'error': self.status, 'fatal': True})
            self.capture.close(); self.adb.close()
            return
        sequence = 0
        last_ui_sequence = -1
        last_frame = None
        last_scan = last_ui = 0.
        started = time.perf_counter()
        retry_at = 0.
        attempts = 0
        times = deque(maxlen=30)
        last_saved_offset = saved_offset or (0., 0.)
        last_profile_write = started
        obs = None
        try:
            while not self.stop.is_set():
                while not self.commands.empty():
                    name, arg = self.commands.get()
                    now = time.perf_counter()
                    if name == 'pause':
                        self._pause(arg, now)
                        controller.clear_observation()
                    elif name == 'end':
                        self._pause(arg, now)
                        self.session_started.clear(); self.paused_at = None
                        controller.clear_observation()
                    elif name == 'start' and not self.active.is_set():
                        self.observe_only = arg
                        if not self.session_started.is_set():
                            controller.reset(); self.session_started.set()
                        controller.clear_observation()
                        self.paused_at = None; self.active.set()
                        self.status = '自動探險中'
                    elif name == 'reconfigure':
                        reset_calibration = arg.pop('_reset_calibration', False)
                        detector, profiles, saved_offset, rebuilt = self._apply_reconfigure(
                            controller, detector, profiles, arg, reset_calibration)
                        crop = self.settings['crop']
                        if rebuilt:
                            last_saved_offset = saved_offset or (0., 0.)
                            last_profile_write = now
                        # The first observation after changing configuration must
                        # come from a new frame, never a pending old-layout frame.
                        current, _ = self.capture.snapshot()
                        if current is not None:
                            sequence = current.sequence
                        obs = last_frame = None
                        last_ui_sequence = -1
                frame, error = self.capture.snapshot()
                now = time.perf_counter()
                failed = error or (frame is None and now-started > 6) or (frame is not None and now-frame.received_at > 3)
                if failed:
                    if now < retry_at:
                        self.stop.wait(min(.1, retry_at-now)); continue
                    attempts += 1
                    self.status = f'影像串流中斷，正在重連（第 {attempts} 次）'
                    self.emit({'status': self.status, 'state': '連線中斷', 'reason': '等待手機重新連線',
                               'casts': controller.started, 'results': controller.completed,
                               'active': self.active.is_set(), 'fps': 0., 'capture_fps': 0.,
                               'age_ms': 0., 'image': None})
                    self.capture.close(); self.capture.thread.join(timeout=4)
                    if self.stop.is_set(): break
                    if self.capture.thread.is_alive():
                        self._pause('舊影像串流無法停止，請重新連線')
                        self.emit({'error': self.status, 'fatal': True}); break
                    self.capture = StreamCapture(self.adb, self.shape,
                        self.settings.get('stream_delay_ms', 60)/1000,
                        self.settings.get('timing_uncertainty_ms', 12)/1000)
                    self.capture.start()
                    sequence = 0; last_frame = obs = None
                    controller.clear_observation()
                    started = time.perf_counter()
                    retry_at = started + min(2 ** min(attempts, 4), 10)
                    continue
                if frame and now-frame.received_at < self.settings['max_frame_age']:
                    attempts = 0
                if frame and frame.sequence != sequence:
                    sequence = frame.sequence
                    if tuple(frame.image.shape[:2]) != (self.capture.height, self.capture.width):
                        raise OSError('手機方向或解析度改變，請重新連線')
                    if now-frame.captured_at > self.settings['max_frame_age']:
                        controller.clear_observation()
                        continue
                    last_frame = frame
                    last_scan = now
                    raw, box = crop_frame(frame.image, self.settings['crop'])
                    obs = detector.detect(raw)
                    crop_offset = (detector.geometry.offset[0]*detector.viewport[1],detector.geometry.offset[1])
                    if (profiles is not None and detector.geometry.ready and now-last_profile_write >= 15
                            and max(abs(a-b) for a,b in zip(crop_offset,last_saved_offset)) >= .001):
                        if profiles.save(self.adb.serial, self.shape, 'ruins', crop_offset, crop=crop):
                            last_saved_offset = crop_offset
                        last_profile_write = now
                    times.append(frame.received_at)
                    now = time.perf_counter()
                    if self.foreground_recovered.is_set():
                        self.foreground_recovered.clear()
                        controller.clear_observation()
                    if self.active.is_set() and self.foreground_ready(now):
                        action = controller.observe(obs, now)
                        input_result = 'observe_only' if action and self.observe_only else None
                        if action and not self.observe_only:
                            input_result = self._ruins_tap(controller, action, frame, box,
                                                           None if controller.fallback_fight else obs.chance,
                                                           detector.geometry.offset, detector.viewport, obs.target)
                        diagnostics.observe(obs, controller, action, now, input_result)
                    else:
                        controller.clear_observation()
                now = time.perf_counter()
                if (last_frame is not None and obs is not None
                        and sequence != last_ui_sequence
                        and now-last_ui >= (.006 if self.preview.is_set() else .15)):
                    reason = ''
                    if obs.state == 'BOSS':
                        if controller.fallback_fight and not self.observe_only:
                            reason = '未能確認勝率，正在戰鬥'
                        elif obs.chance is None or not controller.boss_confirmed:
                            reason = '勝率尚未確認，稍後自動戰鬥'
                        elif controller.treasure_uncertain:
                            reason = '寶藏類型尚未確認，稍後自動戰鬥'
                        elif controller.odds_conflict:
                            reason = '勝率讀值互相矛盾，稍後自動戰鬥'
                        else:
                            threshold = controller.red_threshold if controller.valuable or obs.red else controller.normal_threshold
                            choice = '撤離' if obs.chance < threshold else '戰鬥'
                            bonus = f' + {obs.bonus}%' if obs.bonus else ''
                            reward = '紅色寶藏 · ' if controller.valuable or obs.red else ''
                            reason = f'{reward}勝率 {obs.base}%{bonus} = {obs.chance}% · {choice}（門檻 {threshold}%）'
                    elif self.active.is_set() and not self.foreground_ready(now):
                        reason = '等待遊戲恢復前景'
                    elif controller.last_boss is not None:
                        chance, choice = controller.last_boss
                        value = f'{chance}%' if chance is not None else '勝率未辨明'
                        reason = f'最近首領 {value} · {choice}'
                    fps = (len(times)-1)/(times[-1]-times[0]) if len(times)>1 and times[-1]>times[0] else 0.
                    self.emit({'status': self.status, 'state': controller.LABELS[obs.state], 'reason': reason,
                               'casts': controller.started, 'results': controller.completed,
                               'active': self.active.is_set(), 'fps': fps,
                               'capture_fps': self.capture.fps(now), 'age_ms': (now-last_frame.captured_at)*1000,
                               'image': last_frame.image if self.preview.is_set() else None})
                    last_ui = now; last_ui_sequence = sequence
                self.capture.available.wait(.025)
        except (OSError, ValueError, cv2.error) as exc:
            self._pause(str(exc)); self.emit({'error': str(exc), 'fatal': True})
        except Exception as exc:
            self._pause(str(exc)); self.emit({'error': '探險工作階段停止：' + str(exc), 'fatal': True})
        finally:
            self.active.clear(); self.capture.close(); self.adb.close()
            self.capture.thread.join(timeout=4)

    def _ruins_tap(self, controller, action, frame, box, chance=None, offset=None, viewport=None, target=None):
        now = time.perf_counter()
        if (not self.active.is_set() or self.stop.is_set() or self.observe_only
                or not self.commands.empty()
                or not self.foreground_ready(now)
                or now-frame.captured_at > self.settings['max_frame_age']):
            return 'not_sent'
        x, y, w, h = box
        if action in ('ERROR', 'CHEST'):
            if target is None:return 'not_sent'
            point = target
        else:
            point = self.settings.get('ruins_points', {}).get(action, controller.POINTS[action])
        fx, fy = point
        if action not in ('ERROR', 'CHEST') and self.settings.get('layout_mode', 'auto') == 'auto':
            dx, dy = RuinsGeometry.bounded(offset) or (0., 0.)
            left, width = viewport or (0., 1.)
            default = controller.POINTS[action]
            is_default = all(abs(a-b)<1e-6 for a,b in zip(point,default))
            fx = left + width*(fx+dx) if is_default else fx + width*dx
            fy += dy
        fx, fy = min(.99, max(.01, fx)), min(.99, max(.01, fy))
        px = (x + fx*w)*self.shape[1]/frame.image.shape[1]
        py = (y + fy*h)*self.shape[0]/frame.image.shape[0]
        if self.settings['humanize']:
            px += self.rng.uniform(-.004, .004)*w*self.shape[1]/frame.image.shape[1]
            py += self.rng.uniform(-.002, .002)*h*self.shape[0]/frame.image.shape[0]
        if not self.commands.empty():
            return 'not_sent'
        try:
            if self.settings['humanize']:
                self.adb.tap(px, py, hold_ms=self.rng.randint(45,90))
            else:
                self.adb.tap(px, py)
        except OSError as exc:
            controller.commit(action, time.perf_counter(), uncertain=True)
            self.status = 'ADB 輸入結果未確認，持續確認畫面：' + str(exc)
            return 'uncertain'
        done = time.perf_counter()
        self.action_ms = (done-now)*1000
        controller.commit(action, done)
        if action in ('FIGHT','RETREAT'):
            controller.last_boss = (chance, '戰鬥' if action == 'FIGHT' else '撤離')
        self.status = '自動探險中'
        return 'sent'
