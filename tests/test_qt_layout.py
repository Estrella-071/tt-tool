# SPDX-License-Identifier: GPL-3.0-only
"""Responsive behavior and full-device preview regressions."""
import os
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtCore, QtGui, QtWidgets, QtTest
from qt_fishing import FishingWindow, PhonePreview, traditional_text
from fisher.adb import Device
from fisher.project import VERSION
from adb_app import PHONE_DEFAULTS
import numpy as np

class QtLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
    def setUp(self):
        self.real_refresh=FishingWindow.refresh
        self.refresh=patch.object(FishingWindow,'refresh',lambda _:None);self.refresh.start()
        self.temp=tempfile.TemporaryDirectory();self.w=FishingWindow();self.w.settings_path=Path(self.temp.name)/'settings.json';self.w.language_path=Path(self.temp.name)/'ui.json';self.w.show();QtTest.QTest.qWait(950)
    def tearDown(self):
        self.w.close();self.app.processEvents();self.refresh.stop();self.temp.cleanup()
    def test_width_and_aspect_control_layout_and_keep_actions_reachable(self):
        for width,height,vertical in ((1250,900,False),(900,700,False),(700,650,False),(700,850,True),(900,1100,True)):
            with self.subTest(width=width,height=height):
                self.w.resize(width,height);QtTest.QTest.qWait(60)
                actual=self.w.body.direction()==QtWidgets.QBoxLayout.Direction.TopToBottom
                self.assertEqual(actual,vertical)
                self.assertEqual(self.w.compact_controls.isVisible(),vertical)
                if vertical:
                    self.assertLessEqual(self.w.left.height(),self.w.body_scroll.viewport().height())
        self.assertEqual((self.w.minimumWidth(),self.w.minimumHeight()),(680,600))
        self.assertEqual((self.w.maximumWidth(),self.w.maximumHeight()),(3840,2160))
    def test_title_bar_is_single_line_and_centered_at_minimum_width(self):
        labels = (self.w.title_brand, self.w.title_version, self.w.title_subtitle, self.w.title_transport)
        for width in (self.w.minimumWidth(), 1180):
            self.w.resize(width, 750)
            for language in ('zh_TW', 'en', 'ja', 'ko'):
                with self.subTest(language=language, width=width):
                    self.w.set_language(language, persist=False)
                    self.app.processEvents()
                    self.assertEqual(self.w.title_version.text(), f'v{VERSION}')
                    self.assertGreaterEqual(self.w.title_layout.geometry().height(), 40)
                    self.assertEqual(self.w.max_button.visibleRegion().boundingRect(), self.w.max_button.rect())
                    if width == 1180:
                        self.assertTrue(self.w.title_subtitle.isVisible())
                    visible = [label for label in labels if label.isVisible()]
                    self.assertTrue(all(label in visible for label in (self.w.title_brand, self.w.title_version, self.w.title_transport)))
                    centers = [item.geometry().center().y() for item in (*visible, self.w.max_button)]
                    self.assertLessEqual(max(centers)-min(centers), 1)
                    for label in visible:
                        self.assertFalse(label.wordWrap())
                        self.assertGreaterEqual(label.width(), label.sizeHint().width())

    def test_default_size_shows_actions_and_graphical_settings_without_scrolling(self):
        self.w.resize(1180,900);QtTest.QTest.qWait(100)
        self.assertEqual(self.w.right_scroll.verticalScrollBar().maximum(),0)
        for widget in (self.w.advanced_toggle,self.w.start_btn,self.w.pause_btn):
            self.assertTrue(widget.isVisible())
            self.assertLess(widget.mapTo(self.w,widget.rect().bottomRight()).y(),self.w.height())
        self.assertFalse(self.w.findChildren(QtWidgets.QDoubleSpinBox))
        with patch('qt_fishing.VisualSettingsDialog') as factory:
            factory.return_value.exec.return_value=QtWidgets.QDialog.DialogCode.Rejected
            self.w.advanced_toggle.click()
            factory.assert_called_once()

    def test_maximize_and_restore_preserves_geometry_and_limits(self):
        self.w.resize(900,700);QtTest.QTest.qWait(50)
        before=QtCore.QRect(self.w.geometry());self.w.toggle_maximize();QtTest.QTest.qWait(50)
        self.assertTrue(self.w.window_expanded)
        self.assertLessEqual(self.w.width(),3840);self.assertLessEqual(self.w.height(),2160)
        self.w.toggle_maximize();QtTest.QTest.qWait(50)
        self.assertFalse(self.w.window_expanded)
        self.assertEqual(self.w.geometry(),before)
    def test_preview_zoom_can_be_opened_by_keyboard(self):
        image=QtGui.QImage(360,800,QtGui.QImage.Format.Format_RGB32);image.fill(QtGui.QColor('blue'))
        self.w.preview_label.setImage(image);self.w.preview_label.setFocus()
        QtTest.QTest.keyClick(self.w.preview_label,QtCore.Qt.Key.Key_Return)
        self.assertIsNotNone(self.w.zoom_dialog)
        self.assertEqual(self.w.zoom_preview.image.size(),image.size())
        self.w.zoom_dialog.close();self.app.processEvents()
        self.assertIsNone(self.w.zoom_dialog)
    def test_connection_waits_for_stream_and_does_not_bind_to_launcher(self):
        self.w.selected_device = 'fixture'
        self.w.devices = [Device('fixture', 'device')]
        self.w.update_device_items()
        self.w.ffmpeg_path = 'custom-ffmpeg'
        self.w.pending_start = True
        with patch('qt_fishing.Adb') as adb, patch('qt_fishing.PhoneRunner') as factory, \
                patch('qt_fishing.shutil.which', return_value='custom-ffmpeg'), \
                patch.object(self.w, 'background', side_effect=lambda work, done: done(work())):
            adb.return_value.capture.return_value = Mock(image=np.zeros((800, 360, 3), dtype=np.uint8))
            runner = factory.return_value
            runner.ready.is_set.return_value = False
            runner.active.is_set.return_value = False
            runner.session_started.is_set.return_value = False
            self.w.connect_device()
            adb.return_value.foreground.assert_not_called()
            self.assertEqual(factory.call_args.args[3:], ((800, 360),))
            self.assertEqual(factory.call_args.kwargs, {'ffmpeg': 'custom-ffmpeg'})
            self.assertFalse(self.w.start_btn.isEnabled())
            self.assertEqual(self.w.headline.text(), self.w.tr('等待手機畫面'))
            runner.arm.assert_not_called()
            runner.messages.empty.side_effect = [False, True]
            runner.messages.get_nowait.return_value = {
                'status': '畫面已就緒，可以開始釣魚。', 'state': '', 'reason': '', 'image': None,
                'fps': 0, 'age_ms': 0, 'casts': 0, 'results': 0,
            }
            runner.ready.is_set.return_value = True
            self.w.poll()
            runner.arm.assert_called_once_with(False)
            self.assertTrue(self.w.start_btn.isEnabled())
            self.w.runner = None

    def test_connection_tools_apply_ffmpeg_path_without_reopening(self):
        path = Path(self.temp.name) / 'ffmpeg.exe'
        path.touch()
        label = self.w.label('')
        self.w.set_tool_path('ffmpeg_path', str(path), label)
        self.assertEqual(self.w.ffmpeg_path, str(path))
        saved = json.loads(self.w.language_path.read_text(encoding='utf-8'))
        self.assertEqual(saved['ffmpeg_path'], str(path))
        with patch('qt_fishing.shutil.which', side_effect=['adb.exe', str(path)]), \
                patch('qt_fishing.subprocess.run') as probe, patch.object(self.w, 'refresh') as refresh, \
                patch.object(self.w, 'background', side_effect=lambda work, done: done(work())):
            self.w.retry_connection(Mock())
            self.assertEqual([call.args[0] for call in probe.call_args_list],
                             [['adb.exe', 'version'], [str(path), '-version']])
            refresh.assert_called_once_with()

    def test_start_arms_fishing_not_observation(self):
        runner=Mock();runner.active.is_set.return_value=False;runner.session_started.is_set.return_value=False;runner.settings=self.w.settings();self.w.runner=runner
        with patch.object(self.w,'save',return_value=runner.settings):self.w.start()
        runner.arm.assert_called_once_with(False);self.w.runner=None
    def test_resume_keeps_pending_settings_for_next_session(self):
        runner=Mock();runner.active.is_set.return_value=False;runner.session_started.is_set.return_value=True;self.w.runner=runner
        with patch.object(self.w,'save') as save:self.w.start()
        save.assert_not_called();runner.arm.assert_called_once_with(False);self.w.runner=None
    def test_action_buttons_reflect_runner_state(self):
        self.assertFalse(self.w.start_btn.isEnabled());self.assertFalse(self.w.pause_btn.isEnabled())
        runner=Mock();runner.active.is_set.return_value=False;runner.session_started.is_set.return_value=False;self.w.runner=runner;self.w.update_action_buttons()
        self.assertTrue(self.w.start_btn.isEnabled());self.assertFalse(self.w.pause_btn.isEnabled());self.assertEqual(self.w.start_btn.text(),'開始釣魚')
        runner.active.is_set.return_value=True;runner.session_started.is_set.return_value=True;self.w.update_action_buttons()
        self.assertTrue(self.w.start_btn.isEnabled());self.assertEqual(self.w.start_btn.text(),'暫停釣魚');self.assertTrue(self.w.pause_btn.isEnabled())
        runner.active.is_set.return_value=False;self.w.update_action_buttons()
        self.assertEqual(self.w.start_btn.text(),'繼續釣魚');self.assertTrue(self.w.pause_btn.isEnabled());self.w.runner=None
    def test_space_toggles_and_end_is_separate(self):
        runner=Mock();runner.active.is_set.return_value=False;runner.session_started.is_set.return_value=False;runner.settings=self.w.settings();self.w.runner=runner
        with patch.object(self.w,'save',return_value=runner.settings):
            self.w.activateWindow();self.w.setFocus();QtTest.QTest.qWait(20)
            QtTest.QTest.keyClick(self.w,QtCore.Qt.Key.Key_Space);self.app.processEvents()
            runner.arm.assert_called_once_with(False)
            runner.active.is_set.return_value=True;QtTest.QTest.keyClick(self.w,QtCore.Qt.Key.Key_Space);self.app.processEvents()
            runner.pause.assert_called_once_with()
            self.w.end();runner.end.assert_called_once_with()
        self.w.runner=None
    def test_modes_are_parallel_and_switch_stops_existing_session(self):
        runner=Mock();runner.active.is_set.return_value=True;runner.session_started.is_set.return_value=True
        self.w.runner=runner
        with patch.object(self.w,'connect_device') as connect:
            self.w.switch_mode('ruins')
        runner.close.assert_called_once_with();connect.assert_called_once_with()
        self.assertEqual(self.w.mode,'ruins');self.assertEqual(self.w.control_title.text(),'遺跡探險')
        self.assertEqual(self.w.stat_titles[1].text(),'已完成');self.assertFalse(self.w.advanced_toggle.isHidden())
        self.assertEqual(self.w.ruins_mode.objectName(),'modeSelected')
        self.w.runner=None;self.w.switch_mode('fishing')
        self.assertEqual(self.w.control_title.text(),'釣魚控制')
        self.assertFalse(self.w.advanced_toggle.isHidden())



    def test_cancel_graphical_settings_keeps_connection_and_settings(self):
        before=self.w.settings();runner=Mock();runner.active.is_set.return_value=True
        runner.capture.snapshot.return_value=(type('Frame',(),{'image':np.zeros((800,360,3),dtype=np.uint8)})(),None);self.w.runner=runner
        with patch('qt_fishing.VisualSettingsDialog') as dialog:
            dialog.return_value.exec.return_value=QtWidgets.QDialog.DialogCode.Rejected
            self.w.open_settings()
        self.assertIs(self.w.runner,runner);runner.close.assert_not_called();runner.pause.assert_not_called()
        self.assertEqual(self.w.settings(),before);self.w.runner=None

    def test_graphical_settings_apply_and_persist_both_ruins_thresholds(self):
        self.w.switch_mode('ruins');settings=self.w.settings()
        settings['ruins_normal_threshold']=55;settings['ruins_red_threshold']=25
        with patch('qt_fishing.VisualSettingsDialog') as dialog:
            dialog.return_value.exec.return_value=QtWidgets.QDialog.DialogCode.Accepted
            dialog.return_value.result_settings.return_value=settings
            dialog.return_value.reset_device_calibration=False
            self.w.open_settings()
        self.assertEqual(self.w.settings()['ruins_normal_threshold'],55)
        self.assertEqual(self.w.settings()['ruins_red_threshold'],25)
        self.assertEqual(json.loads(self.w.settings_path.read_text(encoding='utf-8'))['ruins_red_threshold'],25)
        self.assertIn('55%',self.w.mode_summary.text());self.assertIn('25%',self.w.mode_summary.text())

    def test_live_mode_switch_reconfigures_without_closing_or_resetting_session(self):
        runner=Mock();runner.active.is_set.return_value=True;runner.session_started.is_set.return_value=True
        runner.capture.snapshot.return_value=(type('Frame',(),{'image':np.zeros((800,360,3),dtype=np.uint8)})(),None)
        self.w.runner=runner;settings=self.w.settings();settings['layout_mode']='manual'
        with patch('qt_fishing.VisualSettingsDialog') as dialog:
            dialog.return_value.exec.return_value=QtWidgets.QDialog.DialogCode.Accepted
            dialog.return_value.result_settings.return_value=settings
            dialog.return_value.reset_device_calibration=False
            self.w.open_settings()
        runner.reconfigure.assert_called_once()
        self.assertEqual(runner.reconfigure.call_args.args[0]['layout_mode'],'manual')
        runner.close.assert_not_called();runner.pause.assert_not_called();runner.end.assert_not_called()
        self.w.runner=None

    def test_language_switch_translates_live_status_without_changing_decision(self):
        self.w.switch_mode('ruins')
        self.w.show_status('自動探險中','遭遇首領','紅色寶藏 · 勝率 30% + 8% = 38% · 戰鬥（門檻 30%）')
        for lang in ('en','ja','ko'):
            self.w.set_language(lang,persist=False)
            self.assertNotIn('紅色寶藏',self.w.detail.text())
            self.assertIn('38%',self.w.detail.text())
        self.w.set_language('zh_TW',persist=False)
        self.assertIn('紅色寶藏',self.w.detail.text())

    def test_language_preference_persists_without_modifying_activity_settings(self):
        before=self.w.settings();self.w.set_language('ko')
        self.assertEqual(json.loads(self.w.language_path.read_text(encoding='utf-8'))['language'],'ko')
        self.assertEqual(self.w.settings(),before)

    @unittest.skipUnless(os.name=='nt','uses Windows Traditional Chinese locale mapping')
    def test_runtime_messages_are_traditional(self):
        self.assertEqual(traditional_text('等待鱼上钩 · 画面未确认，已暂停'),'等待魚上鉤 · 畫面未確認，已暫停')
    def test_auto_connect_only_one_authorized_device(self):
        device=lambda serial: type('Device',(),{'serial':serial,'state':'device'})()
        with patch('qt_fishing.Adb') as adb, patch.object(self.w,'background',side_effect=lambda work,done:done(work())), patch.object(self.w,'connect_device') as connect:
            adb.return_value.devices.return_value=[device('one')];self.real_refresh(self.w);connect.assert_called_once_with()
            connect.reset_mock();adb.return_value.devices.return_value=[device('one'),device('two')];self.real_refresh(self.w);connect.assert_not_called()
            self.w.auto_connect=False;adb.return_value.devices.return_value=[device('one')];self.real_refresh(self.w);connect.assert_not_called()
    def test_discovery_retries_even_if_old_device_list_was_authorized(self):
        self.w.devices=[type('Device',(),{'state':'device'})()]
        with patch.object(self.w,'refresh') as refresh:
            self.w.scan_if_needed();refresh.assert_called_once_with()
            refresh.reset_mock();self.w.auto_connect=False;self.w.scan_if_needed();refresh.assert_not_called()
    def test_scan_action_restores_selected_phone(self):
        self.w.devices = [type('Device', (), {'serial': 'phone', 'state': 'device'})()]
        self.w.selected_device = 'phone'
        self.w.update_device_items()
        scan = self.w.device.findData(self.w.SCAN_ACTION)
        self.w.device.setCurrentIndex(scan)
        with patch.object(self.w, 'refresh') as refresh:
            self.w.select_device_item(scan)
        refresh.assert_called_once()
        self.assertEqual(self.w.device.currentData(), 'phone')
    def test_close_fades_before_ending_the_session(self):
        runner = Mock()
        self.w.runner = runner
        with patch.object(self.w, 'motion_enabled', return_value=True):
            self.w.close()
            self.assertTrue(self.w.isVisible())
            self.assertEqual(self.w.fade_action, 'close')
            runner.close.assert_not_called()
            QtTest.QTest.qWait(250)
        self.assertFalse(self.w.isVisible())
        runner.close.assert_called_once_with()
        self.assertIsNone(self.w.runner)
    def test_close_dismisses_owned_usb_guide(self):
        self.w.show_usb_help()
        dialog = self.app.activeModalWidget()
        self.assertIsInstance(dialog, QtWidgets.QDialog)
        self.assertTrue(dialog.isVisible())
        self.w.close()
        self.assertIsNone(self.app.activeModalWidget())
        self.assertFalse(self.w.isVisible())
    def test_preview_retains_complete_device_image(self):
        image=QtGui.QImage(360,800,QtGui.QImage.Format.Format_RGB32)
        image.fill(QtGui.QColor('blue'));image.setPixelColor(180,0,QtGui.QColor('red'));image.setPixelColor(180,799,QtGui.QColor('green'))
        self.w.preview_label.setImage(image)
        self.assertEqual((self.w.preview_label.image.width(),self.w.preview_label.image.height()),(360,800))
        self.assertEqual(self.w.preview_label.image.pixelColor(180,0),QtGui.QColor('red'))
        self.assertEqual(self.w.preview_label.image.pixelColor(180,799),QtGui.QColor('green'))

if __name__=='__main__':unittest.main()
