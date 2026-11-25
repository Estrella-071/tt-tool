# Windows インストーラー再配布のお知らせ

[English](THIRD-PARTY.md) · [繁體中文](THIRD-PARTY.zh-TW.md) · 日本語 · [한국어](THIRD-PARTY.ko.md)

tt toolは GPL-3.0 のみで配布されます。バンドルされている `LICENSE` および `NOTICE.md` を参照してください。対応するアプリケーション、インストーラー、およびアップデーターのソースは、[v1.0.6 ソース ツリー ](https://github.com/Estrella-071/tt-tool/tree/v1.0.6).インストーラーには、電話アプリのソース ファイルも含まれています。

- Qt 6.11.0、PySide6 Essentials 6.11.0、および Shiboken 6.11.0 は、GPLv3 コミュニティ ライセンス オプションに基づいて使用されます。 GNU GPL ライセンス テキストは `LICENSE` として含まれています。 Qt から [Qt 6.11.0 source](https://download.qt.io/archive/qt/6.11/6.11.0/single/) と [PySide6 と Shiboken 6.11.0 source](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.0-src/)] をダウンロードします。バージョン管理されたホイールの URL とダイジェストは `DEPENDENCIES.json` にあります。 Qt ライブラリは別のファイルとしてインストールされます。 [Qt ライセンス情報 ](https://doc.qt.io/qt-6/licensing.html) および [Qt for Python 通知 ](https://doc.qt.io/qtforpython-6/licenses.html) を参照してください。
- CPython および Tcl/Tk ライセンスはランタイムに付属します。 NumPy と OpenCV の通知は、インストールされたパッケージとメタデータ ディレクトリにあります。正確なバージョンとダウンロード URL は `DEPENDENCIES.json` にあります。 OpenCV ビデオ I/O ホイールからのオプションの FFmpeg バイナリは除外されます。
- セットアップ エンジンは、Jordan Russell と Martijn Laan による [Inno Setup 7.1.1](https://github.com/jrsoftware/issrc/tree/is-7_1_1)] です。 [そのライセンス](https://github.com/jrsoftware/issrc/blob/is-7_1_1/license.txt)を参照してください。
- Android プラットフォーム ツールと FFmpeg は、ユーザーが公式ダウンロード ページから個別にインストールします。これらは、バンドルされている Python ランタイムから独立しています。
