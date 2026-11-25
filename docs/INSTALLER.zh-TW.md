# Windows x64 安裝指南

[English](INSTALLER.md) · [繁體中文](INSTALLER.zh-TW.md) · [日本語](INSTALLER.ja.md) · [한국어](INSTALLER.ko.md)

[下載 tt-tool-1.0.6-windows-x64-setup.exe](https://github.com/Estrella-071/tt-tool/releases/download/v1.0.6/tt-tool-1.0.6-windows-x64-setup.exe)，適用於 x64 的 Windows 10 22H2 或 Windows 11。安裝程式包含 Python、Qt 與本機影像辨識套件。連接手機另需 [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) 與 [FFmpeg](https://ffmpeg.org/download.html#build-windows)。

## 安裝與開啟

1. 啟動安裝程式，選擇 English、繁體中文、日本語或 한국어。首次開啟工具會沿用所選語言。
2. 首次安裝可更改資料夾，預設為目前使用者的 `%LOCALAPPDATA%\Programs\tt tool`。
3. 選擇捷徑。開始選單捷徑預設勾選，桌面捷徑預設不勾選。
4. 最後可選擇安裝完成後啟動。也可稍後使用捷徑，即使未選擇外部捷徑，安裝資料夾內仍有 **tt tool** 捷徑。

安裝資料夾包含完整 GPL 授權，也可從 **工具維護 → 查看授權** 閱讀。

tt tool 會從使用者的 `Path` 尋找 `adb.exe` 與 `ffmpeg.exe`。從裝置選單開啟 **連線工具** 可直接指定執行檔，然後選 **檢查並重試**。依工具內的 **USB 連線教學** 或[各品牌指南](USB-DEBUGGING.zh-TW.md)設定手機。手機 Android 必須支援 `screenrecord --time-limit 0`。

## 更新

若工具顯示舊版本號 v1.1.0、v1.2.0 或 v1.3.0，請關閉工具，在原安裝資料夾執行 v1.0.6 安裝程式一次。設定會保留，此後可使用新版本系列的程式內更新。歷史版本 v1.0.2 至 v1.0.4 保留原安裝程式與校驗值。

已安裝 v1.0.5 或更新版可選 **工具維護 → 檢查更新**。工具在你要求時查詢 GitHub 最新穩定版本。若可取得已驗證安裝檔，選擇 **下載並安裝** 可開始下載，下載可取消。工具比較 SHA-256 後會詢問是否停止目前活動、關閉視窗並在原位置安裝。安裝時顯示進度，完成後重新開啟工具。

更新完成、失敗或取消後會清除暫存安裝檔。無法程式內更新或從原始碼執行時，可選 **開啟發布頁** 手動下載安裝。更新保留設定、介面語言、校準與本機記錄。

## 檔案與解除安裝

從 **工具維護** 選 **開啟檔案位置** 或 **開啟設定資料夾**。從原始碼版本移轉 `phone_settings.json` 和 `tt_tool_ui.json` 至 `%LOCALAPPDATA%\tt-tool\data` 前，先關閉兩個程式。

安裝版可從工具內選 **解除安裝…**，或使用 Windows 設定的 **已安裝的應用程式**。確認畫面顯示安裝資料夾，從工具啟動時會先詢問是否結束活動並關閉程式。解除安裝會顯示進度與結果，並提供開啟最新穩定版本說明的按鈕。

設定、校準和診斷記錄預設保留於 `%LOCALAPPDATA%\tt-tool\data`。勾選 **一併清除 tt tool 的本機資料** 才移除此資料夾。

## 驗證下載

安裝資訊的發行者為 **71**。安裝程式沒有 Authenticode 簽章，Windows 可能顯示 **未知的發行者**。手動下載時，可與[同一 GitHub 版本的校驗檔](https://github.com/Estrella-071/tt-tool/releases/download/v1.0.6/SHA256SUMS.txt)比較 SHA-256。

```powershell
Get-FileHash .\tt-tool-1.0.6-windows-x64-setup.exe -Algorithm SHA256
```

## 建置與驗證安裝程式

使用 Windows x64、Python 3.12 和 [Inno Setup 7 x64](https://jrsoftware.org/inno-setup/downloads)。先依[繁體中文 README](../README.zh-TW.md)準備 Python 環境，再從儲存庫根目錄執行。

```powershell
.\.venv\Scripts\python.exe selfcheck.py
.\.venv\Scripts\python.exe build_tt_tool.py --iscc "C:\Program Files\Inno Setup 7\ISCC.exe"
```

建置會以鎖定清單檢查依賴、準備獨立執行環境並檢查 Qt 啟動。安裝檔輸出至 `dist\`。執行 `.\.venv\Scripts\python.exe build_tt_tool.py --check-payload` 可單獨驗證執行環境。

從預定發布的提交建置。使用 [Windows 安裝工作流程](https://github.com/Estrella-071/tt-tool/actions/workflows/tt-tool-installer.yml)驗證安裝、捷徑啟動、更新及解除安裝。使用該次執行的 EXE 和校驗檔，發布標籤應指向已驗證的提交。

[第三方元件與原始碼](THIRD-PARTY.zh-TW.md)
