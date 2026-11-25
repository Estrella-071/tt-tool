# SPDX-License-Identifier: GPL-3.0-only
"""Rounded, task-focused Qt interface for the existing ADB phone runner."""
import json
import queue
import shutil
import sys
import threading
import time
from functools import lru_cache
from collections import deque
from copy import deepcopy
from pathlib import Path
import cv2
from PySide6 import QtCore, QtGui, QtWidgets
from fisher.adb import Adb, PHONE_DEFAULTS, validate_phone_settings
from fisher.adb_help import BRANDS, guide_for
from fisher.config import DATA_ROOT
from fisher.phone_runtime import PhoneRunner
from fisher.device_profiles import DeviceProfileStore
from fisher.i18n import LANGUAGE_OPTIONS, translate
from fisher.maintenance import Maintenance
from fisher.ruins import RuinsController
from fisher.ruins_runtime import RuinsRunner
from fisher.visual_settings import VisualSettingsDialog

STYLE = '''
QWidget { background:transparent; color:#302e3d; font-family:"Microsoft JhengHei UI"; font-size:14px; }
QWidget#shell {background:#e9e6ee; border-radius:28px;}
QFrame#card {background:#f7f5f8; border-radius:24px;}
QFrame#previewCard {background:#e0dbe8; border-radius:24px;}
QFrame#stat {background:#e9e6ee; border-radius:22px;}
QFrame#hero {background:#302b40; border-radius:24px;}
QLabel#heroTitle {color:#ffffff; font-family:"Noto Serif TC"; font-size:23px; font-weight:700; background:transparent;}
QLabel#heroDetail {color:#ddd8e8; font-size:13px; background:transparent;}
QLabel#heading {font-family:"Noto Serif TC"; font-size:18px; font-weight:700; background:transparent;}
QLabel#sectionTitle {font-size:15px; font-weight:700; color:#51485f; background:transparent;}
QLabel#controlTitle {font-family:"Noto Serif TC"; font-size:32px; font-weight:700; color:#302b40; background:transparent;}
QLabel#controlSubtitle {font-size:15px; color:#625a70; background:transparent;}
QLabel#statValue {font-family:"Noto Serif TC"; font-size:32px; font-weight:700; color:#514365; background:transparent;}
QLabel#muted {color:#787386; font-size:12px; background:transparent;}
QLabel#brand {font-family:"Noto Serif TC"; font-size:27px; font-weight:800; color:#302b40; background:transparent;}
QLabel#preview {background:#242231; color:#cbc5d7; border-radius:18px;}
QPushButton {background:#edeaf2; color:#423b54; border:0; border-radius:16px; padding:11px 18px; font-weight:700; min-height:20px;}
QPushButton:focus {border:2px solid #8c79ad;}
QPushButton:disabled {background:#efedf1; color:#aaa5b2;}
QPushButton#modeSelected {background:#5f4e87; color:#ffffff;}
QPushButton#primary,QPushButton#fishingPrimary {background:#5f4e87; color:#ffffff;}
QPushButton#primary:disabled,QPushButton#fishingPrimary:disabled {background:#dedbe2; color:#aaa5b2;}
QPushButton#fishingPrimary,QPushButton#fishingSecondary {min-height:34px;}
QPushButton#windowControl {background:transparent; border:0; border-radius:20px; padding:0; min-height:0;}
QPushButton#windowControl:focus {border:2px solid #8c79ad;}
QPushButton#danger {background:#f1edf1; color:#725768;}
QPushButton#usbHelp {background:#454055; color:#f6f3fc; padding:4px 12px; border-radius:12px; font-weight:600;}
QComboBox,QLineEdit,QDoubleSpinBox,QSpinBox {background:#f1eff4; border:2px solid transparent; border-radius:18px; padding:8px 12px; min-height:20px; selection-background-color:#b9abc9;}
QComboBox:focus,QLineEdit:focus,QDoubleSpinBox:focus,QSpinBox:focus {border:2px solid #8c79ad;}
QDoubleSpinBox::up-button,QDoubleSpinBox::down-button,QSpinBox::up-button,QSpinBox::down-button {width:0; border:0;}
QComboBox::drop-down {border:0; width:30px;}
QComboBox#disclosure::down-arrow {image:none; width:0; height:0;}
QComboBox QAbstractItemView {background:#ffffff; border:0; border-radius:18px; padding:8px; selection-background-color:#e5dfed; outline:0;}
QCheckBox {background:transparent; spacing:10px; padding:5px 0;}
QCheckBox::indicator {width:22px; height:22px; border-radius:11px; background:#ded9e4;}
QCheckBox::indicator:checked {background:#776497; border:5px solid #d8cbe8;}
QTabWidget::pane {border:0; background:#f5f3f7; border-radius:18px; top:-1px;}
QTabBar::tab {background:#f1eff4; border:0; border-radius:16px; padding:9px 19px; margin-right:7px; color:#615a6c;}
QTabBar::tab:selected {background:#6b5d91; color:#ffffff; font-weight:700;}
QScrollArea {border:0; background:transparent;}
QScrollBar:vertical {background:transparent; width:12px; margin:2px;}
QScrollBar::handle:vertical {background:#c6becf; border-radius:4px; min-height:30px;}
QScrollBar::handle:vertical:disabled {background:transparent;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent; border:0;}
QToolTip {background:#302b40; color:white; border:0; border-radius:10px; padding:8px;}
QMenu {background:#f5f3f7; color:#302b40; border:1px solid #d8d1e1; border-radius:16px; padding:8px;}
QMenu::item {padding:9px 28px 9px 18px; border-radius:10px;}
QMenu::item:selected {background:#e3dceb;}
QMenu::indicator:checked {background:#6b5d91; border-radius:5px; width:10px; height:10px;}
'''

class AnimatedButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._highlight=0.0
        self.anim = QtCore.QPropertyAnimation(self, b'highlight', self)
        self.anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
    def get_highlight(self):return self._highlight
    def set_highlight(self,value):self._highlight=value;self.update()
    highlight=QtCore.Property(float,get_highlight,set_highlight)
    def transition(self, value, duration=180):
        self.anim.stop();self.anim.setDuration(duration);self.anim.setStartValue(self._highlight);self.anim.setEndValue(value);self.anim.start()
    def enterEvent(self, event):
        self.transition(.15);super().enterEvent(event)
    def leaveEvent(self, event):
        self.transition(0, 240);super().leaveEvent(event)
    def mousePressEvent(self, event):
        self.transition(.25, 100);super().mousePressEvent(event)
    def mouseReleaseEvent(self, event):
        self.transition(.15 if self.underMouse() else 0, 200);super().mouseReleaseEvent(event)
    def paintEvent(self,event):
        super().paintEvent(event)
        if self.isEnabled() and self._highlight>0:
            p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            color=QtGui.QColor('#ffffff' if self.objectName() in ('primary','fishingPrimary') else '#403450');color.setAlphaF(self._highlight)
            p.setPen(QtCore.Qt.PenStyle.NoPen);p.setBrush(color);p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(1,1,-1,-1),16,16)

class WindowButton(AnimatedButton):
    """Uniform, accessible window controls drawn with one stroke style."""
    def __init__(self,kind,action):
        super().__init__('');self.kind=kind;self.expanded=False;self.setObjectName('windowControl');self.setFixedSize(40,40);self.setAccessibleName({'minimize':'最小化','maximize':'最大化或還原','close':'關閉視窗'}[kind]);self.setToolTip(self.accessibleName());self.clicked.connect(action)
    def setExpanded(self,value):self.expanded=value;self.update()
    def paintEvent(self,event):
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        color=QtGui.QColor('#403450');color.setAlphaF(self._highlight);p.setBrush(color);p.setPen(QtGui.QPen(QtGui.QColor('#8c79ad'),2) if self.hasFocus() else QtCore.Qt.PenStyle.NoPen);p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(2,2,-2,-2),18,18)
        p.setPen(QtGui.QPen(QtGui.QColor('#51485f'),1.6,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap,QtCore.Qt.PenJoinStyle.RoundJoin))
        if self.kind=='minimize':p.drawLine(QtCore.QPointF(15,21),QtCore.QPointF(25,21))
        elif self.kind=='close':p.drawLine(QtCore.QPointF(16,16),QtCore.QPointF(24,24));p.drawLine(QtCore.QPointF(24,16),QtCore.QPointF(16,24))
        elif self.expanded:p.drawRoundedRect(QtCore.QRectF(14,17,9,9),1,1);p.drawLine(QtCore.QPointF(18,14),QtCore.QPointF(26,14));p.drawLine(QtCore.QPointF(26,14),QtCore.QPointF(26,22))
        else:p.drawRoundedRect(QtCore.QRectF(15,15,10,10),1,1)

class DisclosureComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('disclosure')

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        color = '#675b7b' if self.isEnabled() else '#a49cad'
        painter.setPen(QtGui.QPen(QtGui.QColor(color), 1.8,
                                 QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap))
        x, y = self.width() - 18, self.height() / 2
        painter.drawLine(QtCore.QPointF(x-4, y-2), QtCore.QPointF(x, y+2))
        painter.drawLine(QtCore.QPointF(x, y+2), QtCore.QPointF(x+4, y-2))

@lru_cache(maxsize=512)
def traditional_text(text):
    """Convert controller messages at the Windows UI boundary."""
    if sys.platform!='win32' or not text:return text
    import ctypes
    mapper=ctypes.windll.kernel32.LCMapStringEx
    length=mapper('zh-TW',0x04000000,text,-1,None,0,None,None,0)
    if not length:return text
    result=ctypes.create_unicode_buffer(length)
    return result.value if mapper('zh-TW',0x04000000,text,-1,result,length,None,None,0) else text

class AnimatedSwitch(QtWidgets.QCheckBox):
    """Accessible checkbox semantics with a custom spring-animated switch."""
    def __init__(self, text):
        super().__init__(text);self._position=0.0
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.motion=QtCore.QPropertyAnimation(self,b'position',self)
        self.motion.setDuration(180);self.motion.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.toggled.connect(self.animate)
    def get_position(self):return self._position
    def set_position(self,value):self._position=value;self.update()
    position=QtCore.Property(float,get_position,set_position)
    def animate(self,checked):
        self.motion.stop();self.motion.setStartValue(self._position);self.motion.setEndValue(1.0 if checked else 0.0);self.motion.start()
    def sizeHint(self):
        metrics=self.fontMetrics();return QtCore.QSize(54+metrics.horizontalAdvance(self.text()),36)
    def hitButton(self,pos):return self.rect().contains(pos)
    def paintEvent(self,event):
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        y=(self.height()-26)/2;track=QtCore.QRectF(0,y,42,26)
        progress=max(0.0,min(1.0,self._position));off=QtGui.QColor('#d8d3df');on=QtGui.QColor('#776497');color=QtGui.QColor(*(round(off.getRgb()[i]+(on.getRgb()[i]-off.getRgb()[i])*progress) for i in range(3)));p.setPen(QtCore.Qt.PenStyle.NoPen);p.setBrush(color);p.drawRoundedRect(track,13,13)
        p.setBrush(QtGui.QColor('#ffffff'));p.drawEllipse(QtCore.QPointF(13+16*self._position,y+13),9,9)
        if self.hasFocus():
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush);p.setPen(QtGui.QPen(QtGui.QColor('#8c79ad'),2));p.drawRoundedRect(track.adjusted(-2,-2,2,2),15,15)
        p.setPen(QtGui.QColor('#302e3d' if self.isEnabled() else '#aaa5b2'));p.drawText(QtCore.QRectF(54,0,self.width()-54,self.height()),QtCore.Qt.AlignmentFlag.AlignVCenter,self.text())

class PhonePreview(QtWidgets.QWidget):
    """Render and measure the whole device frame inside a proportional bezel."""
    activated=QtCore.Signal()
    def __init__(self):
        super().__init__();self.image=QtGui.QImage();self.message='連線後顯示手機畫面';self.setMinimumSize(180,180)
        self.paint_times=deque(maxlen=90);self.frame_id=0;self.painted_id=-1;self._reveal=0.0
        self.reveal=QtCore.QPropertyAnimation(self,b'revealProgress',self);self.reveal.setDuration(720);self.reveal.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor);self.setToolTip('點擊放大即時預覽');self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus);self.setAccessibleName('放大手機預覽')
    def get_reveal(self):return self._reveal
    def set_reveal(self,value):self._reveal=value;self.update()
    revealProgress=QtCore.Property(float,get_reveal,set_reveal)
    def clear(self):self.image=QtGui.QImage();self.paint_times.clear();self._reveal=0;self.update()
    def setText(self,text):self.message=text;self.update()
    def setImage(self,image):
        first=self.image.isNull();self.image=image;self.frame_id+=1
        if first:self.reveal.stop();self.reveal.setStartValue(0.0);self.reveal.setEndValue(1.0);self.reveal.start()
        self.update()
    def mousePressEvent(self,event):
        if event.button()==QtCore.Qt.MouseButton.LeftButton and not self.image.isNull():self.activated.emit()
        super().mousePressEvent(event)
    def keyPressEvent(self,event):
        if event.key() in (QtCore.Qt.Key.Key_Return,QtCore.Qt.Key.Key_Enter,QtCore.Qt.Key.Key_Space) and not self.image.isNull():
            self.activated.emit();event.accept();return
        super().keyPressEvent(event)
    def paintEvent(self,event):
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing);p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        p.setPen(QtGui.QPen(QtGui.QColor('#8c79ad'),2) if self.hasFocus() else QtCore.Qt.PenStyle.NoPen);p.setBrush(QtGui.QColor('#d6d0e1'));p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(1,1,-1,-1),24,24)
        aspect=self.image.width()/self.image.height() if not self.image.isNull() else 360/800
        h=min(float(self.height()-38),(self.width()-38)/aspect);w=h*aspect
        scale=.94+.06*self._reveal if not self.image.isNull() else 1.0
        w*=scale;h*=scale
        screen=QtCore.QRectF((self.width()-w)/2,(self.height()-h)/2,w,h)
        r=screen.adjusted(-5,-5,5,5)
        p.setBrush(QtGui.QColor('#302b40'));p.drawRoundedRect(r,36,36)
        path=QtGui.QPainterPath();path.addRoundedRect(screen,31,31)
        p.save();p.setClipPath(path)
        if self.image.isNull():
            p.fillRect(screen, QtGui.QColor('#242231'))
            p.setPen(QtGui.QColor('#cbc5d7'))
            text_layout = QtGui.QTextOption(QtCore.Qt.AlignmentFlag.AlignCenter)
            text_layout.setWrapMode(QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
            p.drawText(screen.adjusted(10, 4, -10, -4), self.message, text_layout)
        else:
            p.setOpacity(.65+.35*self._reveal);p.drawImage(screen,self.image)
            if self.frame_id != self.painted_id:
                self.painted_id=self.frame_id;self.paint_times.append(time.perf_counter())
        p.restore()

class ResizeHandle(QtWidgets.QWidget):
    def __init__(self):super().__init__();self.setFixedSize(28,28);self.setCursor(QtCore.Qt.CursorShape.SizeFDiagCursor)
    def mousePressEvent(self,event):
        if event.button()==QtCore.Qt.MouseButton.LeftButton:self.window().windowHandle().startSystemResize(QtCore.Qt.Edge.RightEdge | QtCore.Qt.Edge.BottomEdge)
    def paintEvent(self,event):
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing);p.setPen(QtGui.QPen(QtGui.QColor('#a69bb7'),3,QtCore.Qt.PenStyle.SolidLine,QtCore.Qt.PenCapStyle.RoundCap));p.drawLine(10,20,20,10);p.drawLine(16,21,21,16)

class FishingWindow(QtWidgets.QMainWindow):
    SCAN_ACTION = 1
    ADB_PATH_ACTION = 2

    def __init__(self, mode='fishing', start_after_connect=False, *, install_root=None):
        super().__init__(); self.setWindowTitle('tt tool · 手機活動助手');self.setMinimumSize(680,600);self.setMaximumSize(3840,2160);screen=QtWidgets.QApplication.primaryScreen().availableGeometry();self.resize(min(1180,screen.width()-40),min(900,screen.height()-40))
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Window);self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground);self.drag_pos=None;self.last_headline='';self.window_expanded=False;self.restore_rect=None
        self.mode=mode if mode in ('fishing','ruins') else 'fishing';self.runner=None;self.devices=[];self.q=queue.SimpleQueue();self.busy=False;self.adb_path='adb';self.frame=None;self.zoom_dialog=None;self.zoom_preview=None;self.auto_connect=True;self.pending_start=start_after_connect
        self.saved=validate_phone_settings(dict(PHONE_DEFAULTS));self.settings_path=DATA_ROOT/'phone_settings.json';self.language_path=DATA_ROOT/'tt_tool_ui.json';self.language='zh_TW';self._last_messages=None
        self.ui_preferences = {}
        self.selected_device = None
        try:
            if self.settings_path.exists():self.saved.update(validate_phone_settings(json.loads(self.settings_path.read_text(encoding='utf-8'))))
        except (OSError,ValueError,TypeError):pass
        try:
            self.ui_preferences = json.loads(self.language_path.read_text(encoding='utf-8'))
            language=self.ui_preferences.get('language','zh_TW')
            if language in dict(LANGUAGE_OPTIONS):self.language=language
            custom_adb = self.ui_preferences.get('adb_path')
            if isinstance(custom_adb, str) and Path(custom_adb).is_file():
                self.adb_path = custom_adb
        except (OSError,ValueError,TypeError,AttributeError):
            self.ui_preferences = {}
        self.draft_settings=deepcopy(self.saved);self.pending_profile_reset=set()
        self.maintenance = Maintenance(self, install_root)
        self.build();self.timer=QtCore.QTimer(self);self.timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer);self.timer.timeout.connect(self.poll);self.timer.start(12);self.discovery_timer=QtCore.QTimer(self);self.discovery_timer.timeout.connect(self.scan_if_needed);self.discovery_timer.start(5000);QtCore.QTimer.singleShot(150,self.refresh)
    def button(self,text,fn,kind=None):
        b=AnimatedButton(self.tr(text));b.setProperty('i18n_source',text);b.clicked.connect(fn)
        if kind:b.setObjectName(kind)
        return b
    def card(self):
        w=QtWidgets.QFrame();w.setObjectName('card');return w
    def label(self,text,name=None):
        w=QtWidgets.QLabel(self.tr(text));w.setProperty('i18n_source',text)
        if name:w.setObjectName(name)
        w.setWordWrap(True);return w
    def tr(self,text):
        source=str(text or '')
        translated=translate(source,self.language)
        if self.language=='zh_TW':return traditional_text(translated)
        return translated if translated!=source else translate(traditional_text(source),self.language)
    def set_text(self,widget,text):
        if (widget is getattr(self,'headline',None) or widget is getattr(self,'detail',None)) and not getattr(self,'_rendering_status',False):
            self._last_messages=None
        if widget.property('i18n_source')!=text:widget.setProperty('i18n_source',text)
        value=self.tr(text)
        if widget.text()!=value:widget.setText(value)
    def build(self):
        base=QtWidgets.QWidget();base.setObjectName('shell');self.setCentralWidget(base);page=self.page=QtWidgets.QVBoxLayout(base);page.setContentsMargins(28,24,28,24);page.setSpacing(18)
        head=QtWidgets.QHBoxLayout();head.setSpacing(6);head.addWidget(self.label('tt tool','brand'));head.addWidget(self.label('手機活動助手','muted'));head.addStretch();head.addWidget(self.label('ADB  ·  USB','muted'));head.addSpacing(12);head.addWidget(WindowButton('minimize',self.showMinimized));self.max_button=WindowButton('maximize',self.toggle_maximize);head.addWidget(self.max_button);head.addWidget(WindowButton('close',self.close));page.addLayout(head)
        hero=QtWidgets.QFrame();hero.setObjectName('hero');hl=self.hero_layout=QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight,hero);hl.setContentsMargins(24,18,24,18);hl.setSpacing(14)
        status_block=QtWidgets.QWidget();status_layout=QtWidgets.QVBoxLayout(status_block);status_layout.setContentsMargins(0,0,0,0);status_layout.setSpacing(4)
        self.headline=self.label('連接你的手機','heroTitle');self.status_effect=QtWidgets.QGraphicsOpacityEffect(self.headline);self.headline.setGraphicsEffect(self.status_effect);self.status_effect.setOpacity(1);self.status_animation=QtCore.QPropertyAnimation(self.status_effect,b'opacity',self);self.status_animation.setDuration(650);self.status_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic);self.status_slide=QtCore.QPropertyAnimation(self.headline,b'pos',self);self.status_slide.setDuration(650);self.status_slide.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic);self.detail=self.label('開啟 USB 偵錯並允許這台電腦','heroDetail');status_layout.addWidget(self.headline);status_layout.addWidget(self.detail)
        self.usb_help = self.button('USB 連線教學', self.show_usb_help, 'usbHelp')
        status_layout.addWidget(self.usb_help, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        hl.addWidget(status_block,1)
        device_block=QtWidgets.QWidget();device_line=QtWidgets.QHBoxLayout(device_block);device_line.setContentsMargins(0,0,0,0);device_line.setSpacing(10);self.device=DisclosureComboBox();self.device.setMinimumWidth(150);device_line.addWidget(self.device,1)
        self.device.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.device.activated.connect(self.select_device_item)
        self.connect_btn=self.button('連線手機',self.connect_device,'primary');device_line.addWidget(self.connect_btn);self.disconnect_btn=self.button('中斷連線',self.disconnect);device_line.addWidget(self.disconnect_btn);hl.addWidget(device_block,2);page.addWidget(hero)
        self.body_scroll=QtWidgets.QScrollArea();self.body_scroll.setWidgetResizable(True);self.body_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.body_host=QtWidgets.QWidget();self.body=QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.Direction.LeftToRight,self.body_host);self.body.setContentsMargins(0,0,0,0);self.body.setSpacing(18);self.body_scroll.setWidget(self.body_host);page.addWidget(self.body_scroll,1);body=self.body
        left=self.left=self.card();left.setObjectName('previewCard');left.setMinimumWidth(250);left.setMaximumWidth(360);ll=QtWidgets.QVBoxLayout(left);ll.setContentsMargins(20,20,20,20);ll.setSpacing(12)
        ll.addWidget(self.label('即時畫面','heading'));self.preview_label=PhonePreview();self.preview_message='連線後顯示手機畫面';self.preview_label.activated.connect(self.open_preview);ll.addWidget(self.preview_label,1)
        self.preview=AnimatedSwitch(self.tr('顯示手機預覽'));self.preview.setProperty('i18n_source','顯示手機預覽');self.preview.setChecked(True);self.preview.toggled.connect(self.toggle_preview);ll.addWidget(self.preview);ll.addWidget(self.label('點擊畫面可放大','muted'));body.addWidget(left,1)
        right=self.right=self.card();right_layout=QtWidgets.QVBoxLayout(right);right_layout.setContentsMargins(28,26,28,24);right_layout.setSpacing(10)
        right_scroll=self.right_scroll=QtWidgets.QScrollArea();right_scroll.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,QtWidgets.QSizePolicy.Policy.Ignored);right_scroll.setMinimumSize(0,0);right_scroll.setWidgetResizable(True);right_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff);right_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn);right_content=QtWidgets.QWidget();outer=QtWidgets.QVBoxLayout(right_content);outer.setContentsMargins(0,0,8,0);outer.setSpacing(7);right_scroll.setWidget(right_content);right_layout.addWidget(right_scroll,1)
        mode_line=QtWidgets.QHBoxLayout();mode_line.setSpacing(8)
        self.fishing_mode=self.button('釣魚',lambda:self.switch_mode('fishing'));self.ruins_mode=self.button('遺跡探險',lambda:self.switch_mode('ruins'))
        mode_line.addWidget(self.fishing_mode);mode_line.addWidget(self.ruins_mode);mode_line.addStretch();outer.addLayout(mode_line)
        self.title_spacer=QtWidgets.QSpacerItem(0,30,QtWidgets.QSizePolicy.Policy.Minimum,QtWidgets.QSizePolicy.Policy.Fixed);outer.addItem(self.title_spacer);self.control_title=self.label('釣魚控制','controlTitle');outer.addWidget(self.control_title)
        self.mode_summary=self.label('','controlSubtitle');outer.addWidget(self.mode_summary)
        self.update_mode_summary()
        outer.addSpacing(20);controls=QtWidgets.QHBoxLayout();controls.setSpacing(12);self.start_btn=self.button('開始釣魚',self.toggle_fishing,'fishingPrimary');self.pause_btn=self.button('結束  Esc',self.end,'fishingSecondary');controls.addWidget(self.start_btn,2);controls.addWidget(self.pause_btn,1);outer.addLayout(controls)
        outer.addSpacing(12)
        self.advanced_toggle=self.button('設定  ↗',self.open_settings);self.advanced_toggle.setFixedWidth(160);self.advanced_toggle.setToolTip(self.tr('調整畫面、操作位置與活動設定'));outer.addWidget(self.advanced_toggle,0,QtCore.Qt.AlignmentFlag.AlignLeft)
        self.stats=QtWidgets.QWidget();stats=QtWidgets.QHBoxLayout(self.stats);stats.setContentsMargins(0,16,0,0);stats.setSpacing(12)
        self.stat_titles=[]
        for title,attr in [('下鉤','cast_count'),('結算','result_count')]:
            card=QtWidgets.QFrame();card.setObjectName('stat');layout=QtWidgets.QVBoxLayout(card);layout.setContentsMargins(20,15,20,15);layout.setSpacing(4);caption=self.label(title,'muted');self.stat_titles.append(caption);layout.addWidget(caption);value=self.label('—','statValue');setattr(self,attr,value);layout.addWidget(value);stats.addWidget(card,1)
        outer.addWidget(self.stats)
        self.entrance=QtCore.QParallelAnimationGroup(self)
        self.slide=QtCore.QPropertyAnimation(left,b'maximumWidth',self);self.slide.setStartValue(290);self.slide.setEndValue(360);self.slide.setDuration(850);self.slide.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic);self.entrance.addAnimation(self.slide)
        self.hero_animation=QtCore.QPropertyAnimation(hero,b'maximumHeight',self);self.hero_animation.setStartValue(120);self.hero_animation.setEndValue(220);self.hero_animation.setDuration(850);self.hero_animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic);self.entrance.addAnimation(self.hero_animation);self.entrance.finished.connect(lambda:self.resizeEvent(QtGui.QResizeEvent(self.size(),self.size())));QtCore.QTimer.singleShot(0,self.entrance.start)
        outer.addStretch(1)
        body.addWidget(right,2)
        self.compact_controls=QtWidgets.QFrame();compact_row=QtWidgets.QHBoxLayout(self.compact_controls);compact_row.setContentsMargins(0,0,0,0);compact_row.setSpacing(10);self.compact_start=self.button('開始釣魚',self.toggle_fishing,'primary');self.compact_pause=self.button('結束',self.end,'danger');compact_row.addWidget(self.compact_start,2);compact_row.addWidget(self.compact_pause,1);page.addWidget(self.compact_controls);self.compact_controls.hide()
        foot=QtWidgets.QHBoxLayout();self.metrics=self.label('等待連線','muted');foot.addWidget(self.metrics,1)
        self.maintenance_button = self.button('工具維護', self.show_maintenance_menu)
        foot.addWidget(self.maintenance_button)
        self.language_button=self.button(dict(LANGUAGE_OPTIONS)[self.language],self.show_language_menu);self.language_button.setToolTip(self.tr('語言'));foot.addWidget(self.language_button)
        foot.addWidget(ResizeHandle());page.addLayout(foot)
        QtGui.QShortcut(QtGui.QKeySequence('Escape'),self,activated=self.end)
        self.space_shortcut=QtGui.QShortcut(QtGui.QKeySequence('Space'),self,activated=self.toggle_fishing)
        self.space_shortcut.setAutoRepeat(False)
        QtWidgets.QApplication.instance().focusChanged.connect(self.update_space_shortcut)
        self.set_connected(False);self.apply_mode();self.retranslate_ui()
    def show_language_menu(self):
        menu = QtWidgets.QMenu(self.language_button)
        for code,name in LANGUAGE_OPTIONS:
            action=menu.addAction(name);action.setCheckable(True);action.setChecked(code==self.language)
            action.triggered.connect(lambda checked=False,value=code:self.set_language(value))
        self.popup_footer_menu(menu, self.language_button)
    def show_maintenance_menu(self):
        menu = self.maintenance.menu(self.maintenance_button)
        self.popup_footer_menu(menu, self.maintenance_button)
    def popup_footer_menu(self, menu, button):
        menu.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.aboutToHide.connect(menu.deleteLater)
        menu.ensurePolished()
        size = menu.sizeHint()
        menu.popup(button.mapToGlobal(QtCore.QPoint(button.width() - size.width(), -size.height() - 5)))
    def set_language(self,language,persist=True):
        if language not in dict(LANGUAGE_OPTIONS):return
        self.language=language;self.retranslate_ui()
        if persist:self.save_ui_preference('language', language)
    def save_ui_preference(self, key, value):
        self.ui_preferences[key] = value
        try:
            self.language_path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.language_path.with_suffix('.tmp')
            tmp.write_text(json.dumps(self.ui_preferences,ensure_ascii=False),encoding='utf-8')
            tmp.replace(self.language_path)
        except OSError as exc:
            self.set_text(self.detail,str(exc))
    def retranslate_ui(self):
        self.setWindowTitle(self.tr('tt tool · 手機活動助手'))
        for widget in self.findChildren(QtWidgets.QLabel)+self.findChildren(QtWidgets.QAbstractButton):
            if widget is self.language_button:continue
            source=widget.property('i18n_source')
            if isinstance(source,str):widget.setText(self.tr(source))
        self.language_button.setText(dict(LANGUAGE_OPTIONS)[self.language]);self.language_button.setToolTip(self.tr('語言'))
        self.maintenance_button.setToolTip(f"{self.tr('工具維護')} · v{self.maintenance.version}")
        self.device.setAccessibleName(self.tr('手機裝置'))
        self.update_device_items()
        self.advanced_toggle.setToolTip(self.tr('調整畫面、操作位置與活動設定'))
        self.preview_label.setToolTip(self.tr('點擊放大即時預覽'));self.preview_label.setAccessibleName(self.tr('放大手機預覽'))
        if self.preview_label.image.isNull():self.preview_label.setText(self.tr(self.preview_message))
        for button in self.findChildren(WindowButton):
            name={'minimize':'最小化','maximize':'最大化或還原','close':'關閉視窗'}[button.kind]
            button.setAccessibleName(self.tr(name));button.setToolTip(self.tr(name))
        self.update_mode_summary();self.update_action_buttons()
        if self._last_messages is not None:self.show_status(*self._last_messages)
    def update_mode_summary(self):
        if self.mode == 'ruins':
            normal=self.draft_settings['ruins_normal_threshold'];red=self.draft_settings['ruins_red_threshold']
            self.set_text(self.mode_summary,f'總勝率低於 {normal}% 撤離  ·  紅色寶藏門檻 {red}%')
            return
        limit='持續釣魚' if self.draft_settings['continuous'] else '依設定上限停止'
        human='模擬手動操作' if self.draft_settings['humanize'] else '標準操作'
        self.set_text(self.mode_summary,f'{limit}  ·  {human}')
    def apply_mode(self):
        ruins=self.mode=='ruins'
        self.set_text(self.control_title,'遺跡探險' if ruins else '釣魚控制')
        self.fishing_mode.setObjectName('' if ruins else 'modeSelected');self.ruins_mode.setObjectName('modeSelected' if ruins else '')
        for button in (self.fishing_mode,self.ruins_mode):button.style().unpolish(button);button.style().polish(button)
        self.set_text(self.stat_titles[0],'已開始' if ruins else '下鉤');self.set_text(self.stat_titles[1],'已完成' if ruins else '結算')
        self.update_mode_summary();self.update_action_buttons()
    def switch_mode(self,mode):
        if mode==self.mode or self.busy:return
        connected=self.runner is not None
        if connected:self.runner.close();self.runner=None;self.set_connected(False)
        self.pending_start=False;self.mode=mode;self.apply_mode();self.cast_count.setText('—');self.result_count.setText('—')
        if connected:self.set_text(self.headline,'正在切換模式');self.set_text(self.detail,'重新連線手機。');self.connect_device()
    def set_connected(self,yes):
        self.connect_btn.setVisible(not yes);self.disconnect_btn.setVisible(yes)
        self.disconnect_btn.setEnabled(yes)
        self.usb_help.setVisible(not yes)
        self.device.setEnabled(not yes)
        self.update_action_buttons()
        self.connect_btn.setEnabled(not yes)
    def update_action_buttons(self):
        connected=self.runner is not None;active=connected and self.runner.active.is_set()
        session=connected and self.runner.session_started.is_set()
        task='探險' if self.mode=='ruins' else '釣魚'
        text=('暫停' if active else '繼續' if session else '開始')+task
        for button in (self.start_btn,self.compact_start):button.setEnabled(connected);self.set_text(button,text)
        for button in (self.pause_btn,self.compact_pause):button.setEnabled(bool(active or session))
    def update_space_shortcut(self,old,new):
        command_buttons = (self.usb_help, self.maintenance_button, self.language_button)
        widget=new
        while widget is not None and widget is not self:
            if isinstance(widget,(QtWidgets.QLineEdit,QtWidgets.QAbstractSpinBox,QtWidgets.QComboBox,AnimatedSwitch,PhonePreview)) or widget in command_buttons:
                self.space_shortcut.setEnabled(False);return
            widget=widget.parentWidget()
        self.space_shortcut.setEnabled(True)
    def apply_settings(self,cfg):
        self.draft_settings=validate_phone_settings(deepcopy(cfg));self.update_mode_summary()
    def settings(self):
        return validate_phone_settings(deepcopy(self.draft_settings))
    def save(self):
        cfg=self.settings();tmp=self.settings_path.with_suffix('.tmp');tmp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(self.settings_path);self.saved=deepcopy(cfg);return cfg
    def open_settings(self):
        image=self.frame
        if self.runner:
            frame,_=self.runner.capture.snapshot()
            if frame is not None:image=frame.image.copy()
        dialog=VisualSettingsDialog(image,self.settings(),self.mode,parent=self,tr=self.tr)
        if dialog.exec()!=QtWidgets.QDialog.DialogCode.Accepted:return
        try:
            self.apply_settings(dialog.result_settings());self.save()
        except (OSError,ValueError,TypeError) as exc:
            self.set_text(self.detail,str(exc));return
        reset_calibration=bool(dialog.reset_device_calibration)
        if self.runner:
            self.runner.reconfigure(self.draft_settings,reset_calibration=reset_calibration)
        elif reset_calibration:
            self.pending_profile_reset.add(self.mode)
        self.set_text(self.detail,'設定已儲存並套用。' if self.runner else '設定已儲存，連線後套用。')
    def background(self,fn,done):
        if self.busy:return
        self.busy=True;self.connect_btn.setEnabled(False)
        def work():
            try:self.q.put((done,fn(),None))
            except Exception as exc:self.q.put((done,None,str(exc)))
        threading.Thread(target=work,daemon=True).start()
    def refresh(self):
        if self.runner:return
        def work():
            adb=Adb(self.adb_path)
            try:return adb.devices()
            finally:adb.close()
        def done(devices):
            self.devices = devices
            authorized = [d.serial for d in devices if d.state == 'device']
            if self.selected_device not in authorized:
                self.selected_device = authorized[0] if len(authorized) == 1 else None
            self.update_device_items()
            if self.auto_connect and len(authorized)==1:
                self.set_text(self.headline,'正在連線手機');self.set_text(self.detail,'正在載入手機畫面。');self.connect_device();return
            self.set_text(self.headline,'選擇手機' if devices else '未偵測到手機')
            if authorized:
                detail = '請選擇已授權的裝置並連線。'
            elif any(device.state == 'unauthorized' for device in devices):
                detail = '解鎖手機，並在提示中允許這台電腦進行 USB 偵錯。'
            else:
                detail = '請確認 USB 資料線、USB 偵錯與授權。'
            self.set_text(self.detail, detail)
        self.background(work,done)
    def update_device_items(self):
        self.device.clear()
        placeholder = '選擇手機' if self.devices else '未偵測到手機'
        self.device.addItem(self.tr(placeholder))
        states = {'device': '可連線', 'unauthorized': '待手機授權', 'offline': '離線'}
        for device in self.devices:
            status = self.tr(states.get(device.state, device.state))
            self.device.addItem(f'{device.serial}  ·  {status}', device.serial)
        self.device.insertSeparator(self.device.count())
        self.device.addItem(self.tr('重新偵測'), self.SCAN_ACTION)
        self.device.addItem(self.tr('ADB 工具位置…'), self.ADB_PATH_ACTION)
        self.device.setCurrentIndex(max(0, self.device.findData(self.selected_device)))
    def select_device_item(self, index):
        value = self.device.itemData(index)
        if isinstance(value, str) or value is None:
            self.selected_device = value
            return
        self.device.setCurrentIndex(max(0, self.device.findData(self.selected_device)))
        if value == self.SCAN_ACTION:
            self.refresh()
        elif value == self.ADB_PATH_ACTION:
            self.show_adb_tools()
    def scan_if_needed(self):
        if (self.auto_connect and not self.runner and not self.busy
                and not self.device.view().isVisible()
                and QtWidgets.QApplication.activeModalWidget() is None):
            self.refresh()
    def connect_device(self):
        serial = self.device.currentData()
        if not any(device.serial == serial and device.state == 'device' for device in self.devices):
            self.set_text(self.detail,'請選擇已授權的手機。');return
        if shutil.which('ffmpeg') is None:
            self.set_text(self.headline,'連線未完成')
            self.set_text(self.detail,'找不到 FFmpeg。加入 PATH 後重新開啟 tt tool。')
            return
        try:cfg=self.save()
        except (ValueError,OSError) as exc:self.set_text(self.detail,str(exc));return
        def work():
            adb=Adb(self.adb_path,serial)
            try:return adb.capture(),adb.foreground()
            finally:adb.close()
        def done(result):
            frame,package=result;self.frame=frame.image
            if frame.image.shape[0]<frame.image.shape[1]:self.pending_start=False;self.set_text(self.detail,'請將手機轉為直向。');return
            if self.mode in self.pending_profile_reset:
                DeviceProfileStore().clear(serial,frame.image.shape[:2],self.mode,cfg['crop']);self.pending_profile_reset.discard(self.mode)
            self.runner=(RuinsRunner if self.mode=='ruins' else PhoneRunner)(self.adb_path,serial,cfg,frame.image.shape[:2],package);self.runner.full_preview.set();self.runner.start();self.toggle_preview(self.preview.isChecked());self.set_connected(True);self.set_text(self.headline,'手機已連線');self.set_text(self.detail,'畫面已就緒，可以開始探險。' if self.mode=='ruins' else '畫面已就緒，可以開始釣魚。')
            if self.pending_start:self.pending_start=False;self.runner.arm(False)
        self.background(work,done)
    def toggle_fishing(self):
        if self.runner and self.runner.active.is_set():self.pause()
        else:self.start()
    def start(self):
        if not self.runner or self.runner.active.is_set():return
        if self.runner.session_started.is_set():
            self.runner.arm(False);return
        try:cfg=self.save()
        except (ValueError,OSError) as exc:self.set_text(self.detail,str(exc));return
        if cfg!=self.runner.settings:self.runner.reconfigure(cfg)
        self.runner.arm(False)
    def pause(self):
        if self.runner:self.runner.pause();self.set_text(self.headline,'已暫停')
    def end(self):
        if self.runner:self.runner.end();self.set_text(self.headline,'已結束')
    def disconnect(self):
        self.auto_connect=False;self.pending_start=False
        if self.runner:self.runner.close();self.runner=None
        self.preview_message='已中斷連線';self.preview_label.clear();self.preview_label.setText(self.tr(self.preview_message))
        if self.zoom_preview:self.zoom_preview.clear();self.zoom_preview.setText(self.tr(self.preview_message))
        self.set_connected(False);self.set_text(self.headline,'已中斷連線')
    def toggle_preview(self,checked):
        if self.runner:
            if checked:self.runner.preview.set()
            else:self.runner.preview.clear()
        if not checked:
            self.preview_message='預覽已關閉';self.preview_label.clear();self.preview_label.setText(self.tr(self.preview_message))
            if self.zoom_preview:self.zoom_preview.clear();self.zoom_preview.setText(self.tr(self.preview_message))
    def open_preview(self):
        if self.preview_label.image.isNull():return
        if self.zoom_dialog:
            self.zoom_dialog.raise_();self.zoom_dialog.activateWindow();return
        dialog=QtWidgets.QDialog(self);dialog.setWindowTitle(self.tr('即時手機畫面'));dialog.setWindowFlags(QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.FramelessWindowHint);dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground);dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        available=QtWidgets.QApplication.primaryScreen().availableGeometry();dialog.resize(min(600,available.width()-60),min(1000,available.height()-60))
        layout=QtWidgets.QVBoxLayout(dialog);layout.setContentsMargins(0,0,0,0);card=self.card();layout.addWidget(card);inside=QtWidgets.QVBoxLayout(card);inside.setContentsMargins(20,20,20,20);head=QtWidgets.QHBoxLayout();head.addWidget(self.label('即時手機畫面','heading'));head.addStretch();head.addWidget(self.button('關閉',dialog.close));inside.addLayout(head)
        preview=PhonePreview();preview.setImage(self.preview_label.image);preview.setToolTip('');preview.setCursor(QtCore.Qt.CursorShape.ArrowCursor);preview.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus);inside.addWidget(preview,1)
        self.zoom_dialog,self.zoom_preview=dialog,preview
        def closed(_):self.zoom_dialog=None;self.zoom_preview=None
        dialog.finished.connect(closed);dialog.show()
    def show_usb_help(self):
        screen = self.screen().availableGeometry()
        dialog, content = self.maintenance.panel('USB 連線教學', width=min(600, screen.width()-40))
        brands = DisclosureComboBox(dialog)
        brands.setAccessibleName(self.tr('手機品牌'))
        for key, label in BRANDS:
            brands.addItem(self.tr('其他 Android 手機') if key == 'other' else label, key)
        content.addWidget(brands)
        scroll = QtWidgets.QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(max(140, min(270, screen.height()-260)))
        card = self.card()
        steps = QtWidgets.QVBoxLayout(card)
        steps.setContentsMargins(20, 16, 20, 16)
        steps.setSpacing(12)
        scroll.setWidget(card)
        content.addWidget(scroll)
        source = ''

        def show_steps():
            nonlocal source
            while steps.count():
                previous = steps.takeAt(0).widget()
                previous.hide()
                previous.deleteLater()
            instructions, source = guide_for(brands.currentData(), self.language)
            for index, instruction in enumerate(instructions, start=1):
                label = self.label(f'{index}.  {instruction}')
                label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
                steps.addWidget(label)

        brands.currentIndexChanged.connect(show_steps)
        show_steps()
        actions = QtWidgets.QHBoxLayout()
        official = self.button('官方說明', lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(source)))
        actions.addWidget(official)
        actions.addStretch()
        actions.addWidget(self.button('關閉', dialog.accept, 'primary'))
        content.addLayout(actions)
        dialog.finished.connect(dialog.deleteLater)
        dialog.open()
    def show_adb_tools(self):
        if self.runner or self.busy:
            return
        dialog, content = self.maintenance.panel('ADB 工具位置')
        content.addWidget(self.label('ADB 是電腦與 Android 手機通訊的工具。一般會從系統自動找到。只有在已下載 Platform-Tools、但程式找不到 ADB 時，才需要指定檔案。'))
        location = self.label(shutil.which(self.adb_path) or self.tr('目前找不到 ADB'), 'muted')
        location.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        location.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        content.addWidget(location)
        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(self.button('自動尋找', lambda: self.use_adb_path('adb', dialog)))
        actions.addStretch()
        actions.addWidget(self.button('選擇 ADB 執行檔…', lambda: self.browse(dialog), 'primary'))
        content.addLayout(actions)
        dialog.finished.connect(dialog.deleteLater)
        dialog.open()
    def browse(self, dialog=None):
        if self.runner or self.busy:return
        resolved = shutil.which(self.adb_path)
        start = (str(Path(resolved).parent) if resolved else
                 QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.DownloadLocation))
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            dialog or self, self.tr('選擇 ADB 執行檔…'), start, 'ADB (adb.exe)',
        )
        if path and Path(path).name.casefold() == 'adb.exe' and Path(path).is_file():
            self.use_adb_path(path, dialog)
    def use_adb_path(self, path, dialog):
        self.adb_path = path
        self.save_ui_preference('adb_path', None if path == 'adb' else path)
        if dialog is not None:
            dialog.accept()
        self.refresh()
    def show_status(self,status,state,reason):
        self._last_messages=(status,state,reason);self._rendering_status=True
        try:
            if self.headline.text()!=self.tr(status):
                self.set_text(self.headline,status);self.status_animation.stop();self.status_effect.setOpacity(.25);self.status_animation.setEndValue(1);self.status_animation.start();target=self.headline.pos();self.status_slide.stop();self.status_slide.setStartValue(target+QtCore.QPoint(0,7));self.status_slide.setEndValue(target);self.status_slide.start()
            self.detail.setProperty('i18n_source',None)
            text=self.tr(state) if not reason or reason==status else self.tr(state)+' · '+self.tr(reason)
            if self.detail.text()!=text:self.detail.setText(text)
        finally:self._rendering_status=False
    def poll(self):
        while not self.q.empty():
            done,result,error=self.q.get();self.busy=False;self.connect_btn.setEnabled(not bool(self.runner))
            if error:self.pending_start=False;self.set_text(self.headline,'連線未完成');self.set_text(self.detail,error)
            else:
                try:done(result)
                except Exception as exc:self.set_text(self.detail,str(exc))
        self.update_action_buttons()
        if not self.runner:return
        latest=None
        while not self.runner.messages.empty():latest=self.runner.messages.get_nowait()
        if not latest:return
        if 'error' in latest:
            error=latest['error'];self.disconnect();self.set_text(self.headline,'工作階段已停止');self.set_text(self.detail,error);return
        self.show_status(latest['status'],latest['state'],latest['reason'])
        if latest['image'] is not None and self.preview.isChecked():
            img=latest['image'];self.frame=img;qimg=QtGui.QImage(img.data,img.shape[1],img.shape[0],img.strides[0],QtGui.QImage.Format.Format_BGR888).copy()
            self.preview_label.setImage(qimg)
            if self.zoom_preview:self.zoom_preview.setImage(qimg)
        t=self.preview_label.paint_times;fps=(len(t)-1)/(t[-1]-t[0]) if len(t)>1 and t[-1]>t[0] and time.perf_counter()-t[-1]<.5 else 0
        self.set_text(self.metrics,f"擷取 {latest.get('capture_fps',0):.1f} fps  ·  辨識 {latest['fps']:.1f} fps  ·  預覽 {fps:.1f} fps  ·  畫面年齡 {latest['age_ms']:.0f} ms")
        self.cast_count.setText(str(latest['casts']));self.result_count.setText(str(latest['results']))
    def toggle_maximize(self):
        # Translucent frameless windows do not reliably report Windows' native
        # maximized state. Keep explicit geometry and respect our size limits.
        if self.window_expanded:
            if self.restore_rect is not None:self.setGeometry(self.restore_rect)
            self.window_expanded=False;self.max_button.setExpanded(False)
        else:
            self.restore_rect=QtCore.QRect(self.geometry())
            screen=self.windowHandle().screen() if self.windowHandle() else QtWidgets.QApplication.primaryScreen()
            area=screen.availableGeometry();width=min(self.maximumWidth(),area.width());height=min(self.maximumHeight(),area.height())
            self.setGeometry(area.x()+(area.width()-width)//2,area.y()+(area.height()-height)//2,width,height)
            self.window_expanded=True;self.max_button.setExpanded(True)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if not hasattr(self,'body') or not hasattr(self,'title_spacer'):return
        aspect=self.width()/max(1,self.height())
        compact=(self.width()<760 and aspect<1.0) or (self.width()<1200 and aspect<.85)
        short=self.height()<760
        self.title_spacer.changeSize(0,12 if short else 30,QtWidgets.QSizePolicy.Policy.Minimum,QtWidgets.QSizePolicy.Policy.Fixed)
        self.right_scroll.widget().layout().invalidate()
        hero_direction=QtWidgets.QBoxLayout.Direction.LeftToRight if self.width()>=1100 and not compact else QtWidgets.QBoxLayout.Direction.TopToBottom
        if self.hero_layout.direction()!=hero_direction:self.hero_layout.setDirection(hero_direction)
        side=max(20 if short else 28,(self.width()-1680)//2)
        self.page.setContentsMargins(side,16 if short else 24,side,16 if short else 24)
        self.page.setSpacing(12 if short else 18)
        self.hero_layout.setContentsMargins(20 if short else 24,10 if short else 18,20 if short else 24,10 if short else 18)
        self.hero_layout.setSpacing(8 if short else 14)
        desired=QtWidgets.QBoxLayout.Direction.TopToBottom if compact else QtWidgets.QBoxLayout.Direction.LeftToRight
        if self.body.direction()!=desired:
            self.body.setDirection(desired)
            if not self.preview_label.image.isNull():
                self.preview_label.reveal.stop();self.preview_label.reveal.setStartValue(.72);self.preview_label.reveal.setEndValue(1.0);self.preview_label.reveal.start()
        self.compact_controls.setVisible(compact)
        self.start_btn.setVisible(not compact);self.pause_btn.setVisible(not compact)
        self.left.setMaximumWidth(16777215 if compact else 440 if self.width()>=1500 else 360)
        self.preview_label.setMinimumHeight(140 if compact else 180)
        self.left.setMaximumHeight(500 if compact else 16777215)
        self.left.setMinimumHeight(max(260,min(430,self.height()-(345 if short else 385))) if compact else 0)
        self.right.setMinimumHeight(500 if compact else 0)
    def mousePressEvent(self,event):
        if event.button()==QtCore.Qt.MouseButton.LeftButton and event.position().y()<65:
            self.drag_pos=event.globalPosition().toPoint()-self.frameGeometry().topLeft();event.accept()
    def mouseMoveEvent(self,event):
        if self.drag_pos is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint()-self.drag_pos);event.accept()
    def mouseReleaseEvent(self,event):
        self.drag_pos=None
    def closeEvent(self,event):
        if self.runner:self.runner.close()
        super().closeEvent(event)

def main(icon_path=None, *, install_root=None):
    app = QtWidgets.QApplication([arg for arg in sys.argv if arg not in ('--ruins', '--start')])
    app.setStyleSheet(STYLE)
    if icon_path is not None:
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))
    window = FishingWindow('ruins' if '--ruins' in sys.argv else 'fishing', '--start' in sys.argv, install_root=install_root)
    window.show()
    sys.exit(app.exec())
if __name__=='__main__':main()
