# SPDX-License-Identifier: GPL-3.0-only
"""Recognition and bounded decisions for the Ruins Adventure activity."""
from dataclasses import dataclass, replace
from collections import deque
from pathlib import Path
import cv2
import numpy as np
from .config import ROOT
from .ruins_geometry import RuinsGeometry, shifted_to_reference, side_viewport, error_dialog_target
from .ruins_odds import recognize_probability
from .ruins_battle_result import is_battle_result
from .ruins_chest import chest_button_target
from .vision import read_image


@dataclass(frozen=True)
class RuinsObservation:
    state: str
    chance: int | None = None
    confidence: float = 0.0
    base: int | None = None
    bonus: int | None = None
    red: bool = False
    target: tuple[float, float] | None = None
    red_uncertain: bool = False


class RuinsDetector:
    """Recognise confirmed activity controls from the full portrait game area."""
    def __init__(self, assets=None, offset=None, adaptive=True):
        assets = Path(assets or ROOT / 'assets' / 'ruins')
        try:
            atlas = read_image(assets / 'digits.png', cv2.IMREAD_GRAYSCALE)
        except (OSError, ValueError, cv2.error) as exc:
            raise ValueError('遺跡探險辨識資源缺失') from exc
        if (atlas is None or atlas.shape[1] != 160 or atlas.shape[0] < 100
                or atlas.shape[0] % 20):
            raise ValueError('遺跡探險辨識資源缺失')
        self.digits = [[atlas[row*20:(row+1)*20, digit*16:(digit+1)*16] > 0
                        for row in range(atlas.shape[0] // 20)] for digit in range(10)]
        self.adaptive = bool(adaptive)
        self.geometry = RuinsGeometry(offset if self.adaptive else None)
        self._frame_number = 0
        self.viewport = (0., 1.)
        self._initial_crop_offset = RuinsGeometry.bounded(offset) if self.adaptive else None
        self._viewport_pending = None
        self._viewport_agreements = 0

    @staticmethod
    def fraction(hsv, bounds, low, high):
        x1, y1, x2, y2 = bounds
        return float(np.mean(cv2.inRange(hsv[y1:y2, x1:x2], low, high) > 0))

    def probability(self, hsv):
        return recognize_probability(hsv, self.digits)

    def detect(self, image):
        if not self.adaptive:
            self._frame_number += 1
            scaled=cv2.resize(image,(360,800),interpolation=cv2.INTER_AREA)
            error=error_dialog_target(scaled)
            return RuinsObservation('ERROR',confidence=.98,target=error) if error else self._detect_scaled(scaled)
        if self._frame_number % 15 == 0:
            candidate=side_viewport(image)
            if candidate is not None:
                if self._frame_number == 0:
                    self.viewport=candidate
                    if self._initial_crop_offset:
                        restored=(self._initial_crop_offset[0]/candidate[1],self._initial_crop_offset[1])
                        self.geometry.offset=RuinsGeometry.bounded(restored) or (0.,0.)
                else:
                    if self._viewport_pending and max(abs(a-b) for a,b in zip(candidate,self._viewport_pending)) < .005:
                        self._viewport_agreements+=1
                    else:
                        self._viewport_pending,self._viewport_agreements=candidate,1
                    if self._viewport_agreements >= 3 and max(abs(a-b) for a,b in zip(candidate,self.viewport)) >= .005:
                        old_scale=self.viewport[1];self.viewport=candidate
                        remapped=(self.geometry.offset[0]*old_scale/candidate[1],self.geometry.offset[1])
                        self.geometry.offset=RuinsGeometry.bounded(remapped) or (0.,0.)
                        self.geometry.pending=None;self.geometry.agreements=0;self.geometry.ready=False
        left,width=self.viewport;w=image.shape[1]
        x1=max(0,min(w-1,round(left*w)));x2=max(x1+1,min(w,round((left+width)*w)))
        scaled = cv2.resize(image[:,x1:x2], (360, 800), interpolation=cv2.INTER_AREA)
        error=error_dialog_target(scaled)
        if error:
            self._frame_number += 1
            return RuinsObservation('ERROR',confidence=.98,target=(left+width*error[0],error[1]))
        obs = self._detect_scaled(shifted_to_reference(scaled, self.geometry.offset))
        if obs.state == 'CHEST' and obs.target is not None:
            # The button was detected in reference coordinates. Map it back
            # to the original cropped frame, including calibration and bars.
            x, y = obs.target
            dx, dy = self.geometry.offset
            obs = replace(obs, target=(left + width*(x + dx), y + dy))
        self._frame_number += 1
        # Adapt quickly when the current view cannot be recognized, then
        # reduce localization work after the offset has settled.
        interval = 60 if self.geometry.ready and obs.state != 'UNKNOWN' else 15
        if self._frame_number % interval:
            return obs
        if obs.state in ('ADVANCE', 'BOSS', 'CLAIM', 'LOBBY'):
            states = (obs.state,)
        elif obs.state == 'UNKNOWN':
            states = ('BOSS', 'CLAIM', 'ADVANCE', 'REWARD', 'LOBBY')
        else:
            return obs
        for state in states:
            proposal = self.geometry.locate(scaled, state)
            if self.geometry.bounded(proposal) is None:
                continue
            confirmed = self._detect_scaled(shifted_to_reference(scaled, proposal))
            if confirmed.state != state:
                continue
            if self.geometry.offer(proposal):
                return self._detect_scaled(shifted_to_reference(scaled, self.geometry.offset))
            break
        return obs

    def _detect_scaled(self, scaled):
        hsv = cv2.cvtColor(scaled, cv2.COLOR_BGR2HSV)
        f = lambda box, lo, hi: self.fraction(hsv, box, lo, hi)
        left = f((38,592,150,725), (35,70,45), (85,255,200))
        right = f((210,592,322,725), (90,70,35), (130,255,200))
        if left > .38 and right > .38:
            base, bonus, score = self.probability(hsv)
            glow = hsv[110:170,135:225]
            warm = (((glow[:,:,0] <= 13) | (glow[:,:,0] >= 167))
                    & (glow[:,:,1] > 110) & (glow[:,:,2] > 100)).astype(np.uint8)
            red_fraction = float(np.mean(warm))
            closed = cv2.morphologyEx(warm, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))
            _, _, red_stats, _ = cv2.connectedComponentsWithStats(closed)
            largest = float(max(red_stats[1:,4], default=0)) / warm.size
            # Use the contiguous glow as well as hue: orange treasure details
            # alone are not enough to establish a red treasure.
            red = red_fraction >= .30 and largest >= .20
            red_uncertain = not red and red_fraction >= .04 and largest >= .018
            chance = min(100,base+bonus) if base is not None and bonus is not None else None
            return RuinsObservation('BOSS', chance, score, base, bonus, red, red_uncertain=red_uncertain)
        if is_battle_result(scaled):
            return RuinsObservation('BATTLE_RESULT')
        chest_target = chest_button_target(scaled)
        if chest_target is not None:
            return RuinsObservation('CHEST', confidence=.95, target=chest_target)
        claim = f((110,726,250,771), (35,100,120), (90,255,255))
        if claim > .40:
            # A shifted round advance control can overlap this region. Only a
            # wide rectangular control is a claim button.
            claim_offset = self.geometry.locate(scaled, 'CLAIM')
            if claim_offset is not None and max(abs(v) for v in claim_offset) <= .05:
                return RuinsObservation('CLAIM')
        footer = f((115,738,245,764), (0,0,75), (180,80,200))
        dark = float(np.mean(hsv[80:200, :80, 2]))
        if footer > .10 and dark < 90:
            return RuinsObservation('REWARD')
        # Milestone banners temporarily cover the game while the underlying
        # advance control may already be visible but unable to accept input.
        banner = f((0,305,360,350), (0,100,100), (14,255,255))
        caption = f((80,288,280,310), (35,100,140), (90,255,255))
        if banner > .18 and caption > .025:
            return RuinsObservation('MILESTONE')
        advance = f((145,641,215,710), (68,100,120), (100,255,255))
        if advance > .36:
            return RuinsObservation('ADVANCE')
        orange = f((105,684,255,735), (5,100,130), (35,255,255))
        bright = f((85,560,275,780), (8,150,200), (35,255,255)) if orange > .30 else 0.
        if orange > .30 and bright > .025:
            offset=self.geometry.locate(scaled,'LOBBY')
            if offset is not None and max(abs(v) for v in offset) <= .05:
                return RuinsObservation('LOBBY')
        return RuinsObservation('UNKNOWN')


class RuinsController:
    """Require a confirmed state and rate-limit retries across animations."""
    POINTS = {'LOBBY': (.50, .88), 'ADVANCE': (.50, .86),
              'REWARD': (.50, .67), 'CLAIM': (.50, .94),
              'FIGHT': (.73, .82), 'RETREAT': (.26, .82)}
    NORMAL_WITHDRAW_THRESHOLD = 45
    RED_WITHDRAW_THRESHOLD = 30
    BOSS_READ_WINDOW = .8
    BOSS_COLOR_CONFIRM_TIME = .8
    BOSS_FIGHT_AFTER = 2.5
    BOSS_MAX_GAP = .75
    UNCERTAIN_INPUT_TIMEOUT = 12.0
    RETRY = {'LOBBY': 5., 'ADVANCE': 5., 'REWARD': 2.,
             'CLAIM': 5., 'FIGHT': 8., 'RETREAT': 8., 'ERROR': 8., 'CHEST': 3.}
    LABELS = {'LOBBY': '遺跡入口', 'ADVANCE': '探險中', 'REWARD': '發現寶藏',
              'BOSS': '遭遇首領', 'BATTLE_RESULT': '戰鬥結果', 'CLAIM': '探險結算', 'CHEST': '開啟寶箱', 'MILESTONE': '抵達遺跡新區域', 'ERROR': '遊戲錯誤提示', 'UNKNOWN': '等待畫面確認'}

    def __init__(self, settings=None, rng=None):
        self.configure(settings or {})
        self.reset()

    def configure(self, settings):
        self.normal_threshold = settings.get('ruins_normal_threshold', self.NORMAL_WITHDRAW_THRESHOLD)
        self.red_threshold = settings.get('ruins_red_threshold', self.RED_WITHDRAW_THRESHOLD)

    def reconfigure(self, settings):
        """Apply new controls while retaining counts and ambiguous-input state."""
        self.configure(settings)
        self.clear_observation()

    def reset(self):
        self.started = self.completed = 0
        self.lobby_latched = self.claim_latched = False
        self.candidate = None
        self.candidate_count = 0
        self.candidate_since = None
        self.last_action = {}
        self.last_touch = 0.0
        self.uncertain_state = None
        self.uncertain_since = self.uncertain_seen = None
        self.last_boss = None
        self.boss_reads = deque()
        self.boss_confirmed = False
        self.boss_since = None
        self.boss_seen = None
        self.boss_frames = 0
        self.fallback_fight = False
        self.boss_min = self.boss_max = None
        self.red_uncertain_reads = deque()
        self.possible_valuable = False
        self.treasure_uncertain = False
        self.odds_conflict = False
        self.valuable = False
        self.error_attempts = 0

    def clear_observation(self):
        """Drop screen confirmation while paused, disconnected or out of focus."""
        self.candidate = None
        self.candidate_count = 0
        self.candidate_since = None
        self.boss_reads.clear()
        self.boss_confirmed = False
        self.boss_since = None
        self.boss_seen = None
        self.boss_frames = 0
        self.fallback_fight = False
        self.red_uncertain_reads.clear()
        self.treasure_uncertain = False
        self.odds_conflict = False
        self.uncertain_since = self.uncertain_seen = None

    def observe(self, obs, now):
        self.treasure_uncertain = False
        self.odds_conflict = False
        self.fallback_fight = False
        if obs.state == 'BOSS':
            if self.boss_seen is None or now-self.boss_seen > self.BOSS_MAX_GAP:
                self.boss_since = now
                self.boss_frames = 0
            self.boss_seen = now
            self.boss_frames += 1
            while self.boss_reads and now-self.boss_reads[0][0] > self.BOSS_READ_WINDOW:
                self.boss_reads.popleft()
            if obs.chance is not None:
                self.boss_reads.append((now, obs.chance))
                self.boss_min = obs.chance if self.boss_min is None else min(self.boss_min, obs.chance)
                self.boss_max = obs.chance if self.boss_max is None else max(self.boss_max, obs.chance)
            while self.red_uncertain_reads and now-self.red_uncertain_reads[0] > self.BOSS_READ_WINDOW:
                self.red_uncertain_reads.popleft()
            if obs.red_uncertain:
                self.red_uncertain_reads.append(now)
                if len(self.red_uncertain_reads) >= 3 and now-self.red_uncertain_reads[0] >= .18:
                    self.possible_valuable = True
        else:
            # A different screen might be a new encounter. Never reuse odds.
            self.boss_reads.clear()
            if self.boss_seen is None or now-self.boss_seen > self.BOSS_MAX_GAP:
                self.boss_since = self.boss_seen = None
                self.boss_frames = 0
            self.red_uncertain_reads.clear()
        # Red is latched independently; its glow can pulse between frames.
        key = (obs.state, obs.chance)
        if key == self.candidate:
            self.candidate_count += 1
        else:
            self.candidate, self.candidate_count = key, 1
            self.candidate_since = now
        if obs.state == 'BOSS' and obs.red:
            self.valuable = True
            self.possible_valuable = True
        if self.uncertain_state:
            if obs.state not in (self.uncertain_state, 'UNKNOWN'):
                self.uncertain_state = None
                self.uncertain_since = self.uncertain_seen = None
            elif obs.state == self.uncertain_state:
                if self.uncertain_seen is None or now-self.uncertain_seen > .6:
                    self.uncertain_since = now
                self.uncertain_seen = now
                if now-self.uncertain_since >= self.UNCERTAIN_INPUT_TIMEOUT:
                    # Re-evaluate only after fresh frames continuously show the
                    # same actionable screen following an ambiguous ADB result.
                    self.uncertain_state = None
                    self.uncertain_since = self.uncertain_seen = None
            elif self.uncertain_seen is not None and now-self.uncertain_seen > .6:
                self.uncertain_since = self.uncertain_seen = None
        stable = (self.candidate_count >= 3 and self.candidate_since is not None
                  and now-self.candidate_since >= .18)
        boss_confirmed = (obs.state == 'BOSS' and obs.chance is not None
                          and len(self.boss_reads) >= 3
                          and now-self.boss_reads[0][0] >= .18
                          and all(value == obs.chance for _, value in self.boss_reads))
        self.boss_confirmed = boss_confirmed
        if obs.state == 'BOSS':
            stable = boss_confirmed
        if stable:
            if obs.state in ('LOBBY', 'ADVANCE', 'REWARD', 'CLAIM', 'BATTLE_RESULT', 'CHEST'):
                # Retain contradictory odds through unknown frames, foreground
                # interruptions and single-frame false state detections. A
                # confirmed battle-result ribbon ends the previous encounter.
                self.boss_min = self.boss_max = None
            if obs.state not in ('BOSS', 'UNKNOWN'):
                self.boss_since = self.boss_seen = None
                self.boss_frames = 0
            if obs.state not in ('ERROR','UNKNOWN') and self.error_attempts:
                self.error_attempts = 0
                self.last_action.pop('ERROR',None)
            if obs.state in ('REWARD','MILESTONE','BOSS','CLAIM','CHEST'):
                self.last_action.pop('ADVANCE', None)
            if obs.state in ('ADVANCE', 'REWARD', 'BOSS', 'CLAIM', 'CHEST') and self.lobby_latched:
                self.started += 1
                self.lobby_latched = False
            if obs.state == 'LOBBY' and self.claim_latched:
                self.completed += 1
                self.claim_latched = False
                self.valuable = False
                self.possible_valuable = False
        if self.uncertain_state:
            return None
        fallback = False
        if obs.state == 'BOSS':
            if boss_confirmed:
                # When the two configured thresholds imply different choices,
                # first allow the red glow to appear and retain ambiguous red
                # evidence from earlier encounters in the same expedition.
                differs = ((obs.chance < self.normal_threshold) != (obs.chance < self.red_threshold))
                if (not self.valuable and differs
                        and (self.possible_valuable or self.red_uncertain_reads
                             or now-self.boss_since < self.BOSS_COLOR_CONFIRM_TIME)):
                    self.treasure_uncertain = True
                threshold = self.red_threshold if self.valuable else self.normal_threshold
                if self.boss_min < threshold <= self.boss_max:
                    self.odds_conflict = True
                if not self.treasure_uncertain and not self.odds_conflict:
                    action = 'RETREAT' if obs.chance < threshold else 'FIGHT'
                else:
                    fallback = True
            else:
                fallback = True
            if fallback:
                if (self.boss_since is None or self.boss_frames < 3
                        or now-self.boss_since < self.BOSS_FIGHT_AFTER):
                    return None
                action = 'FIGHT'
        else:
            if not stable or obs.state == 'UNKNOWN':
                return None
            action = obs.state
        if action not in self.POINTS and action not in ('ERROR', 'CHEST'):
            return None
        if action in ('ERROR', 'CHEST') and obs.target is None:
            return None
        if now-self.last_touch < .8:
            return None
        if action in ('FIGHT','RETREAT'):
            last_boss = max(self.last_action.get('FIGHT',-float('inf')),
                            self.last_action.get('RETREAT',-float('inf')))
            if now-last_boss < self.RETRY[action]:
                return None
        retry = 30. if action == 'ERROR' and self.error_attempts >= 2 else self.RETRY[action]
        if now-self.last_action.get(action, -float('inf')) < retry:
            return None
        self.fallback_fight = fallback
        return action

    def commit(self, action, now, uncertain=False):
        self.last_action[action] = self.last_touch = now
        if action == 'LOBBY':
            self.lobby_latched = True
        elif action == 'CLAIM':
            self.claim_latched = True
        elif action == 'ERROR':
            self.error_attempts += 1
        if uncertain:
            self.uncertain_state = 'BOSS' if action in ('FIGHT', 'RETREAT') else action
            self.uncertain_since = self.uncertain_seen = None
