# SPDX-License-Identifier: GPL-3.0-only
"""Small, bounded local record of boss decisions without screen or device data."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from .config import DATA_ROOT


class BossDiagnostics:
    MAX_BYTES = 256 * 1024
    WAIT_INTERVAL = 5.0

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DATA_ROOT / 'logs' / 'ruins_decisions.jsonl'
        self.last_seen = None
        self.started = None
        self.last_log = None
        self.readings = Counter()
        self.red_frames = self.uncertain_red_frames = 0
        self.retry_at = 0.0

    def observe(self, obs, controller, action, now, input_result=None):
        if obs.state != 'BOSS':
            return
        if self.last_seen is None or now - self.last_seen > 1.5:
            self.started = now
            self.last_log = None
            self.readings.clear()
            self.red_frames = self.uncertain_red_frames = 0
        self.last_seen = now
        self.readings[str(int(obs.chance)) if obs.chance is not None else 'unknown'] += 1
        self.red_frames += int(bool(obs.red))
        self.uncertain_red_frames += int(bool(obs.red_uncertain))
        decided = action in ('FIGHT', 'RETREAT')
        waiting = (now - self.started >= self.WAIT_INTERVAL and
                   (self.last_log is None or now - self.last_log >= self.WAIT_INTERVAL))
        if not (decided or waiting) or now < self.retry_at:
            return
        reason = ('odds_unconfirmed' if not controller.boss_confirmed else
                  'treasure_uncertain' if controller.treasure_uncertain else
                  'odds_conflict' if controller.odds_conflict else 'confirmed')
        entry = {
            'time': datetime.now().astimezone().isoformat(timespec='seconds'),
            'event': 'decision' if decided else 'waiting',
            'action': action if decided else None,
            'input': input_result if decided else None,
            'fallback_fight': bool(controller.fallback_fight),
            'reason': reason,
            'elapsed_seconds': round(now-self.started, 2),
            'base': int(obs.base) if obs.base is not None else None,
            'bonus': int(obs.bonus) if obs.bonus is not None else None,
            'readings': dict(self.readings),
            'odds_min': controller.boss_min,
            'odds_max': controller.boss_max,
            'normal_threshold': controller.normal_threshold,
            'red_threshold': controller.red_threshold,
            'red_frames': self.red_frames,
            'uncertain_red_frames': self.uncertain_red_frames,
            'red_latched': bool(controller.valuable),
            'possible_red': bool(controller.possible_valuable),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists() and self.path.stat().st_size >= self.MAX_BYTES:
                self.path.replace(self.path.with_name(self.path.stem + '.previous.jsonl'))
            with self.path.open('a', encoding='utf-8') as output:
                output.write(json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + '\n')
            self.last_log = now
        except OSError:
            # Diagnostics must never stop an unattended run.
            self.retry_at = now + 60.0
