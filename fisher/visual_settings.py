# SPDX-License-Identifier: GPL-3.0-only
"""Visual, reversible settings for the phone activities.

The preview edits normalized coordinates.  It never sends input to the device;
the caller decides when accepted settings become active.
"""
from copy import deepcopy
import math

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from .adb import LAYOUT_PROFILE_KEYS, PHONE_DEFAULTS
from .ruins import RuinsController


RUINS_DEFAULTS = {
    'ruins_normal_threshold': 45,
    'ruins_red_threshold': 30,
    'ruins_tap_interval': .55,
    'ruins_tap_max': 1,
}

POINT_LABELS = (
    ('LOBBY', '入口'), ('ADVANCE', '前進'), ('REWARD', '寶藏'),
    ('CLAIM', '結算'), ('FIGHT', '戰鬥'), ('RETREAT', '撤離'),
)


def _clamp(value, low=0., high=1.):
    return max(low, min(high, float(value)))


def fit_screen(bounds, aspect, margin=16.):
    """Centered, aspect-preserving screen rectangle in widget coordinates."""
    bounds = QtCore.QRectF(bounds).adjusted(margin, margin, -margin, -margin)
    if bounds.width() <= 0 or bounds.height() <= 0:
        return QtCore.QRectF()
    aspect = max(.01, float(aspect))
    width = min(bounds.width(), bounds.height() * aspect)
    height = width / aspect
    return QtCore.QRectF(bounds.center().x() - width / 2,
                         bounds.center().y() - height / 2, width, height)


def _image_copy(image):
    if isinstance(image, QtGui.QImage):
        return image.copy()
    if image is None:
        return QtGui.QImage()
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError('手機預覽畫面格式無效')
    image = np.ascontiguousarray(image)
    h, w = image.shape[:2]
    return QtGui.QImage(image.data, w, h, image.strides[0],
                        QtGui.QImage.Format.Format_BGR888).copy()


class PhoneEditor(QtWidgets.QWidget):
    """Drag the crop corners or the selected, crop-relative touch point."""
    changed = QtCore.Signal()

    def __init__(self, image, crop, points, point_key, tr, parent=None):
        super().__init__(parent)
        self.image = _image_copy(image)
        self.crop = list(map(float, crop))
        self.points = {key: list(map(float, point)) for key, point in points.items()}
        self.point_key = point_key
        self.tr = tr
        self._drag = None
        self._drag_origin = None
        self._drag_crop = None
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(tr('畫面與操作位置'))
        self.setToolTip(tr('拖曳角落調整遊戲範圍，拖曳圓點調整觸控位置'))
        self.setMinimumSize(170, 240)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                           QtWidgets.QSizePolicy.Policy.Expanding)

    def screen_rect(self):
        aspect = (self.image.width() / self.image.height()
                  if not self.image.isNull() else 360 / 800)
        return fit_screen(self.rect(), aspect)

    def crop_rect(self):
        r = self.screen_rect()
        x, y, w, h = self.crop
        return QtCore.QRectF(r.x()+x*r.width(), r.y()+y*r.height(),
                             w*r.width(), h*r.height())

    def marker_position(self):
        crop = self.crop_rect()
        x, y = self.points[self.point_key]
        return QtCore.QPointF(crop.x()+x*crop.width(), crop.y()+y*crop.height())

    def set_point_key(self, key):
        if key in self.points:
            self.point_key = key
            self.update()

    def set_values(self, crop, points):
        self.crop = list(map(float, crop))
        self.points = {key: list(map(float, point)) for key, point in points.items()}
        self._drag = None
        self.update()

    def _full_point(self, pos):
        r = self.screen_rect()
        if r.width() <= 0 or r.height() <= 0:
            return (0., 0.)
        return (_clamp((pos.x()-r.x())/r.width()),
                _clamp((pos.y()-r.y())/r.height()))

    def _set_marker(self, pos):
        crop = self.crop_rect()
        if crop.width() <= 0 or crop.height() <= 0:
            return
        self.points[self.point_key] = [_clamp((pos.x()-crop.x())/crop.width()),
                                       _clamp((pos.y()-crop.y())/crop.height())]
        self.changed.emit()
        self.update()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        pos, crop = event.position(), self.crop_rect()
        if QtCore.QLineF(pos, self.marker_position()).length() <= 22:
            self._drag = 'point'
        else:
            corners = {'tl': crop.topLeft(), 'tr': crop.topRight(),
                       'bl': crop.bottomLeft(), 'br': crop.bottomRight()}
            self._drag = next((key for key, corner in corners.items()
                               if QtCore.QLineF(pos, corner).length() <= 16), None)
            if self._drag is None and crop.adjusted(-8, -8, 8, 8).contains(pos):
                if not crop.adjusted(8, 8, -8, -8).contains(pos):
                    self._drag = 'move'
                elif crop.contains(pos):
                    self._drag = 'point'
                    self._set_marker(pos)
        if self._drag:
            self._drag_origin = self._full_point(pos)
            self._drag_crop = list(self.crop)
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if not self._drag:
            super().mouseMoveEvent(event)
            return
        if self._drag == 'point':
            self._set_marker(event.position())
        else:
            x, y = self._full_point(event.position())
            ox, oy, w, h = self._drag_crop
            left, top, right, bottom = ox, oy, ox+w, oy+h
            minimum = .05
            if self._drag == 'move':
                dx, dy = x-self._drag_origin[0], y-self._drag_origin[1]
                left = _clamp(ox+dx, 0, 1-w)
                top = _clamp(oy+dy, 0, 1-h)
                right, bottom = left+w, top+h
            else:
                if 'l' in self._drag: left = _clamp(x, 0, right-minimum)
                if 'r' in self._drag: right = _clamp(x, left+minimum, 1)
                if 't' in self._drag: top = _clamp(y, 0, bottom-minimum)
                if 'b' in self._drag: bottom = _clamp(y, top+minimum, 1)
            self.crop = [left, top, right-left, bottom-top]
            self.changed.emit()
            self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        keys = {QtCore.Qt.Key.Key_Left: (-1, 0), QtCore.Qt.Key.Key_Right: (1, 0),
                QtCore.Qt.Key.Key_Up: (0, -1), QtCore.Qt.Key.Key_Down: (0, 1)}
        if event.key() in keys:
            step = .02 if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier else .005
            dx, dy = keys[event.key()]
            x, y = self.points[self.point_key]
            self.points[self.point_key] = [_clamp(x+dx*step), _clamp(y+dy*step)]
            self.changed.emit()
            self.update()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor('#d7d0e2'))
        p.drawRoundedRect(QtCore.QRectF(self.rect()), 24, 24)
        screen = self.screen_rect()
        if screen.isEmpty(): return
        p.setBrush(QtGui.QColor('#302b40'))
        p.drawRoundedRect(screen.adjusted(-4, -4, 4, 4), 25, 25)
        path = QtGui.QPainterPath()
        path.addRoundedRect(screen, 21, 21)
        p.save()
        p.setClipPath(path)
        if self.image.isNull():
            p.fillRect(screen, QtGui.QColor('#302b40'))
            p.setPen(QtGui.QColor('#ded8e9'))
            p.drawText(screen, QtCore.Qt.AlignmentFlag.AlignCenter, self.tr('尚無手機畫面'))
        else:
            p.drawImage(screen, self.image)
        mask = QtGui.QPainterPath()
        mask.addRect(screen)
        mask.addRect(self.crop_rect())
        mask.setFillRule(QtCore.Qt.FillRule.OddEvenFill)
        p.fillPath(mask, QtGui.QColor(24, 19, 34, 150))
        p.restore()
        crop = self.crop_rect()
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor(42, 34, 57, 180), 5))
        p.drawRoundedRect(crop, 5, 5)
        p.setPen(QtGui.QPen(QtGui.QColor('#f9f6ff'), 2))
        p.drawRoundedRect(crop, 5, 5)
        for point in (crop.topLeft(), crop.topRight(), crop.bottomLeft(), crop.bottomRight()):
            p.setPen(QtGui.QPen(QtGui.QColor('#5f4e87'), 2))
            p.setBrush(QtGui.QColor('#ffffff'))
            p.drawEllipse(point, 6, 6)
        point = self.marker_position()
        p.setPen(QtGui.QPen(QtGui.QColor('#ffffff'), 3))
        p.setBrush(QtGui.QColor('#5f4e87'))
        p.drawEllipse(point, 11, 11)
        p.setPen(QtGui.QPen(QtGui.QColor('#ffffff'), 2))
        p.drawLine(point + QtCore.QPointF(-5, 0), point + QtCore.QPointF(5, 0))
        p.drawLine(point + QtCore.QPointF(0, -5), point + QtCore.QPointF(0, 5))
        if self.hasFocus():
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.setPen(QtGui.QPen(QtGui.QColor('#8c79ad'), 2))
            p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1), 24, 24)


class GuardedSlider(QtWidgets.QSlider):
    """Scrolling the settings page must not change a value."""
    def wheelEvent(self, event):
        event.ignore()


class SliderField(QtWidgets.QWidget):
    def __init__(self, label, value, low, high, step, suffix, tr, parent=None, options=None):
        super().__init__(parent)
        self.original, self.step, self.suffix = value, step, suffix
        self.options = options
        self.changed_by_user = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        top = QtWidgets.QHBoxLayout()
        self.caption = QtWidgets.QLabel(tr(label))
        self.caption.setWordWrap(True)
        self.value_label = QtWidgets.QLabel()
        self.value_label.setObjectName('settingValue')
        top.addWidget(self.caption, 1)
        top.addWidget(self.value_label, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addLayout(top)
        self.slider = GuardedSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setAccessibleName(tr(label))
        self.slider.setRange(0 if options else round(low/step),
                             len(options)-1 if options else round(high/step))
        self.slider.setSingleStep(1)
        self.slider.setPageStep(max(1, (self.slider.maximum()-self.slider.minimum())//20))
        self.slider.setValue(self._position(value))
        self.slider.valueChanged.connect(self._changed)
        layout.addWidget(self.slider)
        self._show_value(float(value))

    def _show_value(self, value):
        if self.step >= 1:
            text = str(int(round(value)))
        else:
            digits = max(0, min(3, int(math.ceil(-math.log10(self.step)))))
            text = f'{value:.{digits}f}'.rstrip('0').rstrip('.')
        self.value_label.setText(text + self.suffix)

    def _changed(self, value):
        self.changed_by_user = True
        self._show_value(self.options[value] if self.options else value*self.step)

    def _position(self, value):
        if self.options:
            return min(range(len(self.options)), key=lambda i: abs(self.options[i]-float(value)))
        return round(float(value)/self.step)

    def value(self):
        if not self.changed_by_user:
            return self.original
        value = (self.options[self.slider.value()] if self.options
                 else self.slider.value()*self.step)
        return int(round(value)) if self.step >= 1 else round(value, 5)

    def set_value(self, value):
        self.original = value
        self.slider.blockSignals(True)
        self.slider.setValue(self._position(value))
        self.slider.blockSignals(False)
        self.changed_by_user = False
        self._show_value(float(value))


class DragHeader(QtWidgets.QFrame):
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle: handle.startSystemMove()
        super().mousePressEvent(event)


class CloseButton(QtWidgets.QAbstractButton):
    """A small drawn control that does not depend on a font glyph."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setBrush(QtGui.QColor('#e4deeb') if self.underMouse() else QtCore.Qt.BrushStyle.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor('#8c79ad'), 2) if self.hasFocus() else QtCore.Qt.PenStyle.NoPen)
        p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1), 17, 17)
        p.setPen(QtGui.QPen(QtGui.QColor('#51485f'), 1.7,
                            QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap))
        p.drawLine(QtCore.QPointF(13, 13), QtCore.QPointF(23, 23))
        p.drawLine(QtCore.QPointF(23, 13), QtCore.QPointF(13, 23))


class AnimatedBody(QtWidgets.QWidget):
    """Reveal laid-out content inside a fixed viewport without moving the dialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.content = QtWidgets.QWidget(self)
        self._offset = 0.
        try:
            self.effect = QtWidgets.QGraphicsOpacityEffect(self.content)
            self.effect.setOpacity(1.)
            self.content.setGraphicsEffect(self.effect)
        except (RuntimeError, AttributeError):
            # The positional reveal still works on platforms without this effect.
            self.effect = None
        curve = QtCore.QEasingCurve(QtCore.QEasingCurve.Type.BezierSpline)
        curve.addCubicBezierSegment(QtCore.QPointF(.65, 0.), QtCore.QPointF(.35, 1.),
                                    QtCore.QPointF(1., 1.))
        self.motion = QtCore.QPropertyAnimation(self, b'offset', self)
        self.motion.setDuration(320)
        self.motion.setEasingCurve(curve)
        self.animation = QtCore.QParallelAnimationGroup(self)
        self.animation.addAnimation(self.motion)
        self.fade = None
        if self.effect is not None:
            self.fade = QtCore.QPropertyAnimation(self.effect, b'opacity', self)
            self.fade.setDuration(320)
            self.fade.setEasingCurve(curve)
            self.animation.addAnimation(self.fade)

    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = float(value)
        self.content.setGeometry(0, round(self._offset), self.width(), self.height())

    offset = QtCore.Property(float, get_offset, set_offset)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.content.setGeometry(0, round(self._offset), self.width(), self.height())

    def start_reveal(self):
        if not self.isVisible():
            return
        self.animation.stop()
        self.set_offset(10.)
        if self.effect is not None:
            self.effect.setOpacity(.25)
        self.motion.setStartValue(10.)
        self.motion.setEndValue(0.)
        if self.fade is not None:
            self.fade.setStartValue(.25)
            self.fade.setEndValue(1.)
        self.animation.start()

    def stop_reveal(self):
        self.animation.stop()
        self.set_offset(0.)
        if self.effect is not None:
            self.effect.setOpacity(1.)


class VisualSettingsDialog(QtWidgets.QDialog):
    """Edit a detached copy of settings; the caller applies only on accept."""
    def __init__(self, image, settings, mode, parent=None, tr=None):
        super().__init__(parent)
        self.tr = tr or (lambda text: text)
        self.mode = mode if mode in ('fishing', 'ruins') else 'fishing'
        self.initial = deepcopy(settings)
        self.layout_mode = settings.get('layout_mode', 'auto')
        if self.layout_mode not in ('auto', 'manual'):
            self.layout_mode = 'auto'
        self._profiles = self._profile_values(settings)
        self._fields = {}
        self._field_grids = []
        self._points = self._point_values(self._profiles[self.layout_mode])
        self.reset_device_calibration = False
        self._reset_auto_requested = False
        self.setWindowTitle(self.tr('遺跡探險設定' if self.mode == 'ruins' else '釣魚設定'))
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(620, 500)
        self.resize(1040, 760)
        self._build(image, self._profiles[self.layout_mode])

    @staticmethod
    def _profile_defaults():
        defaults = deepcopy(PHONE_DEFAULTS)
        defaults.update(deepcopy(RUINS_DEFAULTS))
        defaults['ruins_points'] = {key: list(value) for key, value in RuinsController.POINTS.items()}
        return {key: deepcopy(defaults[key]) for key in LAYOUT_PROFILE_KEYS}

    @classmethod
    def _profile_values(cls, settings):
        base = cls._profile_defaults()
        for key in LAYOUT_PROFILE_KEYS:
            if key in settings:
                base[key] = deepcopy(settings[key])
        original = settings.get('layout_profiles', {})
        if not isinstance(original, dict):
            original = {}
        profiles = {}
        for mode in ('auto', 'manual'):
            values = original.get(mode, {})
            profiles[mode] = deepcopy(base)
            if isinstance(values, dict):
                for key in LAYOUT_PROFILE_KEYS:
                    if key in values:
                        profiles[mode][key] = deepcopy(values[key])
        active = settings.get('layout_mode', 'auto')
        if active in profiles:
            for key in LAYOUT_PROFILE_KEYS:
                if key in settings:
                    profiles[active][key] = deepcopy(settings[key])
        # Older profiles may contain a multi-tap count; keep the schema while
        # enforcing the single-tap action now used by the controller.
        for profile in profiles.values():
            profile['ruins_tap_max'] = 1
        return profiles

    def _point_values(self, settings):
        if self.mode == 'fishing':
            return {'FISHING': [float(settings.get('tap_x', .5)),
                                float(settings.get('tap_y', .855))]}
        result = {key: list(point) for key, point in RuinsController.POINTS.items()}
        for key, point in settings.get('ruins_points', {}).items():
            if key in result and isinstance(point, (list, tuple)) and len(point) == 2:
                result[key] = list(map(float, point))
        return result

    def _label(self, text, name=None):
        label = QtWidgets.QLabel(self.tr(text))
        label.setWordWrap(True)
        if name: label.setObjectName(name)
        return label

    def _build(self, image, settings):
        self.setStyleSheet('''
            QDialog {font-family:"Microsoft JhengHei UI"; color:#302b40; font-size:13px;}
            QFrame#visualShell {background:#f5f3f7; border-radius:26px;}
            QFrame#previewPanel {background:#e5e0eb; border-radius:22px;}
            QLabel {background:transparent; color:#302b40;}
            QLabel#dialogTitle {font-family:"Noto Serif TC"; font-size:24px; font-weight:700;}
            QLabel#sectionTitle {font-family:"Noto Serif TC"; font-size:17px; font-weight:700;}
            QLabel#muted {color:#70697c; font-size:12px;}
            QLabel#settingValue {color:#5f4e87; font-weight:700;}
            QPushButton {background:#eae6ef; color:#433c55; border:0; border-radius:15px; padding:10px 15px; font-weight:700; min-height:22px;}
            QPushButton:hover {background:#ddd6e7;}
            QPushButton:focus {border:2px solid #8c79ad;}
            QPushButton#primary, QPushButton:checked {background:#5f4e87; color:#fff;}
            QCheckBox {spacing:8px; padding:4px;}
            QCheckBox::indicator {width:18px; height:18px; border-radius:9px; background:#d5cede;}
            QCheckBox::indicator:checked {background:#776497; border:4px solid #cfc5dc;}
            QSlider::groove:horizontal {height:6px; border-radius:3px; background:#dad3e2;}
            QSlider::sub-page:horizontal {background:#80709e; border-radius:3px;}
            QSlider::handle:horizontal {background:#5f4e87; border:3px solid #f5f3f7; width:18px; margin:-8px 0; border-radius:11px;}
            QScrollArea {background:transparent; border:0;}
            QWidget#qt_scrollarea_viewport, QWidget#visualPanel {background:transparent;}
            QScrollBar:vertical {background:transparent; width:12px; margin:2px;}
            QScrollBar::handle:vertical {background:#c1b7cc; border-radius:4px; min-height:32px;}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height:0;}
        ''')
        outside = QtWidgets.QVBoxLayout(self)
        outside.setContentsMargins(0, 0, 0, 0)
        shell = QtWidgets.QFrame()
        shell.setObjectName('visualShell')
        outside.addWidget(shell)
        layout = QtWidgets.QVBoxLayout(shell)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        header = DragHeader()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(self._label('遺跡探險設定' if self.mode == 'ruins' else '釣魚設定', 'dialogTitle'), 1)
        close = CloseButton()
        close.setAccessibleName(self.tr('取消'))
        close.clicked.connect(self.reject)
        header_layout.addWidget(close)
        layout.addWidget(header)
        self.animated_body = AnimatedBody()
        self.body = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight,
                                         self.animated_body.content)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(20)
        layout.addWidget(self.animated_body, 1)

        self.left = QtWidgets.QFrame()
        self.left.setObjectName('previewPanel')
        self.left.setMinimumWidth(210)
        self.left.setMaximumWidth(380)
        left = QtWidgets.QVBoxLayout(self.left)
        left.setContentsMargins(16, 16, 16, 16)
        left.setSpacing(8)
        left.addWidget(self._label('畫面與操作位置', 'sectionTitle'))
        help_text = self._label('拖曳角落與圓點', 'muted')
        help_text.setWordWrap(True)
        left.addWidget(help_text)
        key = 'FISHING' if self.mode == 'fishing' else 'ADVANCE'
        self.editor = PhoneEditor(image, settings.get('crop', [0, 0, 1, 1]), self._points, key, self.tr)
        left.addWidget(self.editor, 1)
        self.body.addWidget(self.left, 2)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        panel = QtWidgets.QWidget()
        panel.setObjectName('visualPanel')
        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 3, 8, 0)
        panel_layout.setSpacing(15)
        self.scroll.setWidget(panel)
        self.body.addWidget(self.scroll, 3)
        panel_layout.addWidget(self._label('設定模式', 'sectionTitle'))
        self.layout_choices = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)
        self.layout_choices.setSpacing(8)
        self.layout_buttons = {}
        layout_group = QtWidgets.QButtonGroup(self)
        layout_group.setExclusive(True)
        for layout_mode, title in (('auto', '自動學習'), ('manual', '手動設定')):
            button = QtWidgets.QPushButton(self.tr(title))
            button.setCheckable(True)
            button.setChecked(layout_mode == self.layout_mode)
            button.clicked.connect(lambda checked=False, name=layout_mode: self.switch_layout_mode(name))
            layout_group.addButton(button)
            self.layout_buttons[layout_mode] = button
            self.layout_choices.addWidget(button, 1)
        panel_layout.addLayout(self.layout_choices)
        panel_layout.addWidget(self._label('兩種模式各自保留設定', 'muted'))
        panel_layout.addWidget(self._label('觸控位置', 'sectionTitle'))
        self.reset_calibration_button = QtWidgets.QPushButton(self.tr('重設自動校正'))
        self.reset_calibration_button.setCheckable(True)
        self.reset_calibration_button.toggled.connect(self._toggle_calibration_reset)
        self.reset_calibration_button.setEnabled(self.layout_mode == 'auto')
        if self.mode == 'ruins':
            choices = QtWidgets.QGridLayout()
            choices.setSpacing(8)
            self.point_grid = choices
            self.point_buttons = {}
            group = QtWidgets.QButtonGroup(self)
            group.setExclusive(True)
            for i, (point, label) in enumerate(POINT_LABELS):
                button = QtWidgets.QPushButton(self.tr(label))
                button.setCheckable(True)
                button.setChecked(point == key)
                button.clicked.connect(lambda checked=False, name=point: self.editor.set_point_key(name))
                group.addButton(button)
                self.point_buttons[point] = button
                choices.addWidget(button, i//3, i%3)
            panel_layout.addLayout(choices)
            panel_layout.addWidget(self._label('探險策略', 'sectionTitle'))
            panel_layout.addWidget(self._label('勝率低於門檻時撤離', 'muted'))
            specs = (
                ('ruins_normal_threshold', '一般寶藏勝率門檻', 0, 100, 1, '%'),
                ('ruins_red_threshold', '紅色寶藏勝率門檻', 0, 100, 1, '%'),
            )
            self._add_fields(panel_layout, specs, settings, RUINS_DEFAULTS)
        else:
            panel_layout.addWidget(self._label('釣魚按鈕', 'muted'))
            modes = self.modes = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight)
            self.continuous = QtWidgets.QCheckBox(self.tr('持續釣魚'))
            self.continuous.setChecked(bool(settings.get('continuous', True)))
            self.humanize = QtWidgets.QCheckBox(self.tr('模擬手動操作'))
            self.humanize.setChecked(bool(settings.get('humanize', True)))
            modes.addWidget(self.continuous)
            modes.addWidget(self.humanize)
            modes.addStretch(1)
            panel_layout.addLayout(modes)
            panel_layout.addWidget(self._label('釣魚上限', 'sectionTitle'))
            self._add_fields(panel_layout, (
                ('max_casts', '下鉤上限', 1, 10000, 1, ''),
                ('max_session_minutes', '時間上限（分鐘）', 1, 1440, 1, ''),
            ), settings, PHONE_DEFAULTS)
            panel_layout.addWidget(self._label('持續釣魚開啟時，上限不生效', 'muted'))
            self.continuous.toggled.connect(self._update_limit_enabled)
            self._update_limit_enabled(self.continuous.isChecked())
            panel_layout.addWidget(self._label('進階時序', 'sectionTitle'))
            self._add_fields(panel_layout, (
                ('input_latency_ms', '觸控延遲補償（毫秒）', 0, 500, 1, ''),
                ('stream_delay_ms', '串流延遲估計（毫秒）', 0, 500, 1, ''),
                ('timing_uncertainty_ms', '時序不確定餘量（毫秒）', 0, 150, 1, ''),
                ('capture_interval', '辨識間隔（秒）', .005, 1, .005, ''),
                ('result_wait_s', '收下首次等待（秒）', .05, 10, .05, ''),
                ('result_retry_s', '收下重試間隔（秒）', .15, 5, .05, ''),
            ), settings, PHONE_DEFAULTS)
        panel_layout.addWidget(self.reset_calibration_button, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        panel_layout.addStretch(1)
        foot = QtWidgets.QHBoxLayout()
        self.note = self._label('儲存後立即套用', 'muted')
        self.note.setWordWrap(True)
        foot.addWidget(self.note, 1)
        reset = QtWidgets.QPushButton(self.tr('恢復預設值'))
        reset.clicked.connect(self.reset_defaults)
        self.reset_button = reset
        cancel = QtWidgets.QPushButton(self.tr('取消'))
        cancel.clicked.connect(self.reject)
        self.cancel_button = cancel
        save = QtWidgets.QPushButton(self.tr('儲存設定'))
        save.setObjectName('primary')
        save.setToolTip(self.tr('儲存後立即套用'))
        save.clicked.connect(self.accept)
        self.save_button = save
        foot.addWidget(reset)
        foot.addWidget(cancel)
        foot.addWidget(save)
        layout.addLayout(foot)

    def _add_fields(self, layout, specs, settings, defaults):
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)
        fields = []
        for i, (key, label, low, high, step, suffix) in enumerate(specs):
            value = settings.get(key, defaults[key])
            options = None
            if key == 'max_casts':
                options = list(range(1, 101)) + list(range(105, 501, 5)) + list(range(520, 2001, 20)) + list(range(2100, 10001, 100))
            elif key == 'max_session_minutes':
                options = list(range(1, 121)) + list(range(125, 601, 5)) + list(range(615, 1441, 15))
            field = SliderField(label, value, low, high, step, suffix, self.tr, options=options)
            self._fields[key] = field
            fields.append(field)
            grid.addWidget(field, i//2, i%2)
        layout.addLayout(grid)
        self._field_grids.append((grid, fields))

    @staticmethod
    def _reflow(grid, widgets, columns):
        for index, widget in enumerate(widgets):
            row, column, _, _ = grid.getItemPosition(grid.indexOf(widget))
            if (row, column) != (index//columns, index%columns):
                grid.removeWidget(widget)
                grid.addWidget(widget, index//columns, index%columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, 'body'): return
        compact = self.width() < 700 and self.width()/max(1, self.height()) < .85
        direction = (QtWidgets.QBoxLayout.Direction.TopToBottom if compact
                     else QtWidgets.QBoxLayout.Direction.LeftToRight)
        if self.body.direction() != direction:
            self.body.setDirection(direction)
        field_columns = 1 if self.width() < 820 else 2
        self.layout_choices.setDirection(QtWidgets.QBoxLayout.Direction.TopToBottom if self.width() < 930
                                         else QtWidgets.QBoxLayout.Direction.LeftToRight)
        if hasattr(self, 'modes'):
            self.modes.setDirection(QtWidgets.QBoxLayout.Direction.TopToBottom if self.width() < 820
                                    else QtWidgets.QBoxLayout.Direction.LeftToRight)
        for grid, widgets in self._field_grids:
            self._reflow(grid, widgets, field_columns)
        if hasattr(self, 'point_grid'):
            self._reflow(self.point_grid, list(self.point_buttons.values()),
                         2 if self.width() < 850 else 3)
        self.note.setVisible(self.width() >= 760)
        self.left.setMaximumWidth(16777215 if compact else 380)
        self.left.setMaximumHeight(420 if compact else 16777215)
        self.left.setMinimumHeight(290 if compact else 0)
        self.editor.setMinimumHeight(160 if compact else 240)

    def showEvent(self, event):
        super().showEvent(event)
        # Defer until the layout has final bounds; the header and actions never move.
        QtCore.QTimer.singleShot(0, self.animated_body.start_reveal)

    def hideEvent(self, event):
        self.animated_body.stop_reveal()
        super().hideEvent(event)

    def result_settings(self):
        self._cache_profile()
        result = deepcopy(self.initial)
        result.update(deepcopy(self._profiles[self.layout_mode]))
        result['layout_mode'] = self.layout_mode
        result['layout_profiles'] = deepcopy(self._profiles)
        return result

    def _cache_profile(self):
        profile = self._profiles[self.layout_mode]
        profile.update({key: field.value() for key, field in self._fields.items()})
        profile['crop'] = list(self.editor.crop)
        if self.mode == 'fishing':
            profile['tap_x'], profile['tap_y'] = self.editor.points['FISHING']
            profile['continuous'] = self.continuous.isChecked()
            profile['humanize'] = self.humanize.isChecked()
        else:
            profile['ruins_points'] = deepcopy(self.editor.points)

    def _load_profile(self):
        profile = self._profiles[self.layout_mode]
        for key, field in self._fields.items():
            field.set_value(profile[key])
        self.editor.set_values(profile['crop'], self._point_values(profile))
        if self.mode == 'fishing':
            self.continuous.setChecked(profile['continuous'])
            self.humanize.setChecked(profile['humanize'])
            self._update_limit_enabled(profile['continuous'])

    def switch_layout_mode(self, mode):
        if mode not in ('auto', 'manual') or mode == self.layout_mode:
            return
        self._cache_profile()
        self.layout_mode = mode
        self.layout_buttons[mode].setChecked(True)
        self._load_profile()
        self.reset_calibration_button.setEnabled(mode == 'auto')
        self.reset_device_calibration = mode == 'auto' and self._reset_auto_requested

    def _toggle_calibration_reset(self, checked):
        self._reset_auto_requested = checked
        self.reset_device_calibration = checked and self.layout_mode == 'auto'
        self.reset_calibration_button.setText(self.tr('將重設自動校正' if checked else '重設自動校正'))

    def _update_limit_enabled(self, continuous):
        self._fields['max_casts'].setEnabled(not continuous)
        self._fields['max_session_minutes'].setEnabled(not continuous)

    def reset_defaults(self):
        self._profiles[self.layout_mode] = self._profile_defaults()
        self._load_profile()
