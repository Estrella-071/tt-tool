# Windows 安裝程式重新分發通知

[English](THIRD-PARTY.md) · 繁體中文 · [日本語](THIRD-PARTY.ja.md) · [한국어](THIRD-PARTY.ko.md)

tt tool僅在 GPL-3.0 下分發。請參閱捆綁的 `LICENSE` 和 `NOTICE.md`。相應的應用程式、安裝程式和更新程式來源可從 [v1.0.6 原始碼樹](https://github.com/Estrella-071/tt-tool/tree/v1.0.6) 取得。安裝程式還包含手機應用程式的來源檔案。

- Qt 6.11.0、PySide6 Essentials 6.11.0 和 Shiboken 6.11.0 在其 GPLv3 社區許可選項下使用。 GNU GPL 授權文字包含為 `LICENSE`。從Qt下載[Qt 6.11.0 source](https://download.qt.io/archive/qt/6.11/6.11.0/single/)和[PySide6和Shiboken 6.11.0 source](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.0-src/)。版本控制的輪子 URL 和摘要位於 `DEPENDENCIES.json` 中。 Qt 函式庫作為單獨的檔案安裝。請參閱[Qt 許可資訊](https://doc.qt.io/qt-6/licensing.html) 和[Qt for Python 通知](https://doc.qt.io/qtforpython-6/licenses.html)。
- 運行時附帶 CPython 和 Tcl/Tk 許可證。 NumPy 和 OpenCV 通知位於其安裝的套件和元資料目錄中。它們的確切版本和下載網址位於`DEPENDENCIES.json`。 OpenCV 視訊 I/O 輪中的可選 FFmpeg 二進位檔案被排除在外。
- 設定引擎是 [Inno Setup 7.1.1](https://github.com/jrsoftware/issrc/tree/is-7_1_1)，作者：Jordan Russell 和 Martijn Laan。請參閱[其許可證](https://github.com/jrsoftware/issrc/blob/is-7_1_1/license.txt)。
- Android Platform-Tools 和 FFmpeg 由用戶從其官方下載頁面單獨安裝。它們獨立於捆綁的 Python 運行時。
