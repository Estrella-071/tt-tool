# Windows x64 installer

Download [tt-tool-1.1.0-windows-x64-setup.exe](https://github.com/Estrella-071/tt-tool/releases/download/v1.1.0/tt-tool-1.1.0-windows-x64-setup.exe) for Windows 10 22H2 or Windows 11 on x64. The installer includes Python, Qt and the local image recognition dependencies. Phone connectivity also requires [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) and [FFmpeg](https://ffmpeg.org/download.html#build-windows).

## Install and open tt tool

1. Start Setup and select English, 繁體中文, 日本語 or 한국어. The app uses this language on its first launch.
2. On a first install you can change the folder. By default, Setup installs for the current user under `%LOCALAPPDATA%\Programs\tt tool`.
3. Choose which shortcuts to create. The Start menu shortcut is selected by default. The desktop shortcut is off by default.
4. On the final screen, select the launch option if you want to open tt tool when Setup finishes. You can also use a shortcut later. An installation folder shortcut named **tt tool** is available even when both external shortcuts are off.

Add the folders containing `adb.exe` and `ffmpeg.exe` to the user `Path` and reopen tt tool. You can point to ADB from **Choose adb.exe** in the app. In a new PowerShell window, run `adb version` and `ffmpeg -version` to check that PowerShell can find them. The phone's Android build must support `screenrecord --time-limit 0`.

## Update, find files or uninstall

Open **Maintenance** at the bottom of the app. **Check for updates** reads the latest GitHub release on request. If a newer version is available, confirm to open its release page in your browser. Download the installer, close tt tool and run Setup again. The app keeps its existing language and settings during an update. Use **Open file location** to find the app or **Open settings folder** to find its data.

For installed copies, choose **Uninstall…** to start the Windows uninstaller. You can also remove the app from Windows Settings under **Apps**. Your settings, calibration and local diagnostic logs remain under `%LOCALAPPDATA%\tt-tool\data`. If moving from a source checkout, close both copies before transferring `phone_settings.json` and `tt_tool_ui.json` to this directory.

## Verify a download

The installer is distributed without Authenticode signing. Compare its SHA-256 hash with `SHA256SUMS.txt` from the [same GitHub release](https://github.com/Estrella-071/tt-tool/releases/tag/v1.1.0).

```powershell
Get-FileHash .\tt-tool-1.1.0-windows-x64-setup.exe -Algorithm SHA256
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
