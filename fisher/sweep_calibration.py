# SPDX-License-Identifier: GPL-3.0-only
"""Measure the device-to-preview input delay using the game's information panel."""
import statistics
import time
import cv2
import numpy as np
from .sweep import detect, bottom_y


def calibration_consensus(samples):
    """Accept two close independent runs; isolated scheduling spikes fail closed."""
    candidates=[]
    for i,a in enumerate(samples):
        for b in samples[i+1:]:
            difference=abs(a-b)
            if difference <= max(.025, .30*min(a,b)):
                candidates.append((difference,(a+b)/2))
    return min(candidates)[1] if candidates else None


def calibrate(adb, capture, shape, cancelled, foreground, notify=lambda *args: None, min_latency=.06):
    deadline = time.perf_counter() + 8
    previous = -1
    def next_frame(after=-1, timeout=3):
        until = time.perf_counter()+timeout
        while time.perf_counter()<until:
            if cancelled(): raise RuntimeError('已停止校準')
            frame,error=capture.snapshot()
            if error: raise RuntimeError(error)
            if frame and frame.sequence>after and time.perf_counter()-frame.received_at<.3:
                return frame
            time.sleep(.002)
        raise RuntimeError('畫面未更新，已停止校準')
    def tap_point(y):
        if cancelled() or not foreground(): raise RuntimeError('無法確認前景，已停止校準')
        at=time.perf_counter()
        adb.tap(shape[1]*.5, bottom_y(shape, y*801))
        return at
    def wait_change(baseline, after, started):
        end=time.perf_counter()+3
        while time.perf_counter()<end:
            frame=next_frame(after, max(.05,end-time.perf_counter()));after=frame.sequence
            delta=float(np.mean(cv2.absdiff(baseline[180:600], frame.image[180:600])))
            if delta>5 and frame.received_at>=started:
                return frame,frame.received_at-started
        raise RuntimeError('機率資訊畫面沒有變化，已停止校準')
    def await_ready(after=-1):
        end=time.perf_counter()+4
        while time.perf_counter()<end:
            frame=next_frame(after,max(.05,end-time.perf_counter()));after=frame.sequence
            if detect(frame.image).state=='ready':return frame
        raise RuntimeError('請先關閉彈窗，回到大掃除準備畫面')
    values=[]
    ready=await_ready()
    for cycle in range(2):
        notify('正在校準', '開啟機率資訊，量測點擊與畫面延遲。',ready.image)
        baseline=ready.image.copy()
        t=tap_point(.868)
        opened,opening=wait_change(baseline,ready.sequence,t)
        if detect(opened.image).state=='ready':
            raise RuntimeError('未確認機率資訊畫面，已停止校準')
        time.sleep(.35)
        opened=next_frame(opened.sequence)
        before=opened.image.copy()
        t=tap_point(.948)
        closed,closing=wait_change(before,opened.sequence,t)
        ready=await_ready(closed.sequence-1)
        for v in (opening,closing):
            if not min_latency <= v <= .8:raise RuntimeError('量測延遲不穩定，已停止校準')
            values.append(v)
        time.sleep(.2)
        ready=await_ready(ready.sequence)
    if max(values)-min(values)>.22:raise RuntimeError('量測延遲波動過大，已停止校準')
    return statistics.median(values)
