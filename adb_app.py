# SPDX-License-Identifier: GPL-3.0-only
"""ADB phone UI. Import has no device or window side effects."""
import json
import time
from collections import deque
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from fisher.adb import Adb, PHONE_DEFAULTS, crop_frame, validate_phone_settings
from fisher.config import DATA_ROOT
from fisher.phone_runtime import PhoneRunner

class PhoneApp:
    def __init__(self, root):
        self.root, self.runner = root, None
        self.devices = []
        self.frame = None
        self.package = None
        self.crop = [0, 0, 1, 1]
        self.ui_queue = queue.SimpleQueue()
        self.busy = False
        self.preview_times = deque(maxlen=90)
        self.generation = 0
        self.closed = False
        self.pending_transport = None
        self.values = {}
        self.selection = tk.StringVar()
        self.path = tk.StringVar(value="adb")
        self.observe = tk.BooleanVar(value=True)
        self.preview = tk.BooleanVar(value=True)
        self.continuous = tk.BooleanVar(value=True)
        self.humanize = tk.BooleanVar(value=True)
        self.headline = tk.StringVar(value="連接你的手機")
        self.detail = tk.StringVar(value="以 USB 連接、開啟 USB 偵錯，並在手機上允許這台電腦。")
        self.metrics = tk.StringVar(value="尚無擷取數據")
        self.crop_text = tk.StringVar(value="遊戲範圍：完整螢幕；有黑邊或系統列時請重新框選")
        self.load_settings()
        root.title("tt tool · ADB 手機釣魚")
        root.geometry("1020x920")
        root.minsize(960, 900)
        root.configure(bg="#f2f4f7")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f2f4f7")
        style.configure("TLabel", background="#f2f4f7", foreground="#192f43", font=("Microsoft JhengHei UI", 10))
        style.configure("TCheckbutton", background="#f2f4f7", font=("Microsoft JhengHei UI", 10))
        style.configure("TButton", padding=(12, 9), font=("Microsoft JhengHei UI", 10))
        style.configure("Primary.TButton", background="#17678a", foreground="white")
        style.map("Primary.TButton", background=[("active", "#10506d"), ("disabled", "#748b96")])
        outer = ttk.Frame(root, padding=24)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="tt tool", font=("Segoe UI", 23, "bold")).pack(side="left")
        ttk.Label(header, text="手機釣魚助手", font=("Microsoft JhengHei UI", 12)).pack(side="left", padx=16)
        ttk.Label(header, text="ADB / USB", foreground="#475e70").pack(side="right")
        ttk.Separator(outer).pack(fill="x", pady=16)
        connection = ttk.Frame(outer)
        connection.pack(fill="x")
        self.device_combo = ttk.Combobox(connection, textvariable=self.selection, state="readonly", width=44)
        self.device_combo.pack(side="left", fill="x", expand=True)
        self.refresh_button = ttk.Button(connection, text="重新偵測", command=self.refresh)
        self.refresh_button.pack(side="left", padx=8)
        self.connect_button = ttk.Button(connection, text="連線並觀察", style="Primary.TButton", command=self.connect)
        self.connect_button.pack(side="left")
        status = ttk.Frame(outer)
        status.pack(fill="x", pady=(20, 16))
        ttk.Label(status, textvariable=self.headline, font=("Microsoft JhengHei UI", 16, "bold")).pack(anchor="w")
        ttk.Label(status, textvariable=self.detail, wraplength=880).pack(anchor="w", pady=(5, 0))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 24))
        self.image_label = tk.Label(left, text="連線後顯示手機畫面\n預覽只保留最新一張", bg="#dde5ec", fg="#334d61",
                                    width=35, height=25, font=("Microsoft JhengHei UI", 10))
        self.image_label.pack(fill="both", expand=True)
        ttk.Checkbutton(left, text="顯示辨識預覽", variable=self.preview, command=self.toggle_preview).pack(anchor="w", pady=6)
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="遊戲畫面與點擊", font=("Microsoft JhengHei UI", 11, "bold")).pack(anchor="w")
        self.crop_button = ttk.Button(right, text="框選遊戲畫面 / 設定按鈕", command=self.select_region)
        self.crop_button.pack(fill="x", pady=(8, 5))
        ttk.Label(right, textvariable=self.crop_text, wraplength=540).pack(anchor="w", pady=(0, 12))
        row = ttk.Frame(right)
        row.pack(fill="x")
        for key, label in (("tap_x", "按鈕 X 比例"), ("tap_y", "按鈕 Y 比例")):
            ttk.Label(row, text=label).pack(side="left", padx=(0, 6))
            var = tk.StringVar(value=str(self.saved[key]))
            self.values[key] = var
            ttk.Entry(row, textvariable=var, width=7).pack(side="left", padx=(0, 12))
        ttk.Separator(right).pack(fill="x", pady=16)
        ttk.Label(right, text="執行設定", font=("Microsoft JhengHei UI", 11, "bold")).pack(anchor="w")
        ttk.Checkbutton(right, text="僅觀察與預測，不操作手機", variable=self.observe).pack(anchor="w", pady=(8, 4))
        ttk.Checkbutton(right, text="持續釣魚（忽略次數和時間上限）", variable=self.continuous).pack(anchor="w", pady=4)
        ttk.Checkbutton(right, text="模擬手動操作（落點、反應與按壓時間）", variable=self.humanize).pack(anchor="w", pady=4)
        tabs = ttk.Notebook(right)
        tabs.pack(fill="x", pady=(6, 0))
        limits_tab = ttk.Frame(tabs, padding=8)
        timing_tab = ttk.Frame(tabs, padding=8)
        tabs.add(limits_tab, text="執行上限")
        tabs.add(timing_tab, text="時序調整")
        for key, label in (("input_latency_ms", "觸控延遲補償（毫秒）"),
                           ("stream_delay_ms", "影像串流延遲估計（毫秒）"),
                           ("timing_uncertainty_ms", "時序不確定餘量（毫秒）"),
                           ("capture_interval", "辨識最短間隔（秒）"),
                           ("result_wait_s", "收下首次等待（秒）"),
                           ("result_retry_s", "收下重試間隔（秒）"),
                           ("max_casts", "下鉤上限"), ("max_session_minutes", "時間上限（分鐘）")):
            line = ttk.Frame(limits_tab if key in ("max_casts", "max_session_minutes") else timing_tab)
            line.pack(fill="x", pady=4)
            ttk.Label(line, text=label).pack(side="left")
            var = tk.StringVar(value=str(self.saved[key]))
            self.values[key] = var
            ttk.Entry(line, textvariable=var, width=9).pack(side="right")
        ttk.Label(right, text="延遲補償需實機調整；ADB 指令耗時不等於觸控生效時間。", wraplength=520,
                  foreground="#475e70").pack(anchor="w", pady=8)
        controls = ttk.Frame(right)
        controls.pack(fill="x", pady=(8, 0))
        self.start_button = ttk.Button(controls, text="開始", style="Primary.TButton", command=self.start)
        self.start_button.pack(side="left", fill="x", expand=True)
        ttk.Button(controls, text="暫停  Esc", command=self.pause).pack(side="left", padx=(8, 0), fill="x", expand=True)
        self.disconnect_button = ttk.Button(right, text="中斷連線", command=self.disconnect)
        self.disconnect_button.pack(fill="x", pady=6)
        bottom_separator = ttk.Separator(outer)
        metric_label = ttk.Label(outer, textvariable=self.metrics)
        footer = ttk.Frame(outer)
        footer.pack(side="bottom", fill="x", pady=(6, 0), before=body)
        metric_label.pack(side="bottom", anchor="w", before=body)
        bottom_separator.pack(side="bottom", fill="x", pady=(14, 8), before=body)
        ttk.Label(footer, text="手機保持解鎖、遊戲在前景；旋轉或斷線後需重新連線。", foreground="#475e70").pack(side="left")
        ttk.Button(footer, text="選擇 adb.exe", command=self.browse_adb).pack(side="right")
        root.bind("<Escape>", lambda e: self.pause())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.set_connected(False)
        root.after(8, self.poll)
        root.after(150, self.refresh)

    def load_settings(self):
        self.saved = dict(PHONE_DEFAULTS)
        path = DATA_ROOT / "phone_settings.json"
        if path.exists():
            try:
                self.saved.update(validate_phone_settings(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError, TypeError):
                self.detail.set("手機設定無法讀取，使用預設值；原檔未改寫。")
        self.crop = list(self.saved["crop"])
        self.continuous.set(self.saved["continuous"])
        self.humanize.set(self.saved["humanize"])

    def settings(self):
        cfg = dict(self.saved)
        cfg.update({key: float(var.get()) for key, var in self.values.items()})
        cfg.update(crop=list(self.crop), continuous=self.continuous.get(), humanize=self.humanize.get())
        return validate_phone_settings(cfg)

    def save_settings(self):
        cfg = self.settings()
        path = DATA_ROOT / "phone_settings.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        self.saved = cfg
        return cfg

    def set_connected(self, yes):
        for button in (self.crop_button, self.start_button, self.disconnect_button):
            button.configure(state="normal" if yes else "disabled")

    def background(self, work, done):
        if self.busy:
            return
        self.busy = True
        generation = self.generation
        self.refresh_button.configure(state="disabled")
        self.connect_button.configure(state="disabled")
        def job():
            try:
                result, error = work(), None
            except Exception as exc:
                result, error = None, str(exc)
            self.ui_queue.put((generation, done, result, error))
        threading.Thread(target=job, daemon=True).start()

    def refresh(self):
        if self.runner or self.busy:
            return
        executable = self.path.get()
        def work():
            adb = Adb(executable)
            try:
                return adb.devices()
            finally:
                adb.close()
        def done(devices):
            self.devices = devices
            rows = [f"{d.serial}  ·  {d.state}  ·  {d.detail}" for d in devices]
            self.device_combo.configure(values=rows)
            if rows:
                self.device_combo.current(0)
                self.headline.set("選擇手機，開始觀察")
                self.detail.set("device 可連線；unauthorized 請在手機確認授權；offline 請重新插拔。")
            else:
                self.selection.set("")
                self.headline.set("未偵測到手機")
                self.detail.set("確認 USB 資料線、USB 偵錯與電腦授權，再按重新偵測。")
        self.background(work, done)

    def connect(self):
        if self.runner or self.busy:
            return
        index = self.device_combo.current()
        if index < 0 or index >= len(self.devices):
            self.detail.set("請先偵測並選擇一台手機。")
            return
        device = self.devices[index]
        if device.state != "device":
            self.detail.set("裝置尚未就緒：" + device.state)
            return
        try:
            cfg = self.save_settings()
        except (OSError, ValueError) as exc:
            self.detail.set(str(exc))
            return
        executable, serial = self.path.get(), device.serial
        def work():
            adb = Adb(executable, serial)
            self.pending_transport = adb
            try:
                return adb.capture(), adb.foreground()
            finally:
                adb.close()
                self.pending_transport = None
        def done(result):
            frame, package = result
            self.frame, self.package = frame.image, package
            if self.frame.shape[0] < self.frame.shape[1]:
                raise ValueError("請將手機和遊戲轉為直向後重新連線")
            self.runner = PhoneRunner(executable, serial, cfg, self.frame.shape[:2], package)
            self.runner.start()
            self.set_connected(True)
            self.device_combo.configure(state="disabled")
            self.headline.set("已連線 · 僅觀察")
            self.detail.set("前景 App：" + package + "。先框選遊戲與按鈕，再開始。")
        self.background(work, done)

    def start(self):
        if not self.runner:
            return
        if self.runner.active.is_set():
            return
        try:
            cfg = self.save_settings()
        except (OSError, ValueError) as exc:
            self.detail.set(str(exc))
            return
        # Apply settings with a clean runtime; never modify a running controller.
        if cfg != self.runner.settings:
            self.detail.set("設定已儲存；請中斷並重新連線以套用。")
            return
        self.runner.arm(self.observe.get())

    def pause(self):
        if self.runner:
            self.runner.pause()
        self.headline.set("已暫停 · 僅觀察")

    def disconnect(self):
        if self.runner:
            self.runner.close()
            self.runner = None
        self.set_connected(False)
        self.preview_times.clear()
        self.device_combo.configure(state="readonly")
        self.headline.set("已中斷連線")
        self.detail.set("調整設定後，重新連線即可套用。")

    def toggle_preview(self):
        if self.runner:
            if self.preview.get():
                self.runner.preview.set()
            else:
                self.runner.preview.clear()
        if not self.preview.get():
            self.preview_times.clear()
            self.image_label.configure(image="", text="預覽已關閉\n辨識持續執行")
            self.image_label.image = None

    def select_region(self):
        if self.runner:
            self.pause()
            frame, _ = self.runner.capture.snapshot()
            if frame:
                self.frame = frame.image.copy()
        if self.frame is None:
            return
        self.disconnect()
        dialog = tk.Toplevel(self.root)
        dialog.title("先拖曳完整遊戲範圍，再點釣魚／收下共用按鈕")
        height = min(740, self.root.winfo_screenheight()-180)
        image = Image.fromarray(self.frame[:, :, ::-1])
        image.thumbnail((550, height))
        photo = ImageTk.PhotoImage(image)
        canvas = tk.Canvas(dialog, width=image.width, height=image.height, highlightthickness=0)
        canvas.pack()
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas.image = photo
        hint = tk.StringVar(value="拖曳完整遊戲範圍，排除系統列與黑邊。Esc 取消。")
        ttk.Label(dialog, textvariable=hint, wraplength=540).pack(padx=12, pady=10)
        state = {"start": None, "rect": None, "crop": None}
        def press(event):
            if state["crop"] is None:
                state["start"] = max(0, min(image.width, event.x)), max(0, min(image.height, event.y))
            else:
                x, y, w, h = state["crop"]
                px, py = event.x/image.width, event.y/image.height
                if not (x <= px <= x+w and y <= py <= y+h):
                    hint.set("請點選遊戲範圍內的共用按鈕位置。")
                    return
                self.crop = list(state["crop"])
                self.values["tap_x"].set(f"{(px-x)/w:.5f}")
                self.values["tap_y"].set(f"{(py-y)/h:.5f}")
                self.crop_text.set("遊戲範圍與按鈕已設定；重新連線後套用。")
                self.save_settings()
                dialog.destroy()
        def motion(event):
            if state["start"] is None or state["crop"] is not None:
                return
            if state["rect"]:
                canvas.delete(state["rect"])
            sx, sy = state["start"]
            state["rect"] = canvas.create_rectangle(sx, sy, event.x, event.y, outline="#00a9ce", width=3)
        def release(event):
            if state["start"] is None or state["crop"] is not None:
                return
            sx, sy = state["start"]
            ex, ey = max(0, min(image.width, event.x)), max(0, min(image.height, event.y))
            x, y, w, h = min(sx, ex), min(sy, ey), abs(ex-sx), abs(ey-sy)
            if w < 60 or h < 100:
                hint.set("選區太小，請重新拖曳完整遊戲範圍。")
                state["start"] = None
                return
            state["crop"] = x/image.width, y/image.height, w/image.width, h/image.height
            hint.set("現在點選釣魚／拉鉤／收下共用的按鈕位置。")
        canvas.bind("<ButtonPress-1>", press)
        canvas.bind("<B1-Motion>", motion)
        canvas.bind("<ButtonRelease-1>", release)
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.grab_set()

    def browse_adb(self):
        if self.runner or self.busy:
            return
        path = filedialog.askopenfilename(title="選擇 adb.exe", filetypes=[("ADB", "adb.exe"), ("所有檔案", "*")])
        if path:
            self.path.set(path)
            self.refresh()

    def poll(self):
        if self.closed:
            return
        while not self.ui_queue.empty():
            generation, done, result, error = self.ui_queue.get()
            if generation != self.generation:
                continue
            self.busy = False
            self.refresh_button.configure(state="normal")
            self.connect_button.configure(state="normal")
            if error:
                self.headline.set("連線未完成")
                self.detail.set(error)
            else:
                try:
                    done(result)
                except Exception as exc:
                    self.detail.set(str(exc))
        if self.runner:
            latest = None
            while not self.runner.messages.empty():
                latest = self.runner.messages.get_nowait()
            if latest:
                if "error" in latest:
                    error = latest["error"]
                    self.disconnect()
                    self.headline.set("工作階段已停止")
                    self.detail.set(error)
                else:
                    self.headline.set(latest["status"])
                    self.detail.set(latest["state"] + " · " + latest["reason"])
                    action = latest["action_ms"]
                    if latest["image"] is not None and self.preview.get():
                        image = Image.fromarray(latest["image"][:, :, ::-1])
                        image.thumbnail((280, 450))
                        photo = ImageTk.PhotoImage(image)
                        self.image_label.configure(image=photo, text="", width=280, height=450)
                        self.image_label.image = photo
                        self.preview_times.append(time.perf_counter())
                    times = self.preview_times
                    now = time.perf_counter()
                    preview_fps = ((len(times)-1)/(times[-1]-times[0])
                                   if len(times)>1 and now-times[-1]<.5 and times[-1]>times[0] else 0)
                    self.metrics.set(f"辨識 {latest['fps']:.1f} fps   ·   預覽 {preview_fps:.1f} fps   ·   畫面年齡 {latest['age_ms']:.0f} ms   ·   下鉤 {latest['casts']} / 結算 {latest['results']}" + (f"   ·   輸入 {action:.0f} ms" if action is not None else ""))
        self.root.after(8, self.poll)

    def close(self):
        self.closed = True
        self.generation += 1
        if self.pending_transport:
            self.pending_transport.close()
        if self.runner:
            self.runner.close()
        self.root.destroy()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="tt tool ADB 手機釣魚")
    parser.add_argument("--serial", help="啟動後明確連線到指定序號，仍保持僅觀察")
    args = parser.parse_args()
    root = tk.Tk()
    app = PhoneApp(root)
    if args.serial:
        def select_requested():
            if app.busy:
                root.after(100, select_requested)
                return
            for index, device in enumerate(app.devices):
                if device.serial == args.serial:
                    app.device_combo.current(index)
                    app.connect()
                    return
            app.detail.set("指定裝置未就緒，請重新偵測。")
        root.after(700, select_requested)
    root.mainloop()


if __name__ == "__main__":
    main()
