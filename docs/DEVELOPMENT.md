# Development and verification

English · [繁體中文](DEVELOPMENT.zh-TW.md) · [日本語](DEVELOPMENT.ja.md) · [한국어](DEVELOPMENT.ko.md)

This page describes the legacy emulator and desktop development path. For the current Android phone app and Windows installer, start with [ADB mobile development](ADB.md) and [Windows installer](INSTALLER.md).

## Structure

- `main.py`: Tkinter interface, window selection, settings and preview switches.
- `fisher/vision.py`: Image normalization, color and local template recognition.
- `fisher/controller.py`: Fishing phase, count limit, result retry and action submission.
- `fisher/phase.py`: Proportional coordinates, triangular wave motion phase, two-way arrival time and same trip deduplication.
- `fisher/runtime.py`: Fixed frequency screenshots, cancelable independent key duration, control commands and input coordination.
- `fisher/scheduling.py`: Screenshot rhythm and shortcut key edges.
- `fisher/speed.py`: Reference speed, explicit robust calibration and local parameter saving.
- `fisher/contact.py`: Shared bounded delay compensation and historical strategy comparison implementation.
- `fisher/emulators.py`: LDPlayer/MuMu title filtering, manual selection fallback and selection ownership verification.
- `fisher/windows.py`: Window coordinates, foreground checks and space injection/release.
- `fisher/config.py`: Configuration verification, migration and atomic save.
- `fisher/packaging.py`: Public file listing and ZIP integrity check.
- `desktop.py`, `build_windows.py`: Optional portable startup and build tools.

The source code runs starting from `main.py`, and the official interface uniformly selects the `phase` strategy. The historical `contact` and `center` implementations only retain compatibility and regression controls; their tests explicitly fix the original configuration and do not regard historical high-frequency samples as low-frequency strategy verification.

`ROOT` is for static resources and `DATA_ROOT` is for local settings. Synchronize `PUBLIC_FILES` when adding public files. Do not add local configuration, diagnostic data or the entire screenshot directory to the list.

## Decision and input

The controller only proposes actions and `commit()` after successfully calling the system input. The future HIT of the phase strategy enters the only pending execution slot; each new picture replaces the old plan, and unknown pictures or non-judgment stages cancel the plan. The loop also handles keystroke expiration during the screenshot interval, without using blocking calls that wait for several seconds. When the deadline is approaching, screenshots will be postponed and input will be processed first.

The phase plan cannot apply the 80/120 ms frame age limit of the historical strategy; its prediction range is constrained by the current phase and the next observation. F9, out of focus, window change and exit still cancel the input. The motion phase is retained after input; the same trip lock is released after leaving the target, and the next round can be started when the target changes.

The record and claim styles of the result page share a waiting/retry process. Wait after the first confirmation, and then retry every second for subsequent appointments; stop the closing action if you do not confirm or leave the result page. Don’t accept the initial fishing interface as happy just because of the green button. The Accept button matches the white text mask and caches a limited size template of 0.90 to 1.15 times; it is only executed after the green area, dark background and title are confirmed, and the original local search position and the minimum 0.72 threshold are maintained.

`TRIAL_BUILD=False` is an official build, does not create a trace recorder or session log, and does not export a ZIP when paused. The historical diagnostic module is only retained as an explicit development tool and regression dependency. Manual playback and test output are not part of the normal fishing operation path.

For timing algorithms and boundaries, see [Algorithm Description ](ALGORITHM.md). The current model assumes uniform speed and does not treat long game pauses as a solved problem; low-frequency screenshots should not claim that any direction and speed can be uniquely inferred.

## verify

```bash
python selfcheck.py
python replay.py
python build_release.py
```

Self-test does not send system keystrokes. `test_phase.py` includes simulating a complete runtime loop: sampling at 100 milliseconds and 500 milliseconds respectively, performing HIT between two screenshots; verifying left and right reentry, narrow strips, multi-round targets, normalized zoom, pause/out of focus/unknown/size change cancellation, and calibration without increasing capture frequency and no automatic running data generation. Old strategies, settlement, screenshot budget, shortcut keys, input release, privacy and packaging boundaries continue to return.

The test material uses necessary local game controls and desensitized frame selection examples. Synthetic trajectories and video playback cannot prove the actual game success rate, and offline inspection should still be distinguished from Windows native window, DPI, multi-screen and real simulator verification.

When configuration version 7 is upgraded for the first time, continuous fishing is enabled, the old default sampling interval of 30 is changed to 6, and other custom sampling values, shortcut keys, waiting and other settings are retained. Saved selections in the new version are no longer overwritten by default values; old selections are only reused if the ownership, title, and size are consistent. The explicit calibration switch is only valid for this monitoring. Velocity files only allow scale and statistics fields and do not save raw trajectory or window information.

Perform self-checks and public packaging before submission, and check that there is no private local information in the source code manifest, sample configurations, and images. Distribute in compliance with LICENSE and retain third-party material notices. Optional portable build see [WINDOWS.md](WINDOWS.md).
