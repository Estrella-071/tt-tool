# SPDX-License-Identifier: GPL-3.0-only
"""Foreground-only desktop capture and clicks for sweep calibration."""
import time
import numpy as np
from .adb import Frame

class WindowCapture:
    def __init__(self, windows, hwnd, screen):
        self.windows, self.hwnd, self.screen = windows, hwnd, screen
        self.sequence = 0

    def snapshot(self):
        x,y,w,h = self.windows.client_box(self.hwnd)
        image = np.asarray(self.screen.grab({'left':x,'top':y,'width':w,'height':h}))[:,:,:3].copy()
        now = time.perf_counter()
        self.sequence += 1
        return Frame(image,now,now,0,self.sequence), None

class WindowTap:
    def __init__(self, windows, hwnd, cancelled):
        self.windows, self.hwnd, self.cancelled = windows, hwnd, cancelled

    def tap(self, x, y):
        win = self.windows
        if self.cancelled() or not win.foreground_matches(self.hwnd):
            raise RuntimeError('遊戲視窗不在前景，已停止。')
        if any(win.key_down(k) for k in (1, 0x10, 0x11, 0x12, 0x5b, 0x5c)):
            raise RuntimeError('偵測到手動輸入，已停止。')
        left,top,width,height = win.client_box(self.hwnd)
        if not (0 <= x < width and 0 <= y < height):
            raise RuntimeError('按鈕不在視窗範圍內，已停止。')
        if not win.u.SetCursorPos(round(left+x), round(top+y)):
            raise OSError('無法移動滑鼠')
        if self.cancelled() or not win.foreground_matches(self.hwnd):
            raise RuntimeError('遊戲視窗不在前景，已停止。')
        win.u.mouse_event(2,0,0,0,0)
        try:
            time.sleep(.01)
        finally:
            win.u.mouse_event(4,0,0,0,0)
