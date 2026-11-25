# Windows x64 安裝包

在 [tt tool Releases](https://github.com/Estrella-071/tt-tool/releases) 下載 `tt-tool-1.0.1-windows-x64-setup.exe`。安裝適用於 Windows 10 22H2／Windows 11 x64，在當前使用者的開始選單建立 **tt tool**。Python、Qt 和影像辨識套件已隨附。連接手機需要 [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) 和 [FFmpeg](https://ffmpeg.org/download.html#build-windows)。

啟動安裝程式後先選擇繁體中文、English、日本語或 한국어。首次安裝時工具沿用這個語言。更新版本時，工具保留既有的語言偏好。

將 `adb.exe` 和 `ffmpeg.exe` 所在資料夾加到使用者的 PATH，再重新開啟應用程式。也可使用主畫面「選擇 adb.exe」指定 ADB。用新開的 PowerShell 執行 `adb version` 及 `ffmpeg -version` 可確認 PATH。Android 的螢幕錄影需支援 `screenrecord --time-limit 0`。

設定存在 `%LOCALAPPDATA%\tt-tool\data`。升級前先關閉 tt tool，再執行新版安裝程式。可從 Windows 已安裝的應用程式解除安裝，個人設定保留。如果原本使用從原始碼啟動的版本，可在兩邊均關閉時把 `phone_settings.json` 和 `tt_tool_ui.json` 複製到資料目錄。

安裝程式未進行 Authenticode 簽章。可用 PowerShell 計算 SHA-256，和同一 Release 的 `SHA256SUMS.txt` 比對。

```powershell
Get-FileHash .\tt-tool-1.0.1-windows-x64-setup.exe -Algorithm SHA256
```

## 維護者

使用 Windows x64、Python 3.12 和 [Inno Setup 7 x64](https://jrsoftware.org/inno-setup/downloads)。在專案根目錄執行以下指令。

```powershell
python selfcheck.py
python build_tt_tool.py --iscc "C:\Program Files\Inno Setup 7\ISCC.exe"
```

建置逐一驗證固定清單中的相依檔案，建立獨立運行環境並啟動 Qt 檢查。輸出在 `dist\`。單獨驗證運行環境可用 `python build_tt_tool.py --check-payload`。只從要發布的乾淨提交建置，並在 [GitHub Actions](https://github.com/Estrella-071/tt-tool/actions/workflows/tt-tool-installer.yml) 執行安裝、捷徑啟動、覆蓋安裝和解除安裝驗證。用該次建置的 EXE 和校驗檔建立 Release，將標籤指向該次驗證的提交。

[第三方元件與原始碼](THIRD-PARTY.md)
