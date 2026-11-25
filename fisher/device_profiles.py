# SPDX-License-Identifier: GPL-3.0-only
"""Local, device-scoped screen alignment without retaining device identifiers."""
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from .config import DATA_ROOT


class DeviceProfileStore:
    """Persist bounded normalized offsets for a device, crop and activity."""
    LIMIT = .20

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DATA_ROOT / 'device_profiles.json'

    @staticmethod
    def _key(serial, shape, mode, crop):
        if not isinstance(serial, str) or not serial or not isinstance(mode, str) or not mode:
            return None
        try:
            height, width = (int(shape[0]), int(shape[1]))
            area = list(crop if crop is not None else (0, 0, 1, 1))
            if (height < 100 or width < 100 or len(area) != 4
                    or any(isinstance(v, bool) or not isinstance(v, (int, float))
                           or not math.isfinite(v) for v in area)):
                return None
        except (TypeError, ValueError, IndexError):
            return None
        identity = json.dumps([serial, height, width, mode, [round(v, 5) for v in area]],
                              ensure_ascii=False, separators=(',', ':'))
        return hashlib.sha256(identity.encode('utf-8')).hexdigest()

    @classmethod
    def _valid_offset(cls, value):
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            return None
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) or abs(v) > cls.LIMIT for v in value):
            return None
        return float(value[0]), float(value[1])

    def _read(self):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def load(self, serial, shape, mode, crop=None):
        key = self._key(serial, shape, mode, crop)
        return self._valid_offset(self._read().get(key)) if key else None

    def _write(self, profiles):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.device_profiles_', suffix='.tmp',
                                             delete=False) as file:
                name = file.name
                json.dump(profiles, file, ensure_ascii=False, separators=(',', ':'))
            os.replace(name, self.path)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    def save(self, serial, shape, mode, offset, crop=None):
        key = self._key(serial, shape, mode, crop)
        value = self._valid_offset(offset)
        if not key or value is None:
            return False
        try:
            profiles = self._read()
            profiles[key] = list(value)
            self._write(profiles)
            return True
        except OSError:
            return False

    def clear(self, serial, shape, mode, crop=None):
        key = self._key(serial, shape, mode, crop)
        if not key:
            return False
        try:
            profiles = self._read()
            if key in profiles:
                profiles.pop(key)
                self._write(profiles)
            return True
        except OSError:
            return False
