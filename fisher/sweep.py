# SPDX-License-Identifier: GPL-3.0-only
"""Visual observations and conservative multi-hit controller for the sweep game."""
from dataclasses import dataclass
from collections import deque
import cv2
import numpy as np

@dataclass(frozen=True)
class Observation:
    state: str
    marker: float | None = None
    target: float | None = None
    target_width: float | None = None


def _component(mask, minimum, maximum):
    n, _, stats, centers = cv2.connectedComponentsWithStats(mask)
    items = [(stats[i, 4], centers[i], stats[i]) for i in range(1, n)
             if minimum <= stats[i, 4] <= maximum]
    return max(items, key=lambda item: item[0]) if items else None


def normalized_frame(image):
    """Normalize by width and align the game's bottom-anchored controls."""
    h, w = image.shape[:2]
    if h <= w or w < 180:
        return None
    height = round(h * 360 / w)
    scaled = cv2.resize(image, (360, height), interpolation=cv2.INTER_AREA)
    if height >= 801:
        return scaled[-801:]
    return cv2.copyMakeBorder(scaled, 801-height, 0, 0, 0, cv2.BORDER_CONSTANT)


def bottom_y(shape, reference_y):
    """Map a 360x801 reference coordinate to the source image."""
    h, w = shape[:2]
    return h - (801-reference_y)*w/360


def detect(image):
    """Recognize controls in a full, uncropped portrait game frame."""
    h,w = image.shape[:2]
    if h <= w or w < 180:
        return Observation('unknown')
    # Only the bottom 296 reference pixels contain the controls we inspect.
    # Avoid resizing the whole screenshot on every recognition frame.
    section_height = max(1, round(296*w/360))
    section = image[max(0,h-section_height):h]
    if section.shape[0] != section_height:
        return Observation('unknown')
    section = cv2.resize(section, (360,296), interpolation=cv2.INTER_AREA)
    return detect_controls(section[:170])


def detect_controls(section):
    if min(section.shape[:2]) < 50:
        return Observation('unknown')
    frame = cv2.resize(section, (360,170), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    pink = cv2.inRange(hsv[15:50, 40:320], (165, 150, 180), (179, 255, 255))
    yellow = cv2.inRange(hsv[0:30, 40:320], (20, 160, 180), (35, 255, 255))
    marker = _component(pink, 80, 500)
    target = _component(yellow, 55, 300)
    green = cv2.countNonZero(cv2.inRange(hsv[95:170, 95:265], (75, 95, 160), (95, 255, 255)))
    if marker and target and green > 2500:
        _, mc, _ = marker
        _, tc, ts = target
        return Observation('timing', (mc[0] + 40) / 360, (tc[0] + 40) / 360, ts[2] / 360)
    # The start screen also has an orange ticket button beside the green button.
    orange = cv2.countNonZero(cv2.inRange(hsv[105:155, 270:325], (15, 130, 150), (35, 255, 255)))
    purple = cv2.countNonZero(cv2.inRange(hsv[105:155, 270:325], (125, 65, 100), (160, 255, 255)))
    if green > 4000 and (orange > 120 or purple > 120):
        return Observation('ready')
    return Observation('unknown')


class SweepController:
    """One round only; never repeats an input on an unconfirmed screen."""
    def __init__(self, latency=.10, max_sample_gap=.25):
        self.latency = latency
        self.max_sample_gap = max_sample_gap
        self.state = 'ready'
        self.previous = None
        self.motion = deque(maxlen=24)
        self.direction = 0
        self.last_hit_target = None
        self.last_target_width = None
        self.results = []
        self.hit_at = None
        self.missing = 0
        self.missing_since = None
        self.wait_position = None
        self.wait_still_at = None
        self.wait_stopped = False
        self.hit_motion = None
        self.last_measured_latency = None
        self.hits = 0
        self.hit_delay = 0.0

    def _learn_latency(self, stopped_at):
        # Both timestamps come from the same stream.  The last moving frame
        # estimates when this particular input became visible, including capture lag.
        if self.hit_at is None or stopped_at is None:
            return
        measured = stopped_at-self.hit_at
        if .01 <= measured <= .8 and abs(measured-self.latency)<.2:
            # A frame interval and input scheduling obscure the precise stop time.
            # The observed miss adds a signed timing correction in the direction
            # the marker was moving at the time of the input.
            corrected = measured
            if self.hit_motion and self.wait_position is not None and self.last_hit_target is not None:
                _, velocity = self.hit_motion
                error = self.last_hit_target-self.wait_position
                if abs(velocity) >= .1 and abs(error) <= .1:
                    adjustment = max(-.08, min(.08, error/velocity))
                    corrected = max(.01, min(.8, self.latency-adjustment))
            self.last_measured_latency = corrected
            self.latency = corrected
        self.hit_motion = None

    def cancel_pending_hit(self):
        """Discard an unsent hit after scheduling missed its deadline."""
        if self.state != 'waiting' or self.hit_at is None:
            return
        self.hits = max(0, self.hits-1)
        self.state = 'timing'
        self.previous = None
        self.motion.clear()
        self.direction = 0
        self.hit_at = None
        self.hit_motion = None
        self.last_hit_target = None
        self.last_target_width = None

    def step(self, observation, now):
        o = observation
        if self.state == 'ready':
            if o.state == 'ready':
                self.state = 'starting'
                return 'start'
            return None
        if self.state == 'starting':
            if o.state == 'timing': self.state = 'timing'
            return None
        if self.state == 'waiting':
            # A new target or a confirmed disappearance arms the next hit.
            if o.state != 'timing':
                if self.missing_since is None:self.missing_since=now
                elapsed=now-self.missing_since
                if elapsed >= (.2 if self.hits >= 2 else 1.5):
                    self.state = 'transition'
                return None
            self.missing_since = None
            self.missing = 0
            if self.wait_position is None:
                self.wait_position, self.wait_still_at = o.marker, now
            delta = abs(o.marker-self.wait_position)
            if delta > .004:
                if self.hits < 2 and self.wait_stopped and now-self.hit_at > .15:
                    self.state = 'timing'
                    self.previous = None
                    self.motion.clear()
                    self.direction = 0
                    self.wait_stopped = False
                self.wait_position, self.wait_still_at = o.marker, now
            elif self.wait_still_at is not None and now-self.wait_still_at >= .12:
                if not self.wait_stopped and now-self.hit_at >= .15:
                    if self.last_hit_target is not None and self.last_target_width:
                        error = abs(self.wait_position-self.last_hit_target)
                        self.results.append('黃色' if error <= self.last_target_width/2 else '未命中黃色')
                    self._learn_latency(self.wait_still_at)
                self.wait_stopped = True
            if self.hits >= 2:
                self.state = 'waiting'
                return None
            return None
        if self.state == 'transition':
            if o.state == 'timing' and self.hits < 2:
                self.state = 'timing'
                self.previous = None
                self.motion.clear()
                self.direction = 0
            return None
        if self.state != 'timing' or o.state != 'timing':
            self.previous = None
            self.motion.clear()
            self.direction = 0
            return None
        old = self.previous
        self.previous = (now, o.marker, o.target)
        if old and (now <= old[0] or now-old[0] > self.max_sample_gap or abs(o.target-old[2]) > .015):
            self.motion.clear(); self.direction = 0
        if not self.motion:
            self.motion.append((now, o.marker))
            return None
        difference = o.marker-self.motion[-1][1]
        if abs(difference) < .003:
            return None
        direction = 1 if difference > 0 else -1
        if self.direction and direction != self.direction:
            self.motion.clear()
        self.direction = direction
        self.motion.append((now, o.marker))
        while len(self.motion)>4 and now-self.motion[0][0]>.16:
            self.motion.popleft()
        if len(self.motion)<4 or now-self.motion[0][0]<.045:
            return None
        # Each pass uses a fixed game velocity.  Median pairwise slopes reduce
        # the effect of irregular capture/presentation times on that estimate.
        samples=list(self.motion)
        slopes=[(p2-p1)/(t2-t1) for i,(t1,p1) in enumerate(samples)
                for t2,p2 in samples[i+1:] if t2-t1 >= .035]
        if not slopes:return None
        velocity=float(np.median(slopes))
        if not .03 <= abs(velocity) <= 2 or velocity*direction<=0:
            return None
        # Only target the current pass. If the marker must reverse first, the
        # target will be behind the projected position and we wait for the turn.
        projected=o.marker+velocity*self.latency
        until_center = (o.target-projected)/velocity
        # Schedule near the centre instead of firing at the yellow zone's edge.
        if 0 <= until_center <= .012:
            self.hit_delay = until_center
            self.state = 'waiting'
            self.hits += 1
            self.last_hit_target, self.hit_at = o.target, now+self.hit_delay
            self.last_target_width = o.target_width
            self.hit_motion = (o.marker, velocity)
            self.wait_position, self.wait_still_at, self.wait_stopped = None, None, False
            self.motion.clear(); self.direction = 0
            return 'hit'
        return None
