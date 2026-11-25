# Crack Cleaning: Chronomodels and Evidence

English · [繁體中文](SWEEP-TIMING.zh-TW.md) · [日本語](SWEEP-TIMING.ja.md) · [한국어](SWEEP-TIMING.ko.md)

> This technical record includes historical versions and measurements. For current setup and supported workflows, see [the main guide](../README.md).

## sample

- Android 1.1.6, versionCode 120733181, arm64-v8a. The three APKs installed by the emulator are consistent with the SHA-256 of the local save file; the arm64 split is `7fdd866a18ae22c139e84be7ab2c5a2dded7a5e000961f3cd3e49c12cb662103`.
- `libil2cpp.so` SHA-256: `1223d55a9903364c283fac07f96102410c8adec128add3888e9cb4fb80c67e9c`. The following addresses are ELF virtual addresses, the actual file offset must be converted according to PT_LOAD; do not regard the original disassembly in the Cpp2IL output as the machine code of the correct address.

## Game logic

- `PopupRiftSweepMinigame.PlayTiming` (0x57e6ed8) pumps a round trip time `T` with `Random.Range(minRoundTripTime, maxRoundTripTime)` each time, starting from position 0, and the speed is set to `2/T`.
- `TimingGauge.Update` (0x57c4680) Updates with `position += velocity * Time.unscaledDeltaTime` every frame; clip to endpoint and reverse when bar mode reaches 0 or 1. The portion beyond the endpoint is not preserved by ideal reflection.
- `TimingBarGauge.ToX` (0x57c4308) converts the internal location to `(position - 0.5) * trackWidth`. The picture must remain intact and unobstructed; the scaled pixel coordinates are not internal game coordinates.
- `TimingGauge.Judge` (0x57c47bc) compares half of the width of each judgment area with `abs(position - center)`; bar mode uses this distance directly. `ShowResultAsync` Stop the pointer first and then make a judgment.
- The read-only execution period data shows `perfectRatio=0.04`, `coolRatio=0.2`, `niceRatio=0.4`, `minRoundTripTime=0.7`, and `maxRoundTripTime=1.8` of this sample. These are observations from sample builds and screen settings, other builds or content may differ.

## Assistant models and limitations

The assistant tracks the pointer and the center of the yellow area from the screen; uses the median of paired speeds in the same direction over a period of time to estimate the speed to reduce capture time jitter. It only predicts the current trip and does not assume that it can bounce through the endpoint without loss; it re-estimates the speed after observing the reverse direction. Calibration estimates picture and input lag and corrects the unit's lag settings with each actual stop. This model does not read or modify game memory and does not rely on root.

In a non-stop input observation of Raiden, the window captured about 122 FPS; comparing the screen with the simultaneous read-only game position, it is estimated that the display lags about 23 ms. Another observation of the ADB stream estimates around 100 ms. These numbers include sampling and synchronization errors and should not be considered fixed delays for other computers. In the offline replay of the window observation, except for the initial crossing that lacked complete comparison data, the subsequent four predictions all fell into the internal Perfect interval; this is not the actual key hit rate.

It cannot be inferred from the above that every hit is guaranteed: screen updates, system scheduling, and input lag will all fluctuate. Actual game test results and execution file verification must be reported separately.

## Actual measurement of windows and spaces

After binding a space at the start/stop position, the Thunderbolt Simulator uses Windows windows to capture and simulate space operations; does not use ADB or root. After one miscalculation, the game is closed and reopened before the second stop, and the vote count is still 10. Subsequently, a manual test script and a full Qt interface test were completed each, and both calculations based on the frozen screen fell into the yellow area; the two center errors of the Qt interface round were approximately 0.81% and 0.13% of the screen width. Another complete interface test did not retain two screenshots, so the judgment was not inferred. This is just a small sample of the same computer and is not a guarantee of hit rate or other computers.

## Capture interval and misalignment analysis

The median acquisition interval for an execution of the old interface is approximately 6.3 ms, the 95th percentile is 28.4 ms, and the maximum value is 131 ms; previewing the entire image and judging share the same thread. After moving the window preview to a separate thread and defer writing the calibration file, an observation with no game input resulted in a median of 8.9 ms, a 95th percentile of 17.8 ms, and a maximum of 97.1 ms. The two loads are not the same and cannot be considered a controlled performance comparison.

In the actual measurement of the windows and spaces after the modification, the first screen was interpreted as yellow, and the second screen and user observation were both premature and purple. Based on the estimation of the continuous screen, the time from the position seen before the button is pressed to the frozen position is about 80 ms and 65 ms respectively; the second yellow half-width only allows about 7 ms. This estimate includes screen delays and capture errors, and cannot be regarded as an accurate time of in-game events, but it shows that the current process still cannot guarantee a hit. The new protection will re-estimate the speed when the window capture interval exceeds 35 ms, and the system fails to wake up within 6 ms after the scheduled time to cancel the unsent keystrokes and wait for the next pass. It cannot detect all inputs or exhibit latency changes.
