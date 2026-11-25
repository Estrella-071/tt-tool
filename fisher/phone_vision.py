# SPDX-License-Identifier: GPL-3.0-only
"""Preserve control scale on tall phones instead of stretching the whole screen."""
import cv2
import numpy as np
from .vision import Observation
from .vision import Detector
from .templates import W, H
from .ruins_geometry import error_dialog_target


class PhoneDetector(Detector):
    """Recognize the phone UI while learning bounded per-device translation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.adaptive = True
        self.alignment = (0.0, 0.0)
        self.alignment_ready = False
        self._alignment_candidate = None
        self._alignment_count = 0
        self._alignment_frame = 0
        self._last_state = 'UNKNOWN'
        self._error_active = False

    def set_alignment(self, offset):
        if (isinstance(offset, (tuple, list)) and len(offset) == 2
                and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                        and np.isfinite(v) and abs(v) <= .20 for v in offset)):
            self.alignment = tuple(float(v) for v in offset)
            self.alignment_ready = True

    def _idle_alignment(self, image):
        """Locate the known idle control over a bounded portion of the screen."""
        height, width = image.shape[:2]
        scaled_height = max(H, round(height * W / width))
        scaled = cv2.resize(image, (W, scaled_height), interpolation=cv2.INTER_AREA)
        template, (x, y, _, _), _ = self.templates['idle']
        expected_y = scaled_height - H + y
        top = max(0, expected_y - round(.20 * scaled_height))
        bottom = min(scaled_height, expected_y + template.shape[0] + round(.20 * scaled_height))
        if bottom-top < template.shape[0]:
            return None
        matches = cv2.matchTemplate(scaled[top:bottom], template, cv2.TM_CCOEFF_NORMED)
        _, score, _, (found_x, found_y) = cv2.minMaxLoc(matches)
        if score < max(.84, self.threshold):
            return None
        dx = (found_x-x) / W
        dy = (top+found_y-expected_y) / scaled_height
        if abs(dx) > .20 or abs(dy) > .20:
            return None
        return dx, dy

    def _learn_alignment(self, image):
        candidate = self._idle_alignment(image)
        if candidate is None:
            self._alignment_candidate = None
            self._alignment_count = 0
            return
        height, width = image.shape[:2]
        probe = cv2.warpAffine(image, np.float32([[1, 0, -candidate[0]*width],
                                                   [0, 1, -candidate[1]*height]]),
                               (width, height), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT)
        if self._detect_aligned(probe)[0].state != 'IDLE':
            self._alignment_candidate = None
            self._alignment_count = 0
            return
        if (self._alignment_candidate is not None
                and max(abs(a-b) for a, b in zip(candidate, self._alignment_candidate)) < .012):
            self._alignment_count += 1
        else:
            self._alignment_candidate = candidate
            self._alignment_count = 1
        if self._alignment_count >= 3:
            if not self.alignment_ready:
                self.alignment = candidate
            else:
                self.alignment = tuple(a*.75+b*.25 for a, b in zip(self.alignment, candidate))
            self.alignment_ready = True

    def detect(self, image):
        self._alignment_frame += 1
        # Error dialogs persist until dismissed. Sample occasionally during
        # normal play, then check every frame while one is visible so input is
        # never sent using an old cached dialog position.
        if self._error_active or self._alignment_frame % 4 == 0:
            error_target = error_dialog_target(image)
            self._error_active = error_target is not None
            if error_target is not None:
                self._last_state = 'ERROR'
                return Observation('ERROR', .9, scores={
                    'tap_x': error_target[0], 'tap_y': error_target[1]}), cv2.resize(image, (W, H))
        # The bounded local search is intermittent; the normal timing path uses
        # the latest confirmed alignment without searching every captured frame.
        interval = 4 if not self.alignment_ready or self._last_state == 'UNKNOWN' else 30
        if self.adaptive and self._alignment_frame % interval == 1:
            self._learn_alignment(image)
        dx, dy = self.alignment if self.adaptive else (0., 0.)
        aligned = image
        if abs(dx) > .0001 or abs(dy) > .0001:
            height, width = image.shape[:2]
            matrix = np.float32([[1, 0, -dx*width], [0, 1, -dy*height]])
            aligned = cv2.warpAffine(image, matrix, (width, height),
                                     flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        obs, display = self._detect_aligned(aligned)
        self._last_state = obs.state
        if obs.state != 'UNKNOWN':
            # Hook/claim centers are measured in the aligned image; map them back.
            for xkey, ykey in (('hook_x', 'hook_y'), ('tap_x', 'tap_y')):
                if xkey in obs.scores and ykey in obs.scores:
                    obs.scores[xkey] = min(1., max(0., obs.scores[xkey] + dx))
                    obs.scores[ykey] = min(1., max(0., obs.scores[ykey] + dy))
        return obs, display

    def _detect_aligned(self, image):
        h, w = image.shape[:2]
        scaled = cv2.resize(image, (W, max(H, round(h*W/w))), interpolation=cv2.INTER_AREA)
        extra = scaled.shape[0]-H
        # The reel prompt is actionable as soon as its yellow countdown appears.
        # Its localized title and vertical anchor vary; require all three shapes.
        hsv = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)
        purple = cv2.inRange(hsv, (120, 90, 90), (168, 255, 255))
        yellow = cv2.inRange(hsv, (18, 95, 150), (38, 255, 255))
        _, _, ys, _ = cv2.connectedComponentsWithStats(yellow)
        _, _, ps, _ = cv2.connectedComponentsWithStats(purple)
        for x, y, bw, bh, area in ys[1:]:
            if not (40 <= bw <= 180 and 5 <= bh <= 18 and bw/bh >= 4
                    and len(hsv)*.42 < y < len(hsv)*.82 and 60 < x < 200
                    and x+bw < 280 and area > bw*bh*.65):
                continue
            panel = purple[max(0,y-30):y+bh+12, max(0,x-14):min(W,x+bw+45)]
            buttons = [(px,py,pw,ph) for px,py,pw,ph,pa in ps[1:]
                       if 55 <= pw <= 115 and 45 <= ph <= 115 and pa > 900
                       and .3*W < px+pw/2 < .7*W and y+bh+20 < py < y+180]
            if np.mean(panel > 0) > .24 and buttons:
                px,py,pw,ph = max(buttons, key=lambda b:b[2]*b[3])
                return Observation("BITE", .92, scores={
                    "hook_x": float((px+pw/2)/W),
                    "hook_y": float((py+ph/2)/len(hsv)),
                    "progress_width": int(bw)}), scaled[extra:extra+H]
        bottom_obs, bottom_frame = super().detect(scaled[extra:extra+H])
        if bottom_obs.state in ("IDLE", "WAIT", "BITE", "TIMING"):
            return bottom_obs, bottom_frame
        # Localized claim text differs across clients. Confirm a rectangular green
        # button, white glyphs, a dark modal backdrop and a centered gold title.
        mask = cv2.inRange(hsv, (32, 95, 140), (85, 255, 255))
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        dark = np.mean(hsv[int(.2*len(hsv)):int(.7*len(hsv)), :55, 2] < 85)
        gold = cv2.inRange(hsv[:int(.3*len(hsv)), 60:276], (15, 90, 170), (38,255,255))
        for x, y, bw, bh, area in stats[1:]:
            if (dark > .65 and np.count_nonzero(gold) > 180
                    and 90 <= bw <= 230 and 15 <= bh <= 65
                    and y > len(hsv)*.6 and .2*W < x+bw/2 < .8*W
                    and area > bw*bh*.35):
                roi = scaled[y:y+bh, x:x+bw]
                white = self.white_text(roi)
                if np.mean(white > 0) > .035:
                    obs = Observation("RESULT", .85, variant="claim",
                                      scores={"tap_x": float((x+bw/2)/W),
                                              "tap_y": float((y+bh/2)/len(hsv))})
                    return obs, scaled[extra:extra+H]
        candidates = []
        # Record modals move with safe-area/viewport layout. Locate their small
        # weight icon, then let the original multi-signal detector confirm it.
        template = self.templates["weight"][0]
        match = cv2.matchTemplate(scaled, template, cv2.TM_CCOEFF_NORMED)
        _, confidence, _, location = cv2.minMaxLoc(match)
        if confidence < .80:
            gray_match = cv2.matchTemplate(cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY),
                                          cv2.cvtColor(template, cv2.COLOR_BGR2GRAY),
                                          cv2.TM_CCOEFF_NORMED)
            _, gray_confidence, _, gray_location = cv2.minMaxLoc(gray_match)
            if gray_confidence >= .88:
                confidence, location = gray_confidence, gray_location
        if confidence >= max(.80, self.threshold):
            top = max(0, min(extra, location[1]-365))
            obs, frame = super().detect(scaled[top:top+H])
            if obs.state == "RESULT":
                return obs, frame
        # Bottom-anchored controls first. Centered result modals may use a different
        # anchor, so only accept alternate views for confirmed RESULT observations.
        for top in dict.fromkeys((extra, extra//2, 0)):
            obs, frame = (bottom_obs, bottom_frame) if top == extra else super().detect(scaled[top:top+H])
            if top == extra and obs.state != "UNKNOWN":
                return obs, frame
            if obs.state == "RESULT":
                candidates.append((obs, frame))
        if candidates:
            return max(candidates, key=lambda pair: pair[0].confidence)
        return bottom_obs, bottom_frame
