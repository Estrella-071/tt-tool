# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
import tempfile
import unittest

from fisher.ruins import RuinsController, RuinsObservation
from fisher.ruins_diagnostics import BossDiagnostics


class BossDiagnosticsTests(unittest.TestCase):
    def test_unreadable_fallback_records_reason_without_device_or_screen_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'decision.jsonl'
            diagnostics = BossDiagnostics(path)
            controller = RuinsController()
            obs = RuinsObservation('BOSS')
            action = None
            for t in (1., 1.5, 2., 2.5, 3., 3.5):
                action = controller.observe(obs, t)
                diagnostics.observe(obs, controller, action, t, 'sent' if action else None)
            self.assertEqual(action, 'FIGHT')
            entry = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual((entry['event'], entry['action'], entry['input']), ('decision', 'FIGHT', 'sent'))
            self.assertEqual((entry['reason'], entry['fallback_fight']), ('odds_unconfirmed', True))
            self.assertEqual(entry['readings'], {'unknown': 6})
            self.assertNotIn('device', entry)
            self.assertNotIn('image', entry)

    def test_treasure_ambiguity_and_failed_input_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'decision.jsonl'
            diagnostics = BossDiagnostics(path)
            controller = RuinsController()
            obs = RuinsObservation('BOSS', 35, base=30, bonus=5, red_uncertain=True)
            for t in (1 + i / 10 for i in range(26)):
                action = controller.observe(obs, t)
                diagnostics.observe(obs, controller, action, t, 'uncertain' if action else None)
            entry = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual((entry['base'], entry['bonus']), (30, 5))
            self.assertEqual((entry['reason'], entry['possible_red']), ('treasure_uncertain', True))
            self.assertEqual(entry['input'], 'uncertain')

    def test_conflicting_boss_readings_are_diagnosed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'decision.jsonl'
            diagnostics = BossDiagnostics(path)
            controller = RuinsController()
            high = RuinsObservation('BOSS', 80, base=80, bonus=0)
            controller.observe(high, 1.)
            diagnostics.observe(high, controller, None, 1.)
            low = RuinsObservation('BOSS', 30, base=25, bonus=5)
            for t in (1 + i / 10 for i in range(1, 26)):
                action = controller.observe(low, t)
                diagnostics.observe(low, controller, action, t, 'sent' if action else None)
            entry = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual((entry['reason'], entry['action']), ('odds_conflict', 'FIGHT'))
            self.assertEqual((entry['odds_min'], entry['odds_max']), (30, 80))

    def test_log_rolls_over_and_io_errors_do_not_interrupt_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'decision.jsonl'
            path.write_text('x' * BossDiagnostics.MAX_BYTES, encoding='utf-8')
            controller = RuinsController()
            obs = RuinsObservation('BOSS')
            diagnostics = BossDiagnostics(path)
            diagnostics.observe(obs, controller, 'FIGHT', 1., 'sent')
            self.assertTrue(path.with_name('decision.previous.jsonl').is_file())
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['action'], 'FIGHT')
            broken = BossDiagnostics(Path(directory))
            broken.observe(obs, controller, 'FIGHT', 1., 'sent')
            self.assertEqual(broken.retry_at, 61.)


if __name__ == '__main__':
    unittest.main()
