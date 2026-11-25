# SPDX-License-Identifier: GPL-3.0-only
"""Release lookup, maintenance navigation, and uninstall handoff regressions."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtNetwork, QtWidgets

from fisher.maintenance import latest_version, uninstall_program, version_parts
from qt_fishing import FishingWindow


class MaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_stable_update_version_compares_numerically(self):
        newest = latest_version(b'{"tag_name":"v1.10.0","draft":false,"prerelease":false}')
        self.assertGreater(version_parts(newest), version_parts("1.9.9"))
        with self.assertRaises(ValueError):
            latest_version(b'{"tag_name":"v2.0.0","prerelease":true}')

    @unittest.skipUnless(sys.platform == "win32", "uses Windows registry metadata")
    def test_uninstall_entry_must_point_to_this_installation(self):
        with tempfile.TemporaryDirectory() as temp, patch("winreg.OpenKey"), patch("winreg.QueryValueEx") as value:
            folder = Path(temp)
            program = folder / "unins002.exe"
            program.touch()
            program.with_suffix(".dat").touch()
            value.return_value = (f'"{program}"', 1)
            self.assertEqual(uninstall_program(folder), program.resolve())
            value.return_value = (f'"{program}" /SILENT /NORESTART /TTTOOLPROMPT', 1)
            self.assertEqual(uninstall_program(folder), program.resolve())
            self.assertIsNone(uninstall_program(folder / "another-install"))
            value.return_value = (f'"{program}" /VERYSILENT', 1)
            self.assertIsNone(uninstall_program(folder))

    def test_source_menu_has_no_uninstall_and_keeps_all_languages(self):
        window = FishingWindow()
        self.addCleanup(window.deleteLater)
        for locale in ("zh_TW", "en", "ja", "ko"):
            window.set_language(locale, persist=False)
            menu = window.maintenance.menu(window.maintenance_button)
            self.assertEqual([action.text() for action in menu.actions()],
                             [window.tr(text) for text in ("檢查更新", "開啟檔案位置", "開啟設定資料夾")])
            menu.deleteLater()

    def test_update_uses_published_version_and_offers_release_page(self):
        window = FishingWindow()
        self.addCleanup(window.deleteLater)
        window.set_language("en", persist=False)
        maintenance = window.maintenance
        maintenance.reply = Mock()
        maintenance.reply.attribute.return_value = 200
        maintenance.reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        maintenance.reply.readAll.return_value = b'{"tag_name":"v99.1.0"}'
        with patch.object(maintenance, "offer_releases") as offer:
            maintenance.update_ready()
        offer.assert_called_once_with("有新版本", f"You have v{maintenance.version}. Version v99.1.0 is available.")
        self.assertIsNone(maintenance.reply)

    def test_current_version_still_offers_release_page(self):
        window = FishingWindow()
        self.addCleanup(window.deleteLater)
        window.set_language("en", persist=False)
        maintenance = window.maintenance
        maintenance.reply = Mock()
        maintenance.reply.attribute.return_value = 200
        maintenance.reply.error.return_value = QtNetwork.QNetworkReply.NetworkError.NoError
        maintenance.reply.readAll.return_value = f'{{"tag_name":"v{maintenance.version}"}}'.encode()
        with patch.object(maintenance, "offer_releases") as offer:
            maintenance.update_ready()
        offer.assert_called_once_with("更新檢查", f"You’re up to date on v{maintenance.version}.")

    def test_uninstall_cancel_keeps_session_open(self):
        window = FishingWindow()
        self.addCleanup(window.deleteLater)
        with (patch("fisher.maintenance.uninstall_program", return_value=Path("unins000.exe")),
              patch.object(window.maintenance, "dialog", return_value=(False, False)),
              patch.object(window, "close") as close):
            window.maintenance.uninstall()
        close.assert_not_called()

    def test_failed_uninstall_launch_keeps_window_reconnectable(self):
        window = FishingWindow()
        self.addCleanup(window.deleteLater)
        runner = Mock()
        window.runner = runner
        with (patch("fisher.maintenance.uninstall_program", return_value=Path("unins000.exe")),
              patch.object(window.maintenance, "dialog", return_value=(True, False)) as dialog,
              patch("fisher.maintenance.QtCore.QProcess.startDetached", return_value=(False, 0)),
              patch.object(window, "close") as close):
            window.maintenance.uninstall()
        runner.close.assert_called_once_with()
        self.assertIsNone(window.runner)
        close.assert_not_called()
        self.assertEqual(dialog.call_args.args[0], "無法啟動解除安裝程式")

    def test_uninstall_passes_delete_data_only_when_selected(self):
        window = FishingWindow()
        self.addCleanup(window.deleteLater)
        with (patch("fisher.maintenance.uninstall_program", return_value=Path("unins000.exe")),
              patch.object(window.maintenance, "dialog") as dialog,
              patch("fisher.maintenance.QtCore.QProcess.startDetached", return_value=(True, 1)) as launch,
              patch.object(window, "close")):
            for clear in (False, True):
                dialog.return_value = (True, clear)
                window.maintenance.uninstall()
                self.assertEqual("/TTTOOLCLEARDATA" in launch.call_args.args[1], clear)
