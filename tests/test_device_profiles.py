# SPDX-License-Identifier: GPL-3.0-only
"""Device alignment remains private, bounded and isolated between layouts."""
import json
import tempfile
import unittest
from pathlib import Path

from fisher.device_profiles import DeviceProfileStore
from fisher.adb import validate_phone_settings
from adb_app import PHONE_DEFAULTS


class DeviceProfileTests(unittest.TestCase):
    def test_ruins_settings_migrate_and_reject_invalid_points_and_thresholds(self):
        settings = validate_phone_settings(PHONE_DEFAULTS)
        self.assertEqual((settings['ruins_normal_threshold'], settings['ruins_red_threshold']), (45, 30))
        self.assertEqual(settings['ruins_tap_max'], 1)
        self.assertEqual(validate_phone_settings(dict(PHONE_DEFAULTS,ruins_tap_max=3))['ruins_tap_max'], 1)
        self.assertEqual(settings['ruins_tap_interval'], .55)
        self.assertEqual(validate_phone_settings(dict(PHONE_DEFAULTS,ruins_tap_interval=.35))['ruins_tap_interval'], .55)
        self.assertIn('ADVANCE', settings['ruins_points'])
        for key, value in (('ruins_normal_threshold', 101), ('ruins_red_threshold', -1),
                           ('ruins_tap_max', 7), ('ruins_tap_interval', float('nan')),
                           ('ruins_points', {'ADVANCE': [1.5, .5]}),
                           ('ruins_points', {'UNKNOWN': [.5, .5]})):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_phone_settings(dict(PHONE_DEFAULTS, **{key: value}))

    def test_profiles_are_separate_for_device_activity_resolution_and_crop(self):
        with tempfile.TemporaryDirectory() as folder:
            store = DeviceProfileStore(Path(folder) / 'profiles.json')
            crop = [0, .02, 1, .98]
            self.assertTrue(store.save('private-serial', (2670, 1200), 'ruins', (.02, -.03), crop))
            self.assertEqual(store.load('private-serial', (2670, 1200), 'ruins', crop), (.02, -.03))
            self.assertIsNone(store.load('other', (2670, 1200), 'ruins', crop))
            self.assertIsNone(store.load('private-serial', (2670, 1200), 'fishing', crop))
            self.assertIsNone(store.load('private-serial', (2400, 1080), 'ruins', crop))
            self.assertIsNone(store.load('private-serial', (2670, 1200), 'ruins', [0, 0, 1, 1]))
            self.assertNotIn('private-serial', store.path.read_text(encoding='utf-8'))
            self.assertTrue(store.clear('private-serial', (2670, 1200), 'ruins', crop))
            self.assertIsNone(store.load('private-serial', (2670, 1200), 'ruins', crop))

    def test_corrupt_file_and_invalid_offsets_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profiles.json';path.write_text('{', encoding='utf-8')
            store = DeviceProfileStore(path)
            self.assertIsNone(store.load('x', (800, 360), 'fishing'))
            for value in ((float('nan'), 0), (.21, 0), ('0', 0), (True, 0), (0,)):
                self.assertFalse(store.save('x', (800, 360), 'fishing', value))
            self.assertEqual(path.read_text(encoding='utf-8'), '{')
            self.assertTrue(store.save('x', (800, 360), 'fishing', (.01, -.02)))
            self.assertIsInstance(json.loads(path.read_text(encoding='utf-8')), dict)


if __name__ == '__main__':
    unittest.main()
