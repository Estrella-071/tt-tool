# Local verification record — 2026-10-24

English · [繁體中文](VALIDATION-ADB.zh-TW.md) · [日本語](VALIDATION-ADB.ja.md) · [한국어](VALIDATION-ADB.ko.md)

> This technical record includes historical versions and measurements. For current setup and supported workflows, see [the main guide](../README.md).

Version: 1.7.0-adb; base upstream commit: c1263f7.

## Completed

- `python selfcheck.py`: 193 tests passed. Covers the return of existing simulators, new ADB transfers, designated serial numbers, timeout recycling, coordinate conversion, expired screens, pauses, foreground checks, direction/freeze frame thresholds, long screens and settlement positioning.
- `python replay.py`: The attached example is identified as RESULT, with a confidence value of approximately 0.845.
- `python -m compileall -q fisher adb_app.py`: Passed.
- Tkinter actually starts; the main buttons and blocks of the 1020×920 window are all visible. The interface image has been visually inspected, and paging is set to avoid overflow of the operating area.
- The mobile phone is connected via USB ADB, with a resolution of 1200×2670 and game orientation. No changes were made to the mobile phone resolution, mobile phone programs were installed or game files were modified.
- Native PNG screenshot three times around 1411 / 1276 / 1445 ms. After changing to AVC streaming, the stable segment of host decoding output is about one frame every 17 ms; the actual recognition cycle is about 18~22 fps, which will drop due to settlement recognition and input calls.
- The latest short-term measurement is about 61 seconds: the controller records 3 hooking and 3 result events, completes settlement and returns to prepare for hooking, and pauses due to the upper limit of times. Yellow bar reservations and clicks were also observed in other short segments.
- The test screenshots and original records are left in the working directory outside the project; they are not added to the public compressed package or submitted.

## not proven yet

- The precise delay from image presentation to actual touch on the device has not been measured; the 60ms streaming delay, 80ms touch compensation, and 12ms uncertainty margin are still adjustable initial values.
- 3 result events does not represent a hit for all yellow bars, nor is it a statistic for rare fish success rate or stability over time.
- Not verified on all phones, all DPI/aspect ratios, different Android versions, running for hours, and actually unplugging and reconnecting. Protection against disconnection, rotation, and stagnation has been subject to offline regression and program checking; it cannot be called actual testing on all devices.
- The original installation-free Windows package is still based on the emulator entrance; the mobile phone mode is started with local `start_adb.bat` / `adb_app.py`, which requires native Python, ADB, and FFmpeg.

## 1.7.1-adb additional verification

- 198 self-inspections passed, including the addition of real hook control cropping, removal of text that can still be recognized, no misjudgment when panels or buttons are missing, yellow bars not misjudged as pull hooks, and new frame event wake-up returns.
- In the Traditional Chinese prompt screen provided by the user, the original template path cannot be recognized stably; with the new geometry judgment output BITE, the controller can propose HOOK on the first confirmation screen without checking whether the progress bar has been completed.
- After the actual machine observes BITE, it sends HOOK and then enters TIMING. The stable section of the recognition cycle in the normal and yellow bar stages is about 55 to 60 FPS, and will drop temporarily when performing synchronous ADB input.
- The source stream is already close to 60 FPS; this time the increase is the recognition frequency of consuming new images, and we cannot claim that the original stream or the actual touch delay is improved in proportion.
- During the actual measurement, we also encountered an illustration of the bronze weight on the golden record page. Changed to high-confidence grayscale shape positioning, retained the multi-condition confirmation of the original color panel/dark background/weight icon, and added crop regression.
- This does not mean that all yellow bar hits, all fish species, or long periods of continuous operation have been verified.

## 1.7.2-adb settlement waiting

- 200 self-test items passed; new settlement continuous confirmation, 0.25 second first attempt, 0.35 second retry, unknown screen stop input and old settings retention test.
- The actual new fish result page appeared in the confirmation state at about 17.37 seconds of the test time. The interface sampling at 17.58 seconds showed the first CLOSE. The confirmation returned to IDLE at 18.87 seconds and was paused due to the upper hook limit. Interface sampling is not an accurate device animation time; this paragraph can be observed to return in about 1.5 seconds, and there is no guarantee that every result page will be equally fast.
- The new settings and operation areas of Tkinter 1020×920 passed the visible range check; the compilation check and source code package generation passed.

## 1.7.3-adb operation changes

- The settlement wait default and current local setting are both changed to 1 second.
- 203 self-tests passed; including bounded random drop points, yellow bars not included in response waiting, short press to start and end at the same point, pause during response and no input is sent.
- Check the short section of the actual machine for operation simulation to complete 1 hook and 1 result event and return to IDLE, which is suspended due to the upper limit of times. The short press and close operations have been accepted by current mobile phones; the hit rate or long-term stability of all fish species cannot be inferred based on this.
- After adding the check option, the operation area and main buttons of the 1020×920 window are still visible.

## 1.7.4-adb prospect stopped unexpectedly

- 206 self-tests passed. Added regressions such as resuming after a temporary query fails, pausing when the same app is continued in other apps, and preventing input of expired prospect data but not clearing the running status.
- The mobile phone read-only observation ends normally for 20 seconds; 1 out of 199 host-side samples did not confirm the foreground, and the foreground was valid at the end. Observation mode does not send input to the game and cannot be used as a verification of long-term automatic operation.
- The original static reason for the accidental stop: any single exception/non-game focus is immediately cleared from active, and if you see evidence of expired prospects before entering, you will directly declare to leave the game. Input blocking and formal pause conditions have been separated; user-specific trigger events at the time have not been reproduced.
- The two 120 FPS setting experiments of scrcpy 4.0 both ended abnormally in about 4 seconds; the second section has 242 frames, the timestamp spans about 3.954 seconds, and the effective frame rate is about 60.95. This is a truncated snippet and no inference can be made about the absolute upper limits of hardware or gaming. The 120 FPS backend is not delivered this time.


## 1.7.5-adb preview

206 self-tests passed. In fact, Tkinter connected to the mobile phone and maintained the observation mode for about 10 seconds. The final measurement achieved 54.0 FPS for recognition and 55.1 FPS for preview (the timing of the last 90 successful drawings on the host side). The old preview is released every 150ms, with a theoretical upper limit of about 6.7 FPS, which cannot be mixed with the identified FPS. Closing the preview and disconnecting will clear the preview count; this test does not send game input and does not mean that 55 FPS will be maintained in all states.


## 1.8.1-adb responsive and mobile preview

- 239 self-tests passed, including different size/aspect ratio arrangements, narrow window operation bar, complete mobile preview data, maximize/restore and keyboard-enabled enlarged preview.
- The Windows Qt interface is maximized for inspection at 680×600, 700×650, 700×850, 900×700, 900×1100, 1250×900 and 2560×1440; main controls are visible, and narrow vertical settings can be scrolled.
- Real machine read-only observation: mobile phone streaming is 360×800, and the full preview screen remains at 360×800; approximately 59.4 FPS for recognition and 55.6 FPS for actual preview drawing. No game input is sent in this section; performance of animations, desktop scaling, and other phone sizes may vary.
- Use the simulated backend to test device selection, connection, start, pause and interruption; long-term automatic phishing was not tested in this interface verification.
