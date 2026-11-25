# SPDX-License-Identifier: GPL-3.0-only
"""Windows sweep assistant, with a standalone Qt interface."""
import os
import sys
import threading
from collections import deque
import time
from pathlib import Path

# PyInstaller expands bundled tools here; development continues to use PATH.
if getattr(sys, 'frozen', False):
    from fisher.bundled_tools import prepare_adb
    bundle_tools = Path(sys._MEIPASS) / 'tools'
    local_root = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    adb_tools = prepare_adb(bundle_tools, local_root)
    os.environ['PATH'] = str(adb_tools) + os.pathsep + str(bundle_tools) + os.pathsep + os.environ.get('PATH', '')

from PySide6.QtCore import Qt, Signal, QTimer, QVariantAnimation, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel,
    QPushButton, QComboBox, QHBoxLayout, QVBoxLayout, QSizePolicy, QGraphicsOpacityEffect)
from fisher.adb import Adb, StreamCapture
from fisher.sweep import detect
from fisher.sweep_calibration import calibrate, calibration_consensus
from fisher.sweep_window import WindowCapture, WindowTap
from fisher.sweep_profile import adjusted_delay
import mss
import numpy as np
from fisher.windows import Windows, enable_dpi_awareness
from sweep_app import App as Runner

STYLE = '''
QMainWindow, QWidget#surface { background: #111111; color: #f7f7f8; font-family: "Microsoft JhengHei UI"; font-size: 16px; font-weight: 700; }
QFrame#panel { background: #111111; border: 0; border-radius: 0; }
QFrame#screen { background: #080808; border: 0; border-radius: 18px; }
QLabel { background: transparent; color: #f7f7f8; border: 0; font-family: "Microsoft JhengHei UI"; font-size: 16px; font-weight: 700; }
QLabel#title { font-size: 28px; font-weight: 800; }
QLabel#subtitle, QLabel#muted { color: #a7a4ad; font-size: 15px; }
QLabel#caption { color: #a7a4ad; font-size: 15px; font-weight: 700; }
QLabel#status { font-size: 22px; font-weight: 750; }
QLabel#badge { background: #28232d; color: #d1b4f0; border: 0; border-radius: 11px; padding: 5px 10px; font-size: 13px; font-weight: 700; }
QComboBox { font-family: "Microsoft JhengHei UI"; font-size: 16px; font-weight: 700; background: #202022; color: #fafafa; border: 0; border-radius: 13px; padding: 10px 32px 10px 13px; min-height: 22px; }
QComboBox:hover { background: #302d32; }
QComboBox:focus { background: #36313a; }
QComboBox:disabled { color: #747179; background: #19191a; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width: 28px; border: 0; }
QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #aaa5ad; width: 0; height: 0; margin-right: 8px; }
QComboBox QAbstractItemView { background: #202022; color: white; selection-background-color: #493757; border: 0; padding: 5px; outline: 0; }
QPushButton { font-family: "Microsoft JhengHei UI"; font-size: 16px; background: #242426; color: #f5f5f5; border: 0; border-radius: 15px; padding: 12px 18px; font-weight: 700; }
QPushButton:hover { background: #343037; }
QPushButton:pressed { background: #403b45; }
QPushButton:focus { background: #454049; }
QPushButton:disabled { background: #1d1c1e; color: #777379; border: 0; }
QPushButton#primary { background: #fbfbfa; color: #111111; border: 0; font-size: 16px; }
QPushButton#primary:hover { background: #e8d8f1; }
QPushButton#primary:pressed { background: #d7b9e7; }
QPushButton#primary:disabled { background: #3c383f; color: #96919a; }
'''

class SoftButton(QPushButton):
    """Small, interruptible hover feedback without changing layout."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fade_effect = QGraphicsOpacityEffect(self)
        self.fade_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.fade_effect)
        self.fade = QPropertyAnimation(self.fade_effect, b"opacity", self)
        self.fade.setDuration(180)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _fade_to(self, value):
        self.fade.stop()
        self.fade.setStartValue(self.fade_effect.opacity())
        self.fade.setEndValue(value)
        self.fade.start()

    def enterEvent(self, event):
        if self.isEnabled(): self._fade_to(.87)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._fade_to(1.0)
        super().leaveEvent(event)


class Window(QMainWindow):
    run = Runner.run
    tap_key = Runner.tap_key
    changed = Signal(str, str, object)
    refreshed = Signal(object, str)
    fps_changed = Signal(float, str)
    frame_available = Signal()

    def __init__(self):
        super().__init__()
        self.win = Windows(); self.stop = threading.Event(); self.thread = None; self.items = []; self.refreshing = False
        self.preview_stop = threading.Event(); self.preview_thread = None; self.precalibrated = None; self.panel_latency = None
        self.last_result = None
        self.preview_times = deque(maxlen=90); self.source_fps = 0.0; self.source_label = '擷取'
        self.frame_lock=threading.Lock();self.frame_latest=None;self.frame_scheduled=False
        self.setWindowTitle('大掃除助手'); self.resize(940, 650); self.setMinimumSize(800, 630)
        self.setStyleSheet(STYLE)
        surface=QWidget(objectName='surface'); self.setCentralWidget(surface)
        outside=QVBoxLayout(surface); outside.setContentsMargins(0,0,0,0)
        panel=QFrame(objectName='panel'); outside.addWidget(panel)
        layout=QVBoxLayout(panel);layout.setContentsMargins(27,24,27,24);layout.setSpacing(20)
        head=QHBoxLayout(); layout.addLayout(head)
        title=QLabel('大掃除助手',objectName='title');head.addWidget(title);head.addStretch()
        body=QHBoxLayout();body.setSpacing(24);layout.addLayout(body,1)
        left=QVBoxLayout();left.setSpacing(12);body.addLayout(left,1)
        left.addWidget(QLabel('選擇來源',objectName='caption'))
        self.mode=QComboBox();self.mode.addItems(['電腦視窗','手機 ADB']);left.addWidget(self.mode)
        targetline=QHBoxLayout(); targetline.setSpacing(8);left.addLayout(targetline)
        self.target=QComboBox();self.target.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed);targetline.addWidget(self.target,1)
        self.refresh_button=SoftButton('重新偵測');targetline.addWidget(self.refresh_button)
        self.key_label=QLabel('視窗快捷鍵',objectName='caption');left.addWidget(self.key_label)
        self.key=QComboBox();self.key.addItems(['空格','自動點擊']+[f'F{i}' for i in range(1,13)]);left.addWidget(self.key)
        left.addSpacing(9)
        self.status=QLabel('準備開始',objectName='status');self.status.setWordWrap(True);left.addWidget(self.status)
        self.detail=QLabel('開啟遊戲的大掃除準備畫面，選擇來源後即可開始。',objectName='muted');self.detail.setWordWrap(True);left.addWidget(self.detail)
        left.addStretch()
        self.start_button=SoftButton('開始一輪',objectName='primary');left.addWidget(self.start_button)
        self.stop_button=SoftButton('停止');self.stop_button.setEnabled(False);left.addWidget(self.stop_button)
        self.hint=QLabel('一輪結束後自動停止，倍率轉盤由遊戲處理。',objectName='muted');self.hint.setWordWrap(True);left.addWidget(self.hint)
        right=QFrame(objectName='screen');body.addWidget(right,1)
        screen=QVBoxLayout(right);screen.setContentsMargins(18,18,18,18)
        screenhead=QHBoxLayout(); screen.addLayout(screenhead)
        screenhead.addWidget(QLabel('畫面預覽',objectName='caption'));screenhead.addStretch()
        self.fps_label=QLabel('等待畫面',objectName='muted');screenhead.addWidget(self.fps_label)
        self.dot=QLabel('●');self.dot.setStyleSheet('color:#ac69d2; font-size: 10px;');screenhead.addWidget(self.dot)
        self.preview=QLabel('開始後顯示畫面');self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.setStyleSheet('color: #aaa5ad; font-size: 15px; font-weight: 700;');self.preview.setMinimumSize(200,250);self.preview.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding);screen.addWidget(self.preview,1)
        self.mode.currentIndexChanged.connect(self.mode_changed);self.refresh_button.clicked.connect(self.refresh)
        self.start_button.clicked.connect(self.start);self.stop_button.clicked.connect(self.cancel)
        self.target.currentIndexChanged.connect(self.target_changed)
        self.key.currentIndexChanged.connect(self.target_changed)
        self.changed.connect(self.on_update);self.refreshed.connect(self.on_refresh);self.fps_changed.connect(self.on_fps);self.frame_available.connect(self.draw_latest_frame)
        self.mode_changed()
        # A quiet breathing indicator signals that the preview area is alive.
        self.pulse=QVariantAnimation(self);self.pulse.setStartValue(.45);self.pulse.setKeyValueAt(.5,1.0);self.pulse.setEndValue(.45);self.pulse.setDuration(4400);self.pulse.setLoopCount(-1);self.pulse.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.dot_effect=QGraphicsOpacityEffect(self.dot);self.dot.setGraphicsEffect(self.dot_effect);self.pulse.valueChanged.connect(self.dot_effect.setOpacity);self.pulse.start()

    def mode_changed(self):
        desktop=self.mode.currentText()=='電腦視窗'
        self.key.setVisible(desktop);self.key_label.setVisible(desktop)
        self.hint.setText('可自動點擊，或選擇已映射的快捷鍵。' if desktop else '一輪結束後自動停止，倍率轉盤由遊戲處理。')
        self.refresh()

    def refresh(self):
        if self.thread and self.thread.is_alive():return
        self.items=[];self.start_button.setEnabled(False);self.preview_stop.set()
        if self.refreshing:return
        self.refreshing=True
        mode=self.mode.currentText();self.refresh_button.setEnabled(False)
        self.status.setText('正在偵測');self.detail.setText('正在尋找可用的手機或視窗。')
        def work():
            try:
                if mode=='手機 ADB':
                    adb=Adb()
                    try:items=[(d.serial,d.serial+' · '+d.state) for d in adb.devices() if d.state=='device']
                    finally:adb.close()
                else:items=self.win.windows('ldplayer',True)
                self.refreshed.emit((mode,items),'')
            except Exception as e:self.refreshed.emit((mode,[]),str(e))
        threading.Thread(target=work,daemon=True).start()

    def on_refresh(self, result, error):
        mode,items=result
        self.refreshing=False
        if mode!=self.mode.currentText():self.refresh_button.setEnabled(True);self.refresh();return
        self.refresh_button.setEnabled(True);self.items=items;self.target.blockSignals(True);self.target.clear()
        for _,name in items:self.target.addItem(name)
        if mode=='電腦視窗':
            preferred=next((i for i,(_,name) in enumerate(items) if any(term in name.lower() for term in ('雷電','ldplayer','dnplayer'))),None)
            if preferred is not None:self.target.setCurrentIndex(preferred)
        if error:self.status.setText('偵測失敗');self.detail.setText(error)
        elif items:self.status.setText('準備開始');self.detail.setText('確認來源，並將遊戲停在大掃除準備畫面。')
        else:self.target.addItem('沒有可用來源');self.status.setText('找不到來源');self.detail.setText('請檢查 USB 偵錯授權或開啟模擬器視窗。')
        self.target.blockSignals(False)
        self.start_button.setEnabled(False)
        if items:self.begin_preview()

    def target_changed(self):
        if self.items and not (self.thread and self.thread.is_alive()):self.begin_preview()

    def begin_preview(self):
        i=self.target.currentIndex()
        if i<0 or i>=len(self.items):return
        old=self.preview_thread;self.preview_stop.set()
        stop=threading.Event();self.preview_stop=stop;self.precalibrated=None;self.panel_latency=None
        self.start_button.setEnabled(False)
        mode=self.mode.currentText();target=self.items[i][0]
        self.window_profile='window:'+self.target.currentText()+':'+self.key.currentText()
        self.preview_thread=threading.Thread(target=self.preview_worker,args=(mode,target,stop,old),daemon=True)
        self.preview_thread.start()

    def preview_worker(self,mode,target,stop,old):
        adb=capture=None
        def emit(status,detail='',frame=None):
            if not stop.is_set() and self.preview_stop is stop:self.publish(status,detail,frame)
        try:
            if old and old is not threading.current_thread():
                old.join(timeout=6)
                if old.is_alive():raise RuntimeError('上一個預覽尚未停止')
            if stop.is_set():return
            if mode=='手機 ADB':
                adb=Adb(serial=target);first=adb.capture();package=adb.foreground()
                capture=StreamCapture(adb,first.image.shape[:2]);capture.start()
                emit('正在連線','等待手機畫面。')
                ready=False;seq=-1;last_ui=0;fps_times=deque(maxlen=90);last_fps=0
                while not stop.is_set():
                    frame,error=capture.snapshot()
                    if error:raise RuntimeError(error)
                    if not frame or frame.sequence==seq:stop.wait(.01);continue
                    seq=frame.sequence;now=time.perf_counter();fps_times.append(now)
                    while fps_times and fps_times[0]<now-2:fps_times.popleft()
                    if now-last_fps>=1 and len(fps_times)>1:
                        self.report_fps((len(fps_times)-1)/(fps_times[-1]-fps_times[0]),'擷取');last_fps=now
                    if now-last_ui>.016:
                        emit('預覽中' if ready else '等待準備畫面', '畫面就緒後會自動校準。' if not ready else f'已校準約 {self.precalibrated*1000:.0f} 毫秒，可開始一輪。',frame.image)
                        last_ui=now
                    if not ready and detect(frame.image).state=='ready':
                        delay=calibrate(adb,capture,first.image.shape[:2],stop.is_set,lambda:adb.foreground()==package,emit)
                        if stop.is_set():return
                        self.panel_latency=delay;self.precalibrated=adjusted_delay(target,delay);ready=True
                        emit('__preview_ready__',f'已校準約 {self.precalibrated*1000:.0f} 毫秒。',frame.image)
            else:
                with mss.mss() as screen:
                    capture=WindowCapture(self.win,target,screen)
                    tap=WindowTap(self.win,target,stop.is_set)
                    ready=False
                    while not stop.is_set():
                        current,_=capture.snapshot();frame=current.image
                        emit('預覽中' if ready else '等待校準',
                             '可開始一輪。' if ready else '切回遊戲視窗，停在準備畫面以自動校準。',frame)
                        if not ready and self.win.foreground_matches(target) and detect(frame).state=='ready':
                            measurements=[]
                            for attempt in range(3):
                                try:
                                    sample=calibrate(tap,capture,frame.shape[:2],stop.is_set,
                                                     lambda:self.win.foreground_matches(target),emit,min_latency=.01)
                                    measurements.append(sample)
                                except RuntimeError:
                                    current,_=capture.snapshot()
                                    if stop.is_set() or not self.win.foreground_matches(target) or detect(current.image).state!='ready':
                                        raise
                                delay=calibration_consensus(measurements)
                                if delay is not None:break
                                emit('重新校準','正在確認延遲是否穩定。',frame)
                            else:
                                raise RuntimeError('延遲量測波動過大，請確認模擬器畫面流暢後重新偵測。')
                            if stop.is_set():return
                            self.panel_latency=delay
                            self.precalibrated=adjusted_delay(self.window_profile,delay,min_delay=.01)
                            ready=True
                            emit('__preview_ready__',f'已校準約 {self.precalibrated*1000:.0f} 毫秒。',frame)
                        stop.wait(.033)
                    capture=None
        except Exception as e:emit('預覽已停止',str(e))
        finally:
            if isinstance(capture, StreamCapture):
                capture.close()
                capture.thread.join(timeout=3)
                capture.close()
            if adb:adb.close()

    def start(self):
        self.last_result = None
        if self.thread and self.thread.is_alive():return
        i=self.target.currentIndex()
        if i<0 or i>=len(self.items):return
        self.stop.clear();self.preview_stop.set()
        for w in (self.start_button,self.refresh_button,self.mode,self.target,self.key):w.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.thread=threading.Thread(target=self.run,args=(self.mode.currentText(),self.items[i][0],self.key.currentText()),daemon=True);self.thread.start()

    def report_fps(self,value,label):self.fps_changed.emit(float(value),label)
    def on_fps(self,value,label):
        self.source_fps=value;self.source_label=label;self.update_rates()
    def update_rates(self):
        times=self.preview_times
        cutoff=time.perf_counter()-2
        while times and times[0]<cutoff:times.popleft()
        rate=(len(times)-1)/(times[-1]-times[0]) if len(times)>1 and times[-1]>times[0] else 0
        self.fps_label.setText(f'{self.source_label} {self.source_fps:.0f} · 預覽 {rate:.0f} FPS')

    def cancel(self):self.stop.set();self.status.setText('正在停止')
    def publish(self,status,detail='',frame=None):
        self.changed.emit(status,detail,None)
        if frame is None:return
        with self.frame_lock:
            self.frame_latest=frame
            if self.frame_scheduled:return
            self.frame_scheduled=True
        self.frame_available.emit()

    def draw_latest_frame(self):
        with self.frame_lock:
            frame=self.frame_latest
            self.frame_latest=None
            self.frame_scheduled=False
        if frame is None:return
        frame=frame.copy();h,w=frame.shape[:2]
        image=QImage(frame.data,w,h,frame.strides[0],QImage.Format.Format_BGR888).copy()
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation))
        self.preview_times.append(time.perf_counter());self.update_rates()
    def on_update(self,status,detail,frame):
        if status=='__preview_ready__':
            self.start_button.setEnabled(True);self.status.setText('準備開始');self.detail.setText(self.last_result or detail);return
        if status=='__done__':
            for w in (self.refresh_button,self.mode,self.target,self.key):w.setEnabled(True)
            self.stop_button.setEnabled(False);self.begin_preview();return
        if status=='本輪結束' and detail.startswith('畫面判讀：'):
            self.last_result=detail
        elif self.last_result and status in ('預覽中','等待校準','等待準備畫面'):
            detail=self.last_result
        self.status.setText(status);self.detail.setText(detail)
    def closeEvent(self,event):
        self.stop.set();self.preview_stop.set()
        for worker in (self.thread,self.preview_thread):
            if worker and worker is not threading.current_thread():
                worker.join(timeout=4)
        event.accept()

if __name__=='__main__':
    enable_dpi_awareness();app=QApplication(sys.argv)
    window=Window();window.show();sys.exit(app.exec())
