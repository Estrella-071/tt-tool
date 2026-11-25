# 著作権とライセンス

[English](NOTICE.md) · [繁體中文](NOTICE.zh-TW.md) · 日本語 · [한국어](NOTICE.ko.md)

Copyright (C) 2026 zz11-m および寄稿者。
Copyright (C) 2026 モバイル アプリケーションおよびリリース ツールの tt ツール コントリビューター。

tt ツールの Windows モバイル バージョンには、ADB 携帯電話キャプチャ、釣り識別、遺跡探索、Qt インターフェイスが含まれています。使用されているフィッシング コントロール、タイミング プログラム、およびシミュレーター ツールには、オリジナルの作成者の著作権表示が保持されています。

ソースコードとプロジェクト文書には [GPL-3.0-only](LICENSE) が適用されます。変更版を配布する場合は、著作権とライセンスの表示を保持し、変更箇所を明示し、ライセンスに従って対応するソースコードを提供してください。Windows 携帯版のサードパーティライセンスと対応するソースコードは [サードパーティコンポーネント](docs/THIRD-PARTY.ja.md) を参照してください。

`assets/templates/`、`tests/assets/`、`docs/images/crop-example.png`のゲーム画面およびシミュレーター画面は機能確認、回帰検証、動作例のみに使用されており、その権利はそれぞれの権利者に帰属します。

## エミュレータのポータブル版

シミュレーターのポータブル バージョンには CPython、Tcl/Tk、NumPy、OpenCV ヘッドレス、Pillow、MSS が付属しており、各コンポーネントには独自のライセンスが適用されます。各パッケージの Python ライセンスは `runtime/LICENSE.txt` にあり、Tcl/Tk ライセンスは `runtime/tcl` にあり、Python スイート ライセンスは `dist-info` にあります。 OpenCV には `LICENSE-3RD-PARTY.txt` が付属しています。 `DEPENDENCIES.json` はコンポーネントのバージョン、ソース、SHA-256 を記録し、`app` ディレクトリにはプロジェクトのソース コードが含まれます。
