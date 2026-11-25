# Yellow bar click timing

English · [繁體中文](ALGORITHM.zh-TW.md) · [日本語](ALGORITHM.ja.md) · [한국어](ALGORITHM.ko.md)

> This technical record includes historical versions and measurements. For current setup and supported workflows, see [the main guide](../README.md).

Screenshots and keystrokes use two independent periods: the default interval between screenshots is 100 milliseconds; a pending keystroke is checked individually by the control loop without waiting for the next screenshot. The control loop usually yields the thread every 10 milliseconds and waits for the remaining time when the key press deadline is approaching. Actual wake-up accuracy still depends on Windows scheduling.

## round trip motion

The visible frame width of the track is 1, and the default speed is 0.606 lines per second. The left and right endpoints of the fish float center adopt 0.083 and 0.940 in the same coordinate system to avoid taking the track decoration as the center stroke; one trip is about 1.41 seconds. The normalized image is only used for control positioning, and the speed does not depend on the original screen resolution.

The motion phase always increases forward and the position is mapped to the orbit by the triangle wave. Reaching the endpoint only reverses direction and does not reset speed. The first identification defaults to the right, and then it automatically crosses the endpoint based on time. The new screenshot projects the position to the round-trip branch closest to the prediction to avoid guessing the direction based on the displacement sign of the two images. Multiple rounds of yellow bars continue to use the same phase of movement.

## Click rules

- Predict the observation position to the time when the input takes effect; click immediately when it is still within the yellow range, otherwise make a reservation for the next pass.
- Not yet entered: Calculate the time to pass through the middle of the yellow bar next time, and schedule a click after deducting the input delay. Both the left and right directions and the path that needs to be turned back first are involved in the calculation.
- When the yellow bar is very narrow, the middle part is still calculated, and clicks are not prohibited because the fixed pixel margin is larger than the bar width.
- A plan to be executed will be updated by the next picture; unknown pictures, other stages, pauses, out-of-focus or window size changes cancel the plan.
- You can click at most once on the same trip; if the yellow bar changes, you can enter the next round. When the yellow bar does not change, you can retry the next time you pass it after leaving, without relying on permanent locking or limited retries.
- When the fish float blocks the yellow color, it retains the complete boundary that has been confirmed and avoids treating the remaining small segment of color as a new target.

When the key is near, the input is processed first and then the screenshot is taken. All plans retain the current window and emergency pause checks and do not use long non-cancelable hibernations. After the entire hit window has passed, the next pass is recalculated.

## Speed ​​and latency

The fixed speed is read from the local calibration file, and the reference value is used when not saved. After explicitly checking the calibration, only the same direction interval in normal sampling is used; the starting point of the interval is retained at high frequency, and the speed is estimated again after accumulating at least 0.25 seconds, and the interval is retaken after pressing the key or turning back; cross-end points, near input motion effects, zero displacement and obvious abnormal speeds are excluded, and outliers are screened out by the median and MAD. After the bidirectional samples are stable, the ratio, number of samples, and dispersion will be saved and the calibration will be stopped; the original trajectory will not be saved, and no additional screenshots will be encrypted.

The game response delay benchmark defaults to 40 milliseconds and can be adjusted manually. The local compensation only measures the measurable part from the planned time to the system input execution, and there are upper limits for single adjustment and total compensation; it is not equal to the internal receiving time of the game, nor does it claim to measure the complete game delay based on screen changes.

## applicable boundary

This strategy assumes approximately uniform motion between the two screenshots, with the first direction going to the right. Low-frequency screenshots may miss the short hook prompt, and cannot determine any direction, speed, and pause at the same time; when the yellow bar is restarted midway, the first direction may be opposite to the actual one. It is recommended to start when preparing to set the hook. Game pauses, significant speed changes, prolonged system congestion, or visual misses may still result in missed/accidental presses.

Freeze frame detection is currently not used to block scheduled input. Image recognition still requires complete frame selection and the game layout can correspond to the template; changing the aspect ratio requires re-adaptation when the controls are rearranged, and proportional speed cannot replace visual adaptation.

Screenshots, traces, logs or diagnostic packages are not automatically saved during runtime. Only manual screenshots/recordings and explicit calibration will be written to the corresponding native file.
