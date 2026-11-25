# Windows x64 installer

Download [tt-tool-1.3.0-windows-x64-setup.exe](https://github.com/Estrella-071/tt-tool/releases/download/v1.3.0/tt-tool-1.3.0-windows-x64-setup.exe) for Windows 10 22H2 or Windows 11 on x64. The installer includes Python, Qt and the local image recognition dependencies. Phone connectivity also requires [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) and [FFmpeg](https://ffmpeg.org/download.html#build-windows).

## Install and open tt tool

1. Start Setup and select English, 繁體中文, 日本語 or 한국어. The app uses this language on its first launch.
2. Review the GPL license on its own scrollable page. The Setup interface supports all four languages.
3. On a first install you can change the folder. By default, Setup installs for the current user under `%LOCALAPPDATA%\Programs\tt tool`.
4. Choose which shortcuts to create. The Start menu shortcut is selected by default. The desktop shortcut is off by default.
5. On the final screen, select the launch option if you want to open tt tool when Setup finishes. You can also use a shortcut later. An installation folder shortcut named **tt tool** is available even when both external shortcuts are off.

Add the folders containing `adb.exe` and `ffmpeg.exe` to the user `Path` and reopen tt tool. For a custom ADB installation, choose **ADB tool location…** in the device menu. Use the app's **USB connection guide** or the [manufacturer reference](USB-DEBUGGING.md) to prepare the phone. The phone's Android build must support `screenrecord --time-limit 0`.

## Update tt tool

**From v1.2.0 or earlier**, download v1.3.0, close tt tool and run Setup in the existing installation folder. This enables in-app installation for future updates.

For an installed copy of v1.3.0 or newer, choose **Maintenance → Check for updates**. The app checks the latest stable release on GitHub when you ask. If a verified installer is available, **Download and install** starts a download you can cancel. After comparing the SHA-256 hash with the release asset's digest, the app asks for permission to stop the current activity, close the window and install the update in place. Setup shows progress and the updater reopens tt tool after installation.

The updater cleans up its temporary installer after a completed or failed update or a cancellation. Choose **Open releases** if an in-app update is unavailable, or if you run from source. From the release page, you can download the installer and apply it manually. Updates keep your settings, interface language, calibration and local logs.

## Find files or uninstall

From **Maintenance**, choose **Open file location** or **Open settings folder**. If moving from a source checkout, close both copies before transferring `phone_settings.json` and `tt_tool_ui.json` to `%LOCALAPPDATA%\tt-tool\data`.

For installed copies, choose **Uninstall…** in tt tool or remove the app from **Installed apps** in Windows Settings. The confirmation shows the installation folder. If you start in tt tool, it asks before ending the activity and closing the app. The uninstaller shows progress, reports the result, and lets you open the latest stable release notes in your browser.

Settings, calibration and local diagnostic logs remain in `%LOCALAPPDATA%\tt-tool\data` by default. Select **Also delete local tt tool data** to remove that folder too.

## Verify a download

Setup identifies **71** as the publisher. The installer has no Authenticode signature, so Windows may display **Unknown publisher**. For a manual download, compare its SHA-256 hash with the [checksum manifest in the same GitHub release](https://github.com/Estrella-071/tt-tool/releases/download/v1.3.0/SHA256SUMS.txt).

```powershell
Get-FileHash .\tt-tool-1.3.0-windows-x64-setup.exe -Algorithm SHA256
```

## Build and verify an installer

Use Windows x64, Python 3.12 and [Inno Setup 7 x64](https://jrsoftware.org/inno-setup/downloads). Prepare the Python development environment in the [README](../README.md) before running these commands from the repository root.

```powershell
.\.venv\Scripts\python.exe selfcheck.py
.\.venv\Scripts\python.exe build_tt_tool.py --iscc "C:\Program Files\Inno Setup 7\ISCC.exe"
```

The build checks every dependency against the locked manifest, stages a standalone runtime and checks Qt startup. The installer goes in `dist\`. Run `.\.venv\Scripts\python.exe build_tt_tool.py --check-payload` to verify the runtime separately.

Build from the commit you intend to release. Use the [Windows installer workflow](https://github.com/Estrella-071/tt-tool/actions/workflows/tt-tool-installer.yml) to verify installation, shortcut launch, updating and uninstalling on Windows. Use the EXE and checksum manifest from that run, and point the release tag to the verified commit.

[Third-party components and source code](THIRD-PARTY.md)
