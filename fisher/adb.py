# SPDX-License-Identifier: GPL-3.0-only
"""Bounded ADB transport. Never chooses a device or retries an input implicitly."""
from dataclasses import dataclass
from collections import deque
from copy import deepcopy
from pathlib import Path
import math
import queue
import re
import shutil
import subprocess
import threading
import time
import cv2
import numpy as np


class AdbError(OSError):
    pass


PHONE_DEFAULTS = dict(
    tap_x=.5, tap_y=.855, crop=[0, 0, 1, 1], input_latency_ms=80.,
    max_frame_age=.6, capture_interval=.01, continuous=True,
    stream_delay_ms=60., timing_uncertainty_ms=12., max_casts=20,
    max_session_minutes=15, result_wait_s=1.0, result_retry_s=.35, humanize=True,
)


LAYOUT_PROFILE_KEYS = (
    'tap_x', 'tap_y', 'crop', 'input_latency_ms', 'max_frame_age',
    'capture_interval', 'continuous', 'stream_delay_ms', 'timing_uncertainty_ms',
    'max_casts', 'max_session_minutes', 'result_wait_s', 'result_retry_s', 'humanize',
    'ruins_normal_threshold', 'ruins_red_threshold', 'ruins_tap_interval', 'ruins_tap_max',
    'ruins_points',
)


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    detail: str = ""


@dataclass(frozen=True)
class Frame:
    image: np.ndarray
    captured_at: float
    received_at: float
    duration: float
    sequence: int = 0
    uncertainty: float | None = None


class Adb:
    def __init__(self, executable="adb", serial=None):
        resolved = shutil.which(executable)
        if not resolved:
            raise AdbError("找不到 ADB；請選擇 Android platform-tools 的 adb.exe")
        self.executable, self.serial = str(Path(resolved).resolve()), serial
        self._lock = threading.Lock()
        self._processes = set()
        self.closed = threading.Event()

    def call(self, args, timeout=4, selected=True):
        if self.closed.is_set():
            raise AdbError("ADB 工作階段已關閉")
        cmd = [self.executable]
        if selected:
            if not self.serial:
                raise AdbError("請明確選擇一台手機")
            cmd += ["-s", self.serial]
        cmd += list(args)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with self._lock:
            if self.closed.is_set():
                raise AdbError("ADB 工作階段已關閉")
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 creationflags=flags)
            self._processes.add(p)
        try:
            out, err = p.communicate(timeout=timeout)
            if p.returncode:
                raise AdbError(err.decode("utf-8", "replace").strip() or "ADB 指令失敗")
            return out
        except subprocess.TimeoutExpired as exc:
            p.kill()
            p.communicate()
            raise AdbError("ADB 回應逾時；請檢查 USB 連線與手機授權") from exc
        finally:
            with self._lock:
                self._processes.discard(p)

    def devices(self):
        text = self.call(["devices", "-l"], selected=False).decode("utf-8", "replace")
        found = []
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ("device", "offline", "unauthorized", "recovery", "sideload"):
                found.append(Device(parts[0], parts[1], " ".join(parts[2:])))
        return found

    def capture(self):
        start = time.perf_counter()
        data = self.call(["exec-out", "screencap", "-p"], timeout=3)
        end = time.perf_counter()
        if len(data) > 32 * 1024 * 1024 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise AdbError("手機未傳回有效 PNG 截圖")
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or min(image.shape[:2]) < 100:
            raise AdbError("手機截圖無法解碼")
        # Bounds, not a claim that the precise device capture instant is known.
        return Frame(image, (start + end) / 2, end, end - start)

    def tap(self, x, y, hold_ms=None):
        if hold_ms is None:
            args = ["shell", "input", "tap", str(int(x)), str(int(y))]
        else:
            # Same start/end point creates a short press without a drag.
            if not 20 <= hold_ms <= 100:
                raise ValueError("按壓時間超出範圍")
            args = ["shell", "input", "swipe", str(int(x)), str(int(y)),
                    str(int(x)), str(int(y)), str(int(hold_ms))]
        self.call(args, timeout=2)

    def foreground(self):
        text = self.call(["shell", "dumpsys", "window", "displays"], timeout=3).decode("utf-8", "replace")
        for line in text.splitlines():
            if "mCurrentFocus=" in line:
                match = re.search(r"\s([A-Za-z0-9_.]+)/[^\s}]+", line)
                if match:
                    rotation = re.search(r"^\s*mRotation=(\d+)\s", text, re.M)
                    if rotation and rotation.group(1) != "0":
                        raise AdbError("手機方向已改變；請轉回直向後重新連線")
                    return match.group(1)
        raise AdbError("無法確認手機前景 App；請解鎖並開啟遊戲")

    def close(self):
        self.closed.set()
        with self._lock:
            for p in tuple(self._processes):
                if p.poll() is None:
                    p.kill()


class LatestCapture:
    """One producer and one replaceable slot; no accumulated stale screenshots."""
    def __init__(self, adb, interval=.1):
        self.adb, self.interval = adb, interval
        self.stop = threading.Event()
        self._lock = threading.Lock()
        self.available = threading.Event()
        self.latest = None
        self.error = None
        self.thread = threading.Thread(target=self._run, name="adb-capture", daemon=True)

    def start(self):
        self.thread.start()

    def snapshot(self):
        with self._lock:
            self.available.clear()
            return self.latest, self.error

    def _run(self):
        sequence = 0
        while not self.stop.is_set():
            started = time.perf_counter()
            try:
                frame = self.adb.capture()
                sequence += 1
                frame = Frame(frame.image, frame.captured_at, frame.received_at, frame.duration, sequence, frame.uncertainty)
                with self._lock:
                    self.latest, self.error = frame, None
                    self.available.set()
            except (OSError, ValueError, cv2.error) as exc:
                with self._lock:
                    self.error = str(exc)
                    self.available.set()
                # Fail closed. A new connection must be explicitly requested.
                break
            self.stop.wait(max(0, self.interval - (time.perf_counter() - started)))


def validate_phone_settings(data, _nested=False):
    cfg = dict(data)
    profiles = cfg.pop('layout_profiles', None)
    cfg.setdefault('layout_mode', 'auto')
    if cfg['layout_mode'] not in ('auto', 'manual'):
        raise ValueError('畫面設定模式無效')
    cfg.setdefault("result_wait_s", 1.0)
    cfg.setdefault("humanize", True)
    cfg.setdefault("result_retry_s", .35)
    cfg.setdefault("ruins_normal_threshold", 45)
    cfg.setdefault("ruins_red_threshold", 30)
    cfg.setdefault("ruins_tap_interval", .55)
    cfg.setdefault("ruins_tap_max", 1)
    # Earlier builds allowed bursts; migrate both stored profiles to one tap.
    if (isinstance(cfg['ruins_tap_max'], (int, float)) and not isinstance(cfg['ruins_tap_max'], bool)
            and math.isfinite(cfg['ruins_tap_max']) and 1 < cfg['ruins_tap_max'] <= 6
            and int(cfg['ruins_tap_max']) == cfg['ruins_tap_max']):
        cfg['ruins_tap_max'] = 1
    # Migrate older, more aggressive retry intervals to the new human-paced default.
    interval = cfg['ruins_tap_interval']
    if (isinstance(interval, (int, float)) and not isinstance(interval, bool)
            and math.isfinite(interval) and .12 <= interval < .45):
        cfg['ruins_tap_interval'] = .55
    for key, lo, hi in (("tap_x", 0, 1), ("tap_y", 0, 1),
                        ("max_frame_age", .15, 1.5), ("input_latency_ms", 0, 500),
                        ("stream_delay_ms", 0, 500), ("timing_uncertainty_ms", 0, 150),
                        ("result_wait_s", .05, 10), ("result_retry_s", .15, 5),
                        ("capture_interval", .005, 1), ("max_casts", 1, 10000),
                        ("max_session_minutes", 1, 1440),
                        ("ruins_normal_threshold", 0, 100), ("ruins_red_threshold", 0, 100),
                        ("ruins_tap_interval", .45, 2), ("ruins_tap_max", 1, 1)):
        value = cfg.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f"{key} 應介於 {lo} 與 {hi}")
    if not isinstance(cfg.get("humanize"), bool):
        raise ValueError("humanize 必須為布林值")
    if not isinstance(cfg.get("continuous"), bool):
        raise ValueError("continuous 必須為布林值")
    if int(cfg["max_casts"]) != cfg["max_casts"]:
        raise ValueError("下鉤上限必須為整數")
    for key in ("ruins_normal_threshold", "ruins_red_threshold", "ruins_tap_max"):
        if int(cfg[key]) != cfg[key]:
            raise ValueError(f"{key} 必須為整數")
        cfg[key] = int(cfg[key])
    from .ruins import RuinsController
    points = cfg.get("ruins_points", {})
    if not isinstance(points, dict) or any(key not in RuinsController.POINTS for key in points):
        raise ValueError("遺跡按鈕位置無效")
    result = {}
    for key, default in RuinsController.POINTS.items():
        point = points.get(key, default)
        if (not isinstance(point, (tuple, list)) or len(point) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) or not 0 <= v <= 1 for v in point)):
            raise ValueError(f"遺跡按鈕 {key} 位置無效")
        result[key] = list(point)
    cfg["ruins_points"] = result
    crop = cfg.get("crop")
    if not isinstance(crop, (list, tuple)) or len(crop) != 4 or any(
            isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in crop):
        raise ValueError("請設定有效的完整遊戲範圍")
    x, y, w, h = crop
    if min(x, y) < 0 or min(w, h) <= 0 or x + w > 1.000001 or y + h > 1.000001:
        raise ValueError("遊戲範圍超出手機畫面")
    if not _nested:
        if profiles is not None and not isinstance(profiles, dict):
            raise ValueError('畫面設定內容無效')
        base = {key: deepcopy(cfg[key]) for key in LAYOUT_PROFILE_KEYS}
        checked = {}
        for mode in ('auto', 'manual'):
            values = profiles.get(mode, {}) if profiles is not None else {}
            if not isinstance(values, dict) or any(key not in LAYOUT_PROFILE_KEYS for key in values):
                raise ValueError('畫面設定內容無效')
            candidate = deepcopy(base);candidate.update(deepcopy(values));candidate['layout_mode'] = mode
            validated = validate_phone_settings(candidate, _nested=True)
            checked[mode] = {key: deepcopy(validated[key]) for key in LAYOUT_PROFILE_KEYS}
        # The active top-level values are the authoritative current edit.
        checked[cfg['layout_mode']] = deepcopy(base)
        cfg['layout_profiles'] = checked
    return cfg


def crop_frame(image, crop):
    h, w = image.shape[:2]
    x, y, cw, ch = crop
    left, top = round(x*w), round(y*h)
    right, bottom = round((x+cw)*w), round((y+ch)*h)
    result = image[top:bottom, left:right]
    if min(result.shape[:2]) < 100:
        raise ValueError("遊戲選區太小；請框選完整遊戲")
    return result, (left, top, right-left, bottom-top)


class MotionGate:
    """Require fresh, advancing marker observations before allowing prediction."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.last = None
        self.direction = 0
        self.confirmed = 0
        self.last_move = None

    def observe(self, obs, at):
        if obs.state != "TIMING" or obs.marker is None:
            self.reset()
            return False
        if self.last is not None:
            pt, px = self.last
            dt, dx = at-pt, obs.marker-px
            if dt <= 0:
                return False
            if dt > .65 or abs(dx) > 220*dt + 12:
                self.confirmed = 0
            elif abs(dx) >= 1:
                direction = 1 if dx > 0 else -1
                self.confirmed = self.confirmed + 1 if direction == self.direction else 1
                self.direction = direction
                self.last_move = at
            elif self.last_move is None or at-self.last_move > .22:
                self.confirmed = 0
        self.last = at, obs.marker
        return self.confirmed >= 2 and self.last_move is not None and at-self.last_move <= .22

    def fresh(self, now):
        return self.confirmed >= 2 and self.last_move is not None and now-self.last_move <= .35

class StreamFailure(str):
    """Keep snapshot errors string-compatible while exposing recovery details."""

    def __new__(cls, message, diagnostic="", retry=True):
        value = super().__new__(cls, f"{message}: {diagnostic}" if diagnostic else message)
        value.message = message
        value.diagnostic = diagnostic
        value.retry = retry
        return value


class _ProcessDiagnostics:
    def __init__(self, pipe, name):
        self.name = name
        self.chunks = deque(maxlen=4)
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._read, args=(pipe,),
                                       name=name + "-stderr", daemon=True)
        self.thread.start()

    def _read(self, pipe):
        try:
            with pipe:
                while chunk := pipe.read1(1024):
                    with self.lock:
                        self.chunks.append(chunk)
        except OSError:
            pass

    def text(self):
        with self.lock:
            data = b"".join(self.chunks)
        return " ".join(data.decode("utf-8", "replace").split())


class StreamCapture(LatestCapture):
    """Continuous AVC stream, with one frame slot and bounded process diagnostics."""

    def __init__(self, adb, physical_shape, stream_delay=.06, uncertainty=.012, *, ffmpeg="ffmpeg"):
        super().__init__(adb)
        self.width = 360
        self.height = int(round(physical_shape[0] / physical_shape[1] * self.width / 2) * 2)
        self.delay = stream_delay
        self.uncertainty = uncertainty
        self.ffmpeg = ffmpeg
        self.processes = []
        self._process_lock = threading.Lock()
        self._diagnostics = []
        self.frame_times = deque(maxlen=120)

    def fps(self, now=None):
        now = time.perf_counter() if now is None else now
        with self._lock:
            times = tuple(self.frame_times)
        if len(times) < 2 or now - times[-1] > .5 or times[-1] <= times[0]:
            return 0.0
        return (len(times)-1)/(times[-1]-times[0])

    def close(self):
        self.stop.set()
        with self._process_lock:
            for process in self.processes:
                if process.poll() is None:
                    process.kill()

    def _spawn(self, name, command, stdin=subprocess.DEVNULL):
        with self._process_lock:
            if self.stop.is_set():
                return None
            process = subprocess.Popen(command, stdin=stdin, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.processes.append(process)
            self._diagnostics.append(_ProcessDiagnostics(process.stderr, name))
            return process

    def failure(self, message, io_error=""):
        with self._process_lock:
            diagnostics = tuple(self._diagnostics)
        outputs = {item.name: item.text() for item in diagnostics}
        if io_error:
            outputs["I/O"] = io_error
        source = outputs.get("ADB", "").casefold()
        decoder = outputs.get("FFmpeg", "").casefold()
        serial = getattr(self.adb, "serial", None)
        if serial:
            outputs = {name: output.replace(serial, "[device]") for name, output in outputs.items()}
        details = " · ".join(f"{name}: {output[-400:]}" for name, output in outputs.items() if output)
        if any(marker in source for marker in ("outside acceptable range", "unrecognized option",
                                              "unknown option", "invalid output format",
                                              "screenrecord: not found", "screenrecord: inaccessible")):
            return StreamFailure("手機不支援目前的錄影方式，請檢查 Android／ADB 版本", details, retry=False)
        if any(marker in decoder for marker in ("unrecognized option", "unknown decoder",
                                               "decoder not found", "encoder not found",
                                               "unknown input format", "unknown output format",
                                               "requested output format 'rawvideo' is not known")):
            return StreamFailure("FFmpeg 無法解碼手機畫面，請更新 FFmpeg", details, retry=False)
        return StreamFailure(message, details)

    def _read_frames(self, pipe):
        size, sequence = self.width*self.height*3, 0
        started = previous = time.perf_counter()
        while not self.stop.is_set():
            data = pipe.read(size)
            if self.stop.is_set() or len(data) != size:
                break
            received = time.perf_counter()
            # Discard startup buffering; never publish a burst as fresh motion.
            if received-started < .8:
                continue
            sequence += 1
            image = np.frombuffer(data, np.uint8).reshape(self.height, self.width, 3)
            frame = Frame(image, received-self.delay, received, received-previous, sequence, self.uncertainty)
            previous = received
            with self._lock:
                self.latest, self.error = frame, None
                self.frame_times.append(received)
                self.available.set()

    def _run(self):
        if self.stop.is_set():
            return
        ffmpeg = shutil.which(self.ffmpeg)
        if not ffmpeg:
            self._publish_failure(StreamFailure("找不到 FFmpeg，請在連線工具中指定位置", retry=False))
            return
        failure = None
        io_error = ""
        try:
            # Keep exec-out's binary-safe stdout for the encoded video.
            source = self._spawn("ADB", [self.adb.executable, "-s", self.adb.serial, "exec-out",
                "screenrecord", "--output-format=h264", "--size", f"{self.width}x{self.height}",
                "--bit-rate", "1500000", "--time-limit", "0", "-"])
            if source is None:
                return
            decoder = self._spawn("FFmpeg", [ffmpeg, "-loglevel", "error", "-probesize", "32",
                "-analyzeduration", "0", "-flags", "low_delay", "-threads", "1", "-f", "h264",
                "-i", "pipe:0", "-an", "-f", "rawvideo", "-pix_fmt", "bgr24",
                "-fps_mode", "passthrough", "pipe:1"], stdin=source.stdout)
            if decoder is None:
                return
            source.stdout.close()
        except OSError as exc:
            failure = StreamFailure("無法啟動連線工具，請確認執行檔位置", str(exc), retry=False)
        else:
            try:
                self._read_frames(decoder.stdout)
            except (OSError, ValueError) as exc:
                io_error = str(exc)
        finally:
            interrupted = self.stop.is_set()
            self.close()
            for process, diagnostic in zip(self.processes, self._diagnostics):
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                diagnostic.thread.join(timeout=.2)
                if process.stdout is not None:
                    process.stdout.close()
            if not interrupted:
                self._publish_failure(failure or self.failure("影像串流結束，正在等待恢復", io_error))

    def _publish_failure(self, failure):
        with self._lock:
            self.error = failure
            self.available.set()


class ForegroundMonitor:
    """Block on any uncertain sample; pause only on sustained evidence."""
    def __init__(self, expected):
        self.expected = expected
        self.uncertain_since = None
        self.other = None
        self.other_since = None
        self.other_count = 0
        self.last_reason = ""

    def update(self, now, package=None, error=None):
        if error is None and package == self.expected:
            self.uncertain_since = self.other_since = None
            self.other, self.other_count, self.last_reason = None, 0, ""
            return True, None
        if self.uncertain_since is None:
            self.uncertain_since = now
        if error is None and package:
            if package != self.other:
                self.other, self.other_since, self.other_count = package, now, 1
            else:
                self.other_count += 1
            self.last_reason = "前景 App：" + package
            # Voice assistants and system overlays may briefly take focus while
            # the game stays open. Block taps throughout, with a longer grace.
            overlay = package in ("com.google.android.googlequicksearchbox", "com.android.systemui")
            if self.other_count >= 3 and now-self.other_since >= (30.0 if overlay else 1.0):
                return False, "持續確認手機前景為 " + package + "，已暫停"
        else:
            self.other, self.other_since, self.other_count = None, None, 0
            self.last_reason = str(error or "未取得前景 App")
        if error is not None and now-self.uncertain_since >= 3:
            return False, "前景驗證持續失敗，已暫停：" + self.last_reason
        return False, None
