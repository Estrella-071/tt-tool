# Windows x64 インストールガイド

[English](INSTALLER.md) · [繁體中文](INSTALLER.zh-TW.md) · [日本語](INSTALLER.ja.md) · [한국어](INSTALLER.ko.md)

[tt-tool-1.0.6-windows-x64-setup.exe をダウンロード](https://github.com/Estrella-071/tt-tool/releases/download/v1.0.6/tt-tool-1.0.6-windows-x64-setup.exe)します。対応環境は Windows 10 22H2 または Windows 11 の x64 です。インストーラーには Python、Qt、ローカル画像認識の依存パッケージが含まれます。スマートフォン接続には [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) と [FFmpeg](https://ffmpeg.org/download.html#build-windows) も必要です。

## インストールと起動

1. セットアップを起動し、English、繁體中文、日本語、한국어から選びます。初回起動時は選択した言語を使用します。
2. 初回インストール時はフォルダーを変更できます。既定では現在のユーザーの `%LOCALAPPDATA%\Programs\tt tool` にインストールされます。
3. ショートカットを選びます。スタートメニューは既定でオン、デスクトップはオフです。
4. 最終画面で完了後の起動を選べます。ショートカットは後からも使えます。外部ショートカットを両方オフにしても、インストールフォルダー内に **tt tool** のショートカットがあります。

完全な GPL ライセンスはインストールフォルダーにあり、**メンテナンス → ライセンスを表示** からも読めます。

tt tool はユーザーの `Path` から `adb.exe` と `ffmpeg.exe` を探します。端末メニューの **接続ツール** で実行ファイルを指定し、**確認して再試行** を選べます。アプリの **USB 接続ガイド** または[メーカー別ガイド](USB-DEBUGGING.ja.md)に従って端末を準備します。Android は `screenrecord --time-limit 0` に対応する必要があります。

## 更新

旧番号 v1.1.0、v1.2.0、v1.3.0 が表示される場合は、tt tool を閉じ、既存のインストール先で v1.0.6 インストーラーを一度実行してください。設定は保持され、それ以降は新しいバージョン系列のアプリ内更新を利用できます。過去の v1.0.2～v1.0.4 には元のインストーラーとチェックサムが残ります。

インストール済みの v1.0.5 以降は **メンテナンス → 更新を確認** を選びます。操作時に GitHub の最新安定版を確認します。検証可能なインストーラーがあれば **ダウンロードしてインストール** で開始でき、途中でキャンセルできます。SHA-256 を比較した後、現在の操作を終了して閉じ、元の場所にインストールするか確認します。進行状況を表示し、完了後に tt tool を再起動します。

更新完了、失敗またはキャンセル時には一時インストーラーを削除します。アプリ内更新を利用できない場合やソースから実行している場合は **リリースページを開く** から手動でダウンロードできます。設定、表示言語、調整値、ローカルログは更新後も保持されます。

## ファイルとアンインストール

**メンテナンス** の **ファイルの場所を開く** または **設定フォルダーを開く** を使います。ソース版から `phone_settings.json` と `tt_tool_ui.json` を `%LOCALAPPDATA%\tt-tool\data` に移す場合は、両方のアプリを先に終了してください。

インストール版では tt tool の **アンインストール…** または Windows 設定の **インストールされているアプリ** から削除できます。確認画面にインストール先が表示されます。tt tool から開始するときは操作の終了とアプリの終了を確認します。アンインストーラーは進行状況と結果を表示し、最新安定版のリリースノートを開くボタンを提供します。

設定、調整値、診断ログは既定で `%LOCALAPPDATA%\tt-tool\data` に保持されます。このフォルダーも削除する場合はローカルデータの削除を選択します。

## ダウンロードの検証

インストール情報の発行元は **71** です。インストーラーには Authenticode 署名がないため、Windows では **不明な発行元** と表示される場合があります。手動ダウンロード時は SHA-256 を[同じ GitHub リリースのチェックサム](https://github.com/Estrella-071/tt-tool/releases/download/v1.0.6/SHA256SUMS.txt)と比較できます。

```powershell
Get-FileHash .\tt-tool-1.0.6-windows-x64-setup.exe -Algorithm SHA256
```

## インストーラーのビルドと検証

Windows x64、Python 3.12、[Inno Setup 7 x64](https://jrsoftware.org/inno-setup/downloads) を使用します。[日本語 README](../README.ja.md) で Python 環境を準備し、リポジトリのルートから実行します。

```powershell
.\.venv\Scripts\python.exe selfcheck.py
.\.venv\Scripts\python.exe build_tt_tool.py --iscc "C:\Program Files\Inno Setup 7\ISCC.exe"
```

ビルドは固定されたマニフェストと依存パッケージを照合し、独立した実行環境を準備して Qt の起動を確認します。インストーラーは `dist\` に出力されます。`.\.venv\Scripts\python.exe build_tt_tool.py --check-payload` で実行環境だけを確認できます。

公開予定のコミットからビルドし、[Windows インストーラーワークフロー](https://github.com/Estrella-071/tt-tool/actions/workflows/tt-tool-installer.yml)でインストール、ショートカット起動、更新、削除を検証します。その実行で得た EXE とチェックサムを使用し、リリースタグを検証済みコミットに設定します。

[サードパーティーのコンポーネントとソースコード](THIRD-PARTY.ja.md)
