# SPDX-License-Identifier: GPL-3.0-only
"""Interaction and geometry checks for the phone settings editor."""
import copy
import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PySide6 import QtCore, QtGui, QtTest, QtWidgets
from adb_app import PHONE_DEFAULTS
from fisher.adb import LAYOUT_PROFILE_KEYS, validate_phone_settings
from fisher.visual_settings import CloseButton, VisualSettingsDialog, fit_screen


class VisualSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def dialog(self, mode='fishing', settings=None, image=None):
        if settings is None:
            settings = copy.deepcopy(PHONE_DEFAULTS)
        if image is None:
            image = np.full((800, 360, 3), 120, dtype=np.uint8)
        dialog = VisualSettingsDialog(image, settings, mode)
        dialog.show()
        QtTest.QTest.qWait(20)
        self.addCleanup(dialog.close)
        return dialog

    def test_screen_fit_preserves_complete_frame_and_aspect(self):
        for width, height, aspect in ((300, 700, 360/800), (700, 300, 360/800),
                                     (400, 600, 9/16), (300, 600, 2/3)):
            with self.subTest(width=width, height=height, aspect=aspect):
                bounds = QtCore.QRectF(0, 0, width, height)
                screen = fit_screen(bounds, aspect)
                self.assertAlmostEqual(screen.width()/screen.height(), aspect)
                self.assertTrue(bounds.contains(screen))
                self.assertAlmostEqual(screen.center().x(), bounds.center().x())
                self.assertAlmostEqual(screen.center().y(), bounds.center().y())

    def test_drag_marker_and_resize_crop_use_phone_coordinates(self):
        dialog = self.dialog()
        editor = dialog.editor
        screen = editor.screen_rect()
        marker = editor.marker_position().toPoint()
        target = QtCore.QPoint(round(screen.x()+screen.width()*.65),
                               round(screen.y()+screen.height()*.72))
        QtTest.QTest.mousePress(editor, QtCore.Qt.MouseButton.LeftButton, pos=marker)
        QtTest.QTest.mouseMove(editor, target, delay=10)
        QtTest.QTest.mouseRelease(editor, QtCore.Qt.MouseButton.LeftButton, pos=target)
        result = dialog.result_settings()
        self.assertAlmostEqual(result['tap_x'], .65, delta=.01)
        self.assertAlmostEqual(result['tap_y'], .72, delta=.01)

        corner = editor.crop_rect().topLeft().toPoint()
        target = QtCore.QPoint(round(screen.x()+screen.width()*.1),
                               round(screen.y()+screen.height()*.1))
        QtTest.QTest.mousePress(editor, QtCore.Qt.MouseButton.LeftButton, pos=corner)
        QtTest.QTest.mouseMove(editor, target, delay=10)
        QtTest.QTest.mouseRelease(editor, QtCore.Qt.MouseButton.LeftButton, pos=target)
        crop = dialog.result_settings()['crop']
        for got, want in zip(crop, (.1, .1, .9, .9)):
            self.assertAlmostEqual(got, want, delta=.01)
        self.assertAlmostEqual(dialog.result_settings()['tap_x'], .65, delta=.01)

    def test_ruins_thresholds_are_editable_and_reset_to_defaults(self):
        cfg = copy.deepcopy(PHONE_DEFAULTS)
        cfg.update(ruins_normal_threshold=70, ruins_red_threshold=40,
                   ruins_tap_interval=.8, ruins_tap_max=6)
        dialog = self.dialog('ruins', cfg)
        self.assertEqual(dialog.result_settings()['ruins_normal_threshold'], 70)
        self.assertEqual(dialog.result_settings()['ruins_red_threshold'], 40)
        dialog._fields['ruins_normal_threshold'].slider.setValue(55)
        dialog._fields['ruins_red_threshold'].slider.setValue(35)
        self.assertEqual(dialog.result_settings()['ruins_normal_threshold'], 55)
        self.assertEqual(dialog.result_settings()['ruins_red_threshold'], 35)
        dialog.reset_button.click()
        result = dialog.result_settings()
        self.assertEqual((result['ruins_normal_threshold'], result['ruins_red_threshold']), (45, 30))
        self.assertEqual((result['ruins_tap_interval'], result['ruins_tap_max']), (.55, 1))
        self.assertNotIn('ruins_tap_interval', dialog._fields)
        self.assertNotIn('ruins_tap_max', dialog._fields)
        self.assertEqual(cfg['ruins_normal_threshold'], 70)

    def test_legacy_tap_limits_are_single_in_both_profiles(self):
        cfg = copy.deepcopy(PHONE_DEFAULTS)
        cfg.update(ruins_tap_max=2, layout_mode='manual',
                   layout_profiles={'auto': {'ruins_tap_max': 6},
                                    'manual': {'ruins_tap_max': 2}})
        dialog = self.dialog('ruins', cfg)
        self.assertNotIn('ruins_tap_max', dialog._fields)
        result = dialog.result_settings()
        self.assertEqual(result['ruins_tap_max'], 1)
        self.assertEqual(result['layout_profiles']['auto']['ruins_tap_max'], 1)
        self.assertEqual(result['layout_profiles']['manual']['ruins_tap_max'], 1)

    def test_ruins_points_are_independent_and_keyboard_accessible(self):
        dialog = self.dialog('ruins')
        dialog.point_buttons['FIGHT'].click()
        before = dialog.result_settings()['ruins_points']
        self.assertEqual(dialog.editor.point_key, 'FIGHT')
        dialog.editor.setFocus()
        QtTest.QTest.keyClick(dialog.editor, QtCore.Qt.Key.Key_Left)
        after = dialog.result_settings()['ruins_points']
        self.assertAlmostEqual(after['FIGHT'][0], before['FIGHT'][0]-.005)
        self.assertEqual(after['RETREAT'], before['RETREAT'])

    def test_cancel_preserves_input_and_reset_calibration_is_explicit(self):
        cfg = copy.deepcopy(PHONE_DEFAULTS)
        cfg['crop'] = [.1, .1, .8, .8]
        snapshot = copy.deepcopy(cfg)
        dialog = self.dialog('ruins', cfg)
        self.assertFalse(dialog.reset_device_calibration)
        dialog.reset_calibration_button.click()
        self.assertTrue(dialog.reset_device_calibration)
        dialog.reset_calibration_button.click()
        self.assertFalse(dialog.reset_device_calibration)
        dialog.editor.points['ADVANCE'][0] = .3
        dialog.cancel_button.click()
        self.assertEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Rejected)
        self.assertEqual(cfg, snapshot)

    def test_continuous_fishing_disables_limits_without_changing_them(self):
        dialog = self.dialog()
        self.assertFalse(dialog._fields['max_casts'].isEnabled())
        self.assertEqual(dialog.result_settings()['max_casts'], PHONE_DEFAULTS['max_casts'])
        dialog.continuous.click()
        self.assertTrue(dialog._fields['max_casts'].isEnabled())
        self.assertFalse(dialog.result_settings()['continuous'])
        self.assertEqual(dialog.result_settings()['max_casts'], PHONE_DEFAULTS['max_casts'])

    def test_unchanged_slider_preserves_exact_values_and_wheel_does_not_edit(self):
        cfg = copy.deepcopy(PHONE_DEFAULTS)
        cfg['capture_interval'] = .013
        dialog = self.dialog(settings=cfg)
        field = dialog._fields['capture_interval']
        self.assertEqual(dialog.result_settings()['capture_interval'], .013)
        slider = field.slider
        before = slider.value()
        event = QtGui.QWheelEvent(QtCore.QPointF(2, 2), QtCore.QPointF(2, 2),
                                  QtCore.QPoint(), QtCore.QPoint(0, 120),
                                  QtCore.Qt.MouseButton.NoButton,
                                  QtCore.Qt.KeyboardModifier.NoModifier,
                                  QtCore.Qt.ScrollPhase.NoScrollPhase, False)
        QtWidgets.QApplication.sendEvent(slider, event)
        self.assertEqual(slider.value(), before)
        self.assertEqual(dialog.result_settings()['capture_interval'], .013)

    def test_legacy_settings_initialize_two_deep_copied_profiles(self):
        cfg = copy.deepcopy(PHONE_DEFAULTS)
        cfg['crop'] = [.05, .1, .9, .8]
        cfg['tap_x'] = .42
        snapshot = copy.deepcopy(cfg)
        dialog = self.dialog(settings=cfg)
        result = dialog.result_settings()
        self.assertEqual(result['layout_mode'], 'auto')
        self.assertEqual(set(result['layout_profiles']), {'auto', 'manual'})
        for profile in result['layout_profiles'].values():
            self.assertEqual(set(profile), set(LAYOUT_PROFILE_KEYS))
            self.assertEqual(profile['crop'], [.05, .1, .9, .8])
            self.assertEqual(profile['tap_x'], .42)
            self.assertNotIn('layout_profiles', profile)
        result['layout_profiles']['auto']['crop'][0] = .2
        self.assertEqual(result['layout_profiles']['manual']['crop'][0], .05)
        self.assertEqual(cfg, snapshot)
        validate_phone_settings(dialog.result_settings())

    def test_switching_profiles_preserves_separate_fishing_geometry_and_timing(self):
        dialog = self.dialog()
        dialog.editor.crop = [.1, .1, .8, .8]
        dialog.editor.points['FISHING'] = [.6, .8]
        dialog._fields['input_latency_ms'].slider.setValue(120)
        dialog.continuous.click()
        dialog.layout_buttons['manual'].click()
        self.assertEqual(dialog.layout_mode, 'manual')
        self.assertEqual(dialog.editor.crop, [0., 0., 1., 1.])
        self.assertEqual(dialog._fields['input_latency_ms'].value(), 80.)
        self.assertTrue(dialog.continuous.isChecked())
        dialog.editor.crop = [.2, .1, .7, .8]
        dialog.editor.points['FISHING'] = [.3, .7]
        dialog._fields['input_latency_ms'].slider.setValue(150)
        dialog.humanize.click()
        result = dialog.result_settings()
        auto, manual = result['layout_profiles']['auto'], result['layout_profiles']['manual']
        self.assertEqual((auto['tap_x'], auto['tap_y'], auto['input_latency_ms']), (.6, .8, 120))
        self.assertFalse(auto['continuous'])
        self.assertEqual((manual['tap_x'], manual['tap_y'], manual['input_latency_ms']), (.3, .7, 150))
        self.assertFalse(manual['humanize'])
        self.assertEqual(result['crop'], manual['crop'])
        self.assertEqual(result['tap_x'], manual['tap_x'])
        dialog.layout_buttons['auto'].click()
        self.assertEqual(dialog.editor.crop, [.1, .1, .8, .8])
        self.assertEqual(dialog.editor.points['FISHING'], [.6, .8])
        self.assertEqual(dialog._fields['input_latency_ms'].value(), 120)
        self.assertFalse(dialog.continuous.isChecked())
        dialog.layout_buttons['manual'].click()
        self.assertEqual(dialog.editor.points['FISHING'], [.3, .7])
        self.assertFalse(dialog.humanize.isChecked())
        validate_phone_settings(dialog.result_settings())

    def test_ruins_profile_reset_only_changes_selected_mode(self):
        dialog = self.dialog('ruins')
        dialog._fields['ruins_normal_threshold'].slider.setValue(65)
        dialog.editor.points['FIGHT'] = [.7, .77]
        dialog.reset_calibration_button.click()
        self.assertTrue(dialog.reset_device_calibration)
        dialog.layout_buttons['manual'].click()
        self.assertFalse(dialog.reset_calibration_button.isEnabled())
        self.assertFalse(dialog.reset_device_calibration)
        dialog._fields['ruins_normal_threshold'].slider.setValue(80)
        dialog._fields['ruins_red_threshold'].slider.setValue(20)
        dialog.editor.points['FIGHT'] = [.6, .72]
        dialog.reset_button.click()
        result = dialog.result_settings()
        auto, manual = result['layout_profiles']['auto'], result['layout_profiles']['manual']
        self.assertEqual((auto['ruins_normal_threshold'], auto['ruins_points']['FIGHT']), (65, [.7, .77]))
        self.assertEqual((manual['ruins_normal_threshold'], manual['ruins_red_threshold']), (45, 30))
        self.assertEqual(manual['ruins_points']['FIGHT'], [.73, .82])
        self.assertEqual(result['layout_mode'], 'manual')
        self.assertEqual(result['ruins_normal_threshold'], 45)
        dialog.layout_buttons['auto'].click()
        self.assertTrue(dialog.reset_calibration_button.isEnabled())
        self.assertTrue(dialog.reset_device_calibration)
        self.assertEqual(dialog._fields['ruins_normal_threshold'].value(), 65)
        self.assertEqual(dialog.editor.points['FIGHT'], [.7, .77])
        validate_phone_settings(dialog.result_settings())

    def test_cancel_after_profile_switch_preserves_both_original_profiles(self):
        cfg = validate_phone_settings(copy.deepcopy(PHONE_DEFAULTS))
        cfg['layout_profiles']['manual']['tap_x'] = .28
        snapshot = copy.deepcopy(cfg)
        dialog = self.dialog(settings=cfg)
        dialog.layout_buttons['manual'].click()
        dialog.editor.points['FISHING'][0] = .8
        dialog._fields['input_latency_ms'].slider.setValue(200)
        dialog.cancel_button.click()
        self.assertEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Rejected)
        self.assertEqual(cfg, snapshot)

    def test_small_landscape_window_keeps_preview_and_buttons_reachable(self):
        dialog = self.dialog('ruins')
        dialog.resize(620, 500)
        self.app.processEvents()
        self.assertEqual(dialog.body.direction(), QtWidgets.QBoxLayout.Direction.LeftToRight)
        self.assertGreater(dialog.editor.screen_rect().width(), 90)
        self.assertTrue(dialog.rect().contains(dialog.save_button.mapTo(dialog, dialog.save_button.rect().bottomRight())))
        self.assertFalse(dialog.findChildren(QtWidgets.QAbstractSpinBox))

    def test_localized_small_window_has_no_hidden_horizontal_content(self):
        from fisher.i18n import translate
        for mode in ('fishing', 'ruins'):
            for language in ('en', 'ja', 'ko'):
                with self.subTest(mode=mode, language=language):
                    dialog = VisualSettingsDialog(np.zeros((800, 360, 3), np.uint8),
                        copy.deepcopy(PHONE_DEFAULTS), mode,
                        tr=lambda text: translate(text, language))
                    dialog.resize(620, 500)
                    dialog.show()
                    self.app.processEvents()
                    self.assertEqual(dialog.scroll.horizontalScrollBar().maximum(), 0)
                    self.assertTrue(dialog.rect().contains(dialog.save_button.mapTo(dialog, dialog.save_button.rect().bottomRight())))
                    dialog.close()

    def test_reveal_moves_and_fades_without_moving_window_or_disabling_controls(self):
        dialog = self.dialog()
        animation = dialog.animated_body
        before = dialog.geometry()
        viewport = animation.geometry()
        animation.start_reveal()
        self.assertEqual(animation.motion.duration(), 320)
        self.assertEqual(animation.motion.easingCurve().type(), QtCore.QEasingCurve.Type.BezierSpline)
        animation.animation.setCurrentTime(80)
        self.assertGreater(animation.offset, 0.)
        self.assertLess(animation.offset, 10.)
        if animation.effect is not None:
            self.assertGreater(animation.effect.opacity(), .25)
            self.assertLess(animation.effect.opacity(), 1.)
        dialog.continuous.click()
        self.assertFalse(dialog.continuous.isChecked())
        animation.animation.setCurrentTime(320)
        self.assertAlmostEqual(animation.offset, 0.)
        self.assertEqual(dialog.geometry(), before)
        self.assertEqual(animation.geometry(), viewport)
        if animation.effect is not None:
            self.assertAlmostEqual(animation.effect.opacity(), 1.)

    def test_cancel_and_close_work_during_reveal(self):
        for use_close in (False, True):
            with self.subTest(use_close=use_close):
                dialog = self.dialog()
                dialog.animated_body.start_reveal()
                control = dialog.findChild(CloseButton) if use_close else dialog.cancel_button
                control.click()
                self.assertEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Rejected)
                self.assertEqual(dialog.animated_body.animation.state(),
                                 QtCore.QAbstractAnimation.State.Stopped)
                self.assertAlmostEqual(dialog.animated_body.offset, 0.)


if __name__ == '__main__':
    unittest.main()
