# Windows免安裝隨身版

[English](WINDOWS.md) · 繁體中文 · [日本語](WINDOWS.ja.md) · [한국어](WINDOWS.ko.md)

> 此技術文件包含歷史版本與測量紀錄。目前的安裝方式和支援功能請見[主要指南](../README.zh-TW.md)。

## 普通用戶

在專案的GitHub Releases中選擇 `tt-tool-emulator-版本号-Windows-x64.zip`，完整解壓，雙擊 `启动钓鱼助手.bat`。下載頁是否已有對應版本，以項目實際發布為準。不要下載GitHub自動生成的Source code ZIP來代替便攜包。

適用64位Windows 10/11。套件中帶有獨立CPython、Tcl/Tk、NumPy、OpenCV、Pillow和MSS；無需安裝Python、Anaconda、PyCharm或額外運行pip，首次啟動也不下載元件。雷電或MuMu模擬器和游戲仍需自行準備。程式不會修改系統Python、登錄或PATH。

根目錄的 `app/` 儲存完整專案原始碼和資源，`runtime/` 儲存獨立運作環境，`data/` 在運作後儲存本機設定、日誌、截圖和錄影。雙擊入口使用隨包解釋器的隔離模式，不讀取用戶安裝的Python包和PYTHONPATH。

解壓縮到目前帳戶可寫的位置，不要放在壓縮包預覽視窗、唯讀磁碟或需要提權才能寫入的系統目錄。同一個資料目錄重複啟動會提示切換到已開啟的視窗。不同資料夾中的獨立副本仍應避免同時控制相同模擬器。

初次使用仍需要設置空格映射、選擇窗口、框選完整游戲區域，并通過開始按鈕或快捷鍵啟動釣魚。操作步驟請參考 [README](../README.zh-TW.md)。

## 更新與排查

- 更新：先退出舊版，將新包解壓縮到新資料夾。保留舊目錄備份；需要沿用設定時，僅複製舊 `data/` 中的 `config.json`、`speed_profile.json` 到新套件的 `data/`，不存在的檔案無需建立。從原始碼版遷移時，複製專案根目錄中的這兩個檔案。歷史截圖和錄影可繼續保留在舊目錄。
- 無法開啟：雙擊 `检查运行环境.bat`，保留顯示的錯誤；啟動錯誤另寫入 `data/logs/startup.log`。不要公開未經檢查的錯誤日誌。
- 文件被攔截或缺失：核對是否來自專案發佈頁、校驗值是否一致，再按系統提示處理；不要以關閉安全軟體作為常規步驟。
- 權限不一致：僅當模擬器以管理員身分執行時，才考慮以相同權限執行助手。
- 分享：發佈建置得到的原始ZIP，不要重新壓縮自己已經使用過的便攜目錄。

## 維護者重新生成

倉庫根目錄運作：

```bash
python build_windows.py
```

建置入口只需Python 3.10以上的標準庫。首次建置需要連網，從固定清單下載運行環境和Windows依賴，逐一檢查SHA-256。之後可重複使用 `.build-cache/` 中的檔案。建置不會讀取本機 `config.json` 或把日誌、截圖、錄影帶入完成品。

輸出在 `dist/tt-tool-emulator-版本号-Windows-x64.zip`。 Windows主機上構建還會用隨包解釋器檢查Tk、ImageTk、圖像模板、錄像編解碼和顯示器接口；該檢查不截圖、不發送按鍵。在其他作業系統上可組裝相同便攜包，但二進位結構和檔案完整性檢查不等於Windows運行驗證。發布前仍需在Windows上檢查介面、框選、暫停與真實模擬器操作。

在GitHub上傳原始碼後，也可進入 **Actions → Windows portable → Run workflow**。工作流程在Windows機器上建置、檢查，成功後提供可下載的建置產物。下載後將便攜ZIP手動新增至GitHub Release；工作流程不會自動發布版本。倉庫須包含 `.github/workflows/windows-portable.yml`，不要漏傳以點開頭的目錄。

`packaging/windows-runtime.lock.json` 固定依賴版本、來源和雜湊。更新依賴時要同時核對Windows x64/Python 3.12相容性及許可，驗證實際下載後再更新清單；不要只改版本字串。目前鎖定包沒有wheel的額外`.data`安裝目錄；新增此類相依性須先擴充並測試建置規則。

本專案使用獨立運行環境目錄實現免安裝，不需要在用戶電腦臨時解包單檔EXE。請務必一起分送入口、app和runtime。原始碼由明確文件清單產生；第三方二進位保留其上游許可，版本與下載來源記錄在套件內 `DEPENDENCIES.json`。
