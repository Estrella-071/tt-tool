# SPDX-License-Identifier: GPL-3.0-only
"""Small one-round sweep assistant for an Android device or Windows window."""
import queue
from collections import deque
import ctypes as C
import threading
import time
import tkinter as tk
from tkinter import ttk
import cv2
import mss
import numpy as np
from PIL import Image, ImageTk
from fisher.adb import Adb, StreamCapture
from fisher.sweep import detect, detect_controls, SweepController, bottom_y
from fisher.sweep_calibration import calibrate
from fisher.sweep_profile import remember
from fisher.sweep_window import WindowTap
try:
    import dxcam
except ImportError:
    dxcam = None
from fisher.windows import Windows, INPUT, KEYBDINPUT, enable_dpi_awareness

class App:
    def __init__(self, root):
        self.root = root
        self.win = Windows()
        self.events = queue.Queue(maxsize=3)
        self.stop = threading.Event()
        self.thread = None
        self.items = []
        self.mode = tk.StringVar(value='手機 ADB')
        self.key = tk.StringVar(value='空格')
        self.status = tk.StringVar(value='選擇來源後開始')
        self.detail = tk.StringVar(value='先開啟遊戲的大掃除準備畫面。')
        root.title('大掃除助手')
        root.geometry('480x670')
        root.minsize(430, 570)
        root.configure(bg='#f1f4f5')
        style = ttk.Style(root); style.theme_use('clam')
        style.configure('TFrame', background='#f1f4f5')
        style.configure('TLabel', background='#f1f4f5', foreground='#19313a', font=('Microsoft JhengHei UI', 10))
        style.configure('TButton', padding=9, font=('Microsoft JhengHei UI', 10))
        style.configure('Primary.TButton', background='#087e72', foreground='white')
        outer = ttk.Frame(root, padding=20); outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='大掃除助手', font=('Microsoft JhengHei UI', 19, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='每次執行一輪，自動完成黃色判定').pack(anchor='w', pady=(3, 16))
        row=ttk.Frame(outer); row.pack(fill='x')
        self.mode_box=ttk.Combobox(row,textvariable=self.mode,values=('手機 ADB','電腦視窗'),state='readonly',width=12)
        self.mode_box.pack(side='left'); self.mode_box.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.target=ttk.Combobox(row,state='readonly'); self.target.pack(side='left',fill='x',expand=True,padx=8)
        self.refresh_button=ttk.Button(row,text='重新偵測',command=self.refresh); self.refresh_button.pack(side='right')
        keyrow=ttk.Frame(outer); keyrow.pack(fill='x',pady=(8,0))
        ttk.Label(keyrow,text='視窗快捷鍵').pack(side='left')
        ttk.Combobox(keyrow,textvariable=self.key,values=('空格',)+tuple('F'+str(i) for i in range(1,13)),state='readonly',width=8).pack(side='left',padx=8)
        self.preview=tk.Label(outer,text='選擇來源並開始',bg='#dae5e5',fg='#426064',font=('Microsoft JhengHei UI',10))
        self.preview.pack(fill='both',expand=True,pady=16)
        ttk.Label(outer,textvariable=self.status,font=('Microsoft JhengHei UI',14,'bold')).pack(anchor='w')
        ttk.Label(outer,textvariable=self.detail,wraplength=410).pack(anchor='w',pady=(5,12))
        buttons=ttk.Frame(outer);buttons.pack(fill='x')
        self.start_button=ttk.Button(buttons,text='開始一輪',style='Primary.TButton',command=self.start);self.start_button.pack(side='left',fill='x',expand=True)
        self.stop_button=ttk.Button(buttons,text='停止',command=self.cancel);self.stop_button.pack(side='left',padx=(8,0))
        ttk.Label(outer,text='視窗模式：將所選快捷鍵映射到開始／停止按鈕，啟動後切回視窗。',wraplength=410).pack(anchor='w',pady=(12,0))
        root.protocol('WM_DELETE_WINDOW',self.close); root.after(100,self.poll); root.after(100,self.refresh)

    def publish(self, status, detail='', frame=None):
        try:self.events.put_nowait((status,detail,frame))
        except queue.Full:
            try:self.events.get_nowait()
            except queue.Empty:pass
            try:self.events.put_nowait((status,detail,frame))
            except queue.Full:pass

    def refresh(self):
        if self.thread and self.thread.is_alive():return
        try:
            if self.mode.get()=='手機 ADB':
                adb=Adb()
                try:self.items=[(d.serial, d.serial+' · '+d.state) for d in adb.devices() if d.state=='device']
                finally:adb.close()
            else:self.items=self.win.windows('ldplayer',True)
            self.target['values']=[name for _,name in self.items]
            if self.items:self.target.current(0);self.status.set('準備連線');self.detail.set('請確認選擇的來源與遊戲畫面。')
            else:self.target.set('');self.status.set('找不到來源');self.detail.set('請檢查手機 USB 偵錯授權，或開啟模擬器視窗。')
        except Exception as e:self.status.set('偵測失敗');self.detail.set(str(e))

    def start(self):
        if self.thread and self.thread.is_alive():return
        i=self.target.current()
        if i<0 or i>=len(self.items):self.status.set('請選擇來源');return
        self.stop.clear()
        self.start_button['state']='disabled'; self.refresh_button['state']='disabled';self.mode_box['state']='disabled';self.target['state']='disabled'
        self.thread=threading.Thread(target=self.run,args=(self.mode.get(),self.items[i][0],self.key.get()),daemon=True);self.thread.start()

    def cancel(self):
        self.stop.set();self.status.set('正在停止')

    def tap_key(self, hwnd, key, stamp):
        if key == '空格':
            return self.win.tap_space(hwnd,30,self.stop.is_set,lambda:time.perf_counter()-stamp<.3)
        vk=0x70+int(key[1:])-1
        if (self.stop.is_set() or not self.win.foreground_matches(hwnd) or
                time.perf_counter()-stamp>.3 or any(self.win.key_down(k) for k in (0x10,0x11,0x12,0x5b,0x5c,vk))):
            return False
        down=INPUT(type=1,ki=KEYBDINPUT(vk,0,0,0,0))
        up=INPUT(type=1,ki=KEYBDINPUT(vk,0,2,0,0))
        if self.win.u.SendInput(1,C.byref(down),C.sizeof(INPUT))!=1:raise OSError('快捷鍵輸入失敗')
        try:self.stop.wait(.03)
        finally:
            if self.win.u.SendInput(1,C.byref(up),C.sizeof(INPUT))!=1:raise OSError('快捷鍵釋放失敗')
        return True

    def run(self, mode, target, key):
        adb=capture=camera=None
        preview_worker=None
        pending_profiles=[]
        guard_stop=threading.Event()
        try:
            previous_preview=getattr(self,'preview_thread',None)
            if previous_preview and previous_preview is not threading.current_thread():
                previous_preview.join(timeout=6)
                if previous_preview.is_alive():raise RuntimeError('預覽尚未停止，請再試一次')
            if mode=='手機 ADB':
                adb=Adb(serial=target); first=adb.capture(); package=adb.foreground()
                shape=first.image.shape[:2]; capture=StreamCapture(adb,shape);capture.start()
                guard={'ok':False,'at':0.0}
                def foreground():
                    while not self.stop.is_set() and not guard_stop.is_set():
                        try:guard['ok']=adb.foreground()==package
                        except OSError:guard['ok']=False
                        guard['at']=time.perf_counter();guard_stop.wait(.25)
                threading.Thread(target=foreground,daemon=True).start()
            else:
                self.publish('請切回遊戲視窗','3 秒後開始；視窗須保持前景且完整可見。')
                if self.stop.wait(3):return
                shape=None
            if mode=='手機 ADB':
                delay=getattr(self,'precalibrated',None)
                if delay is None:
                    delay=calibrate(adb,capture,shape,self.stop.is_set,lambda: guard['ok'] and time.perf_counter()-guard['at']<.8,self.publish)
                self.publish('校準完成',f'畫面與輸入延遲約 {delay*1000:.0f} 毫秒。')
            else:
                delay=getattr(self,'precalibrated',None)
                if delay is None: raise RuntimeError('請先切回遊戲視窗，等待自動校準。')
            controller=SweepController(latency=delay, max_sample_gap=.25 if mode=='手機 ADB' else .035); start=time.perf_counter(); unknown_since=None; seq=-1; last_preview=0; last_measured=None; fps_times=deque(maxlen=90); last_fps=0
            labels={'ready':'等待準備畫面','starting':'已開始，等待判定','timing':'追蹤黃色目標','waiting':'等待下一次判定','transition':'等待結果'}
            if mode != '手機 ADB':
                def desktop_preview():
                    # Full-frame capture must not block the timing loop.
                    try:
                        with mss.mss() as preview_screen:
                            while not guard_stop.is_set() and not self.stop.is_set():
                                try:
                                    x,y,w,h=self.win.client_box(target)
                                    full=np.asarray(preview_screen.grab({'left':x,'top':y,'width':w,'height':h}))[:,:,:3]
                                    preview=cv2.resize(full,(280,max(1,round(h*280/w))),interpolation=cv2.INTER_AREA)
                                    detail=('畫面判讀：'+'、'.join(controller.results)) if controller.results else '按停止可隨時取消。'
                                    self.publish(labels[controller.state],detail,preview)
                                except (OSError, ValueError):
                                    pass
                                guard_stop.wait(.033)
                    except Exception:
                        pass  # Preview failure must never trigger a game input.
                preview_worker=threading.Thread(target=desktop_preview,daemon=True)
                preview_worker.start()
            with mss.mss() as screen:
                if mode != '手機 ADB' and dxcam is not None:
                    try:
                        camera=dxcam.create(output_color='BGR')
                    except Exception:
                        camera=None
                while not self.stop.is_set():
                    now=time.perf_counter()
                    if now-start>45:raise RuntimeError('等待逾時；請確認畫面與快捷鍵設定。')
                    if mode=='手機 ADB':
                        frame,error=capture.snapshot()
                        if error:raise RuntimeError(error)
                        if not frame or frame.sequence==seq:self.stop.wait(.005);continue
                        seq=frame.sequence;im=frame.image;stamp=frame.captured_at
                        safe=guard['ok'] and now-guard['at']<.8 and now-stamp<.3
                    else:
                        if not self.win.foreground_matches(target):raise RuntimeError('遊戲視窗不在前景，已停止。')
                        x,y,w,h=self.win.client_box(target)
                        top=round(bottom_y((h,w),505));bottom=round(bottom_y((h,w),675))
                        if top < 0 or bottom > h or top >= bottom:raise RuntimeError('視窗畫面不完整')
                        if camera is not None and x>=0 and y+top>=0 and x+w<=camera.width and y+bottom<=camera.height:
                            im=camera.grab(region=(x,y+top,x+w,y+bottom))
                            if im is None:
                                self.stop.wait(.001)
                                continue
                        else:
                            im=np.asarray(screen.grab({'left':x,'top':y+top,'width':w,'height':bottom-top}))[:,:,:3]
                        stamp=time.perf_counter();safe=True
                    obs=detect(im) if mode=='手機 ADB' else detect_controls(im)
                    fps_times.append(now)
                    while fps_times and fps_times[0]<now-2:fps_times.popleft()
                    if now-last_fps>=1 and len(fps_times)>1:
                        report=getattr(self,'report_fps',None)
                        if report:report((len(fps_times)-1)/(fps_times[-1]-fps_times[0]),'辨識')
                        last_fps=now
                    trace=getattr(self,'trace_hook',None)
                    if trace:trace('frame',now,obs,controller.state)
                    if controller.state=='transition':
                        if unknown_since is None:unknown_since=now
                        if now-unknown_since>1.5:
                            self.publish('本輪結束', '畫面判讀：' + '、'.join(controller.results) if controller.results else '已停止操作；倍率轉盤由遊戲處理。',im);return
                    else:unknown_since=None
                    # Never advance controller if the input guard is not fresh.
                    action=controller.step(obs,stamp) if safe else None
                    if controller.last_measured_latency is not None and controller.last_measured_latency != last_measured:
                        last_measured=controller.last_measured_latency
                        raw=getattr(self,'panel_latency',None)
                        profile = target if mode=='手機 ADB' else getattr(self,'window_profile',None)
                        if raw is not None and profile:pending_profiles.append((profile,raw,last_measured))
                    if action:
                        if action=='hit' and controller.hit_delay>0 and self.stop.wait(controller.hit_delay):return
                        # A delayed host wake-up invalidates the projection. Retry on a later pass.
                        if action=='hit' and time.perf_counter()-controller.hit_at > .006:
                            controller.cancel_pending_hit()
                            continue
                        if action=='hit' and time.perf_counter()-stamp>.3:raise RuntimeError('畫面已過期，已停止操作')
                        if trace:trace('action',time.perf_counter(),obs,action)
                        if mode=='手機 ADB':
                            if not guard['ok'] or time.perf_counter()-guard['at']>.8:raise RuntimeError('無法確認手機前景，已停止。')
                            if self.stop.is_set(): return
                            adb.tap(shape[1]*.5,bottom_y(shape,801*.805))
                        else:
                            if key=='自動點擊':
                                if time.perf_counter()-stamp>.3:raise RuntimeError('畫面已過期，已停止操作')
                                WindowTap(self.win,target,self.stop.is_set).tap(w*.5,bottom_y((h,w),801*.805))
                            elif not self.tap_key(target,key,stamp):raise RuntimeError('無法安全送出快捷鍵，已停止。')
                    if mode=='手機 ADB' and now-last_preview>.033:
                        preview=cv2.resize(im,(280,max(1,round(im.shape[0]*280/im.shape[1]))),interpolation=cv2.INTER_AREA)
                        detail = ('畫面判讀：' + '、'.join(controller.results)) if controller.results else '按停止可隨時取消。'
                        self.publish(labels[controller.state],detail,preview);last_preview=now
                    self.stop.wait(.003)
        except Exception as e:self.publish('已停止',str(e))
        finally:
            guard_stop.set()
            if preview_worker:preview_worker.join(timeout=2)
            for profile,raw,measured in pending_profiles:remember(profile,raw,measured)
            if camera:camera.release()
            if capture:
                capture.close()
                capture.thread.join(timeout=3)
                capture.close()
            if adb:adb.close()
            if self.stop.is_set():self.publish('已停止','可再次選擇來源並開始。')
            self.publish('__done__')

    def poll(self):
        while True:
            try:status,detail,frame=self.events.get_nowait()
            except queue.Empty:break
            if status=='__done__':
                self.start_button['state']='normal';self.refresh_button['state']='normal';self.mode_box['state']='readonly';self.target['state']='readonly';continue
            self.status.set(status);self.detail.set(detail)
            if frame is not None:
                im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.thumbnail((250,355))
                photo=ImageTk.PhotoImage(im);self.preview.configure(image=photo,text='');self.preview.image=photo
        self.root.after(100,self.poll)

    def close(self):
        self.stop.set();self.root.destroy()

if __name__=='__main__':
    enable_dpi_awareness(); root=tk.Tk();App(root);root.mainloop()
