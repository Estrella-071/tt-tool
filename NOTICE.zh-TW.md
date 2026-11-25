# 版權與授權

[English](NOTICE.md) · 繁體中文 · [日本語](NOTICE.ja.md) · [한국어](NOTICE.ko.md)

Copyright (C) 2026 zz11-m and contributors.
Copyright (C) 2026 tt tool contributors for the mobile application and release tooling.

tt tool 的 Windows 手機版包含 ADB 手機擷取、釣魚辨識、遺跡探險與 Qt 介面。沿用的釣魚控制、時序程式及模擬器工具保留原作者版權聲明。

原始碼及專案文件採 [GPL-3.0-only](LICENSE)。散布修改版時，請保留版權與授權聲明、標示修改，並依授權提供相應的原始碼。手機安裝包的第三方授權及對應原始碼見 [第三方元件](docs/THIRD-PARTY.zh-TW.md)。

`assets/templates/`、`tests/assets/` 及 `docs/images/crop-example.png` 中的遊戲與模擬器畫面僅用於功能辨識、回歸驗證及操作示例，權利歸各自的權利人。

## 模擬器可攜版

模擬器可攜版隨附 CPython、Tcl/Tk、NumPy、OpenCV headless、Pillow 及 MSS，各元件適用各自的授權。Python 授權位於 `runtime/LICENSE.txt`，Tcl/Tk 授權位於 `runtime/tcl`，Python 套件授權位於各套件的 `dist-info`。OpenCV 另附 `LICENSE-3RD-PARTY.txt`。`DEPENDENCIES.json` 記錄元件版本、來源與 SHA-256，`app` 目錄包含專案原始碼。
