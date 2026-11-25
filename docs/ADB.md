# ADB mobile mode

English · [繁體中文](ADB.zh-TW.md) · [日本語](ADB.ja.md) · [한국어](ADB.ko.md)

Connect an Android phone over USB from a Windows computer. Phone-side installation and root access are not required.

## Getting started

1. Install the Windows x64 release and prepare Android SDK Platform-Tools and FFmpeg as described in the [installer guide](INSTALLER.md).
2. On the phone, enable USB debugging, authorize this computer, and open the game in portrait orientation.
3. Open tt tool. It connects automatically when exactly one authorized phone is available. Otherwise, select the phone and connect.
4. After selecting the activity, open "Settings", select "Automatic Learning" or "Manual Settings", and preview the corners and operating points of the drag range on your phone; the timing and evacuation threshold can be adjusted with the slider, and the default can be restored. The settings of the two modes are saved separately and applied immediately after saving.
5. Press "Start Fishing" or the space bar to start, and press again to pause; the count and session time are retained during the pause. Press "End" or Esc to end the session and start counting again next time.

If the screen does not change after setting the hook or pulling the hook, mobile phone fishing will automatically retry after confirming that the screen is still stable; retrying the same hook will not display the count repeatedly. When the screen cannot be confirmed temporarily, it will continue to observe and continue after the recognition is restored. When setting the upper limit of the number of hooks, retries will also be included in the upper limit of the number of operations; the time limit is still valid.

## ruins adventure

Select "Ruins Adventure" on the main screen. When switching, the originally executed mode will end and reconnect; open the phone on the ruins exploration page and press "Start Adventure" or the space bar. The program recognizes the entrance, advancement, treasure pop-up window and settlement, and continues to the next round after accepting it. Use the space bar to pause and resume; press End or Esc to end the session.

When encountering the treasure chest reward page, the program will recognize the button at the bottom, automatically open the next group or all remaining treasure chests, and confirm the final reward before continuing the adventure; button recognition does not rely on text.

The boss screen is judged by the total winning rate after the basic winning rate plus teammate bonuses. By default, the evacuation rate for general treasures is less than 45%, and the evacuation rate for red treasures is less than 30%. The two thresholds can be adjusted or restored to default in the adventure settings. Click on each operation and wait for the screen to change; if the screen remains unchanged, try again after confirming and waiting. When simulated manual is enabled, the landing point and pressing time will change within a limited range. The boss's winning rate needs to be confirmed on multiple screens; if the winning rate cannot be confirmed, the readings are conflicting, or the treasure type is unknown and will affect the decision-making, continue to observe for about 2.5 seconds and then fight automatically. The interface displays the currently recognized winning rate and decisions; it will only send clicks after confirming that the game is still in the foreground and the screen is valid.

Fishing and exploration will identify game errors based on the color, shape and button position of the prompt window. After confirmation, press the green button; if the screen remains unchanged, the retry interval will be extended. The entrance, hook and prize recognition do not match specific Chinese characters. The boss win rate still requires identifying the numbers, percent sign, and plus sign on the screen.

If ADB reports that the input result is unknown, the program will wait for the screen to change; fishing will retry when the operation confirmation times out and the same operable screen continues to be stable; exploration will re-recognize the screen after 12 seconds. When paused, disconnected or the screen cannot be confirmed, the screen will be reconfirmed before operation.

## Foreground switching and yellow bar prediction

When other apps or floating windows obtain the foreground, the session remains enabled and clicks are paused on the phone; the game will automatically continue after confirming that it has regained the foreground. Timeouts related to the game screen will not be advanced during the waiting period, but the upper limit of the session time is still calculated based on the actual time. This will not send clicks to widgets in other apps.

The yellow bar uses phase prediction projected to the moment when the touch takes effect. The target is near the entrance of the yellow bar safe zone and sets an upper limit on the effective time. After clicking in the previous round, only two consecutive frames confirm that the new yellow bar is not blocked by the pointer, and the next hit can be planned after a short interval; when the change cannot be confirmed, the original repeated click protection is retained. Predictions are still affected by streaming latency, touch latency, and recognition errors.

After the settings are saved, they will be applied in the control thread. Switching activities ends the current session and reconnects. Automatically learns to correct limited positional offsets from confirmed local control items; manual settings are based on the range and point operations dragged by the user, and automatic correction is not read or updated. The mobile phone settings are only stored in the local machine `phone_settings.json`, and the interface language is stored in `tt_tool_ui.json`. Automatic corrections are stored separately as `device_profiles.json` by device hash, resolution, activity and selection; original device serial numbers, accounts or screenshots are not saved. Automatic correction can be reset in settings.

## Screenshots and timing

Use a PNG screenshot to obtain the original size and selection when connecting for the first time. Normal execution uses the `adb exec-out screenrecord` AVC stream instead, and FFmpeg continuously decodes into 360-pixel-wide frames; a latest frame slot avoids accumulated recognition work. The preview is only drawn when it is turned on; the interface displays the frame rate of decoding reception, recognition and actual preview drawing respectively.

The video streaming uses the `--time-limit 0` supported by the mobile phone for continuous output; when the streaming ends unexpectedly or the device is temporarily disconnected, it will continue to reconnect and wait for new images. If older versions of Android do not support this parameter, additional adaptation is required. Clicks will no longer be sent when FFmpeg does not exist, the stream is stopped, the device is disconnected, the screen expires, the landscape is rotated, or the foreground app changes. The foreground check uses an independent execution thread, and the check results are not entered when they expire.

The yellow bar follows the original round-trip phase prediction, but first requires continuous movement of the sample and confirmation of the direction to avoid assuming that it is always to the right at the beginning. Yellow bar clicks will not be sent when the frame is frozen for a long time or the direction is unknown. If the target time window is smaller than the set uncertainty margin, the trip will be skipped.

`Estimated stream latency (ms)` presets 60ms, `Touch latency compensation (ms)` presets 80ms, and `Timing uncertainty margin (ms)` presets 12ms. All are initial estimates, not automatically measured end-to-end data. Subject to USB, phone, game, and Windows schedule adjustments; not guaranteed for every fish or yellow bar hit. The frame interval, screen age and input command time in the interface are measured on the host side, and the return of the ADB command does not mean that the touch actually takes effect.

## Mobile phone screen adaptation

The proportion of controls is retained based on the width of the screen, and the operating area is aligned at the bottom for long screens; the record pop-up window is positioned with a weight icon and then submitted to multi-condition judgment for confirmation. The ordinary close page combines the dark background, golden title area, green rectangular button and white pixel distribution recognition, and independently positions the close button without comparing specific fonts. The frame selection uses the original mobile screen ratio; when sending a click, it returns to the physical pixels of the mobile phone.

## verify

`python selfcheck.py` executes existing regression and mobile phone offline tests without sending input.
`python build_release.py` creates a source code ZIP that excludes local data.

Mobile phone actual testing, synthetic screen testing, and offline playback can only prove the corresponding range, and the number of tests cannot be used to infer the long-term actual success rate.

> The following sections record historical development versions and measurements.

Earlier mobile development builds required Python 3.10 or later. Their source setup used `python -m pip install -r requirements.txt`, then `python qt_fishing.py` or `start_adb.bat`. The historical emulator entry was `main.py`, and `python adb_app.py` opened the earlier mobile interface.

## 1.7.1 Update

The default recognition interval is 0.01 seconds, and the actual upper limit is still determined by the frame frequency of the mobile phone encoding stream. The new picture wakes up the control loop through events and retains the latest frame slot. The actual measurement of the normal/yellow bar phase of the mobile phone is about 55~60 FPS, which will drop temporarily during the input command and settlement recognition; it is not claimed to reduce the end-to-end delay by the same multiple.

The "Pull Hard" prompt no longer relies on the `bite.png` template with simplified Chinese characters: after the purple prompt panel, yellow horizontal bar and purple round button below are jointly confirmed, the first confirmation screen will pull the hook without waiting for the end of the progress bar. The retractor button is positioned independently and waits for stage changes after delivery to avoid repeated retraction.

## 1.7.2 Settlement acceleration

After confirming the settlement page for the first time in the mobile phone mode, wait 0.25 seconds and then try to accept it. If it is still stuck on the confirmed result page, try again at the 0.35 second benchmark interval (retaining the original slight jitter).If the game animation is not ready for input, the first click may not close the page. Adjust the timing settings and reconnect to apply them. The emulator mode retains its original defaults.

## 1.7.3 Manual operation simulation

The current settlement first wait is defaulted to 1 second. When "Simulate manual operation" is checked:

- The click point changes within a circle near the center with a radius of 0.8% of the short side of the game selection, and is limited to the selection.
- The short reaction time is increased by 40~120ms for lowering the hook, 15~40ms for retracting the hook, and 30~90ms for retraction.
- Non-yellow bar operations use the same coordinates to press/lift, press for 35~75ms, and do not drag.
- Settlement retry floats ±100ms around the set value.
- The yellow bar only changes the landing point, and still uses the original predicted time and ordinary clicks to avoid damaging the hit window.

You can uncheck the box to restore the fixed landing point and no additional response delay; the settings need to be reconnected to apply. These are input changes, not a model calibrated to real-person data, and are not guaranteed to avoid game detection.

## 1.7.4 Foreground inspection and frame rate evaluation

Input is not sent when a transient query fails, focus is transferred, or the foreground result expires, but the running status is not cleared immediately. Reconfirm that it is the same game and continue; it will be officially suspended after confirming the same other app for at least 1 second and three or more times. If the uncertain state lasts for 3 seconds, "Prospect verification continues to fail" and the actual reason will be displayed; after the actual pause, it still needs to be started manually.

In the experiment of native scrcpy 4.0 setting `--max-fps=120` and encoding frame-rate=120, the effective segment for about 3.95 seconds before crash was still about 61 FPS. The scrcpy native program ends with an exception of 0xC0000005, so this experiment cannot prove a long-term frame rate cap, nor can it be used as a stable alternative backend. Currently retaining the authenticated original stream without using fill/duplicate frames to claim 120 FPS.

The mobile screen can support 120Hz, which does not mean that the current game screen, encoding path and capture pipeline provide 120 new screens. The max-fps of scrcpy is the upper limit setting. For related implementation, please refer to [Official development document ](https://github.com/Genymobile/scrcpy/blob/master/doc/develop.md). To truly double this, you still need to verify game output and a stable high frame rate capture backend.

## Rounded corner interface

The new desktop interface uses PySide6. The upper part of the window can be dragged and moved, and the upper right corner can be minimized or closed. Customizable rounded corner buttons, settings tabs, and status areas provide transition animations. Connect, observe, start, pause and ADB input still use the original mobile backend. After changing settings or box selections, you need to reconnect to apply; closing the window will stop the session started by the window. The new version will not automatically take over or stop the open windows of the old version.

## 1.8.1 Window and full preview

When the desktop interface is started, the default size is set based on the available screen space, with an upper limit of 1180×900; the manual adjustment range is 680×600 to 3840×2160 logical pixels, subject to display scaling and actual screen limitations. The upper right box will enlarge the window to the available area of ​​the current screen (not exceeding the upper limit), press again to restore; the lower right corner can be dragged to resize.

When the width is less than 760 and the window is vertical, or when the width is less than 1200 and the aspect ratio is less than 0.85, it is changed to top-down arrangement, and the start/pause is fixed at the bottom; for the rest, the left and right columns are used. Narrow horizontal windows will change the X/Y columns to be arranged up and down; when the height is lower than 760, the top area will be reduced. The main content of the ultra-wide window is kept within approximately 1680 logical pixels to avoid excessive elongation of the input field. The settings area scrolls as needed.

The preview uses the entire mobile phone stream instead of the 336×598 cropped screen for recognition; the outer frame is scaled according to the image aspect ratio and rounded corners are applied. Display resolution is still limited by ADB streaming, and rounded corners obscure very few corner pixels. Click on the preview, or focus on the preview and press Enter/Spacebar to open a larger live screen. Preview FPS is calculated based on the actual number of new frames drawn; may drop when the viewport is obscured or hidden. The original Tk interface still retains the recognition annotation preview.
