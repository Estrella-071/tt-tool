# Android で USB デバッグを有効にする

[English](USB-DEBUGGING.md) · [繁體中文](USB-DEBUGGING.zh-TW.md) · [日本語](USB-DEBUGGING.ja.md) · [한국어](USB-DEBUGGING.ko.md)

1. 下表を参考に端末のバージョンまたはビルド番号を 7 回タップし、求められたら画面ロックの PIN を入力して「開発者向けオプション」を表示します。すでに表示されている場合は次に進みます。
2. 「開発者向けオプション」で「USB デバッグ」を有効にし、端末の確認画面で許可します。
3. 端末のロックを解除したままデータ転送対応の USB ケーブルで PC に接続します。USB デバッグの許可を求められたら、信頼できる PC の RSA キーを承認します。
4. tt tool の端末メニューで「再検出」を選択します。複数台ある場合は対象端末を選びます。[Android ADB ガイド](https://developer.android.com/tools/adb#Enabling)

## メーカー別の設定場所

機種、地域、OS バージョンにより名称は異なります。表示後に場所が見つからない場合は設定で「開発者向けオプション」を検索してください。

| メーカー | 開発者向けオプションの表示 | USB デバッグの場所 |
| --- | --- | --- |
| Google Pixel | 「デバイス情報」で「ビルド番号」をタップ。 | 「システム › 開発者向けオプション」。旧版では「システム › 詳細設定」。 [Android Developers](https://developer.android.com/codelabs/basic-android-kotlin-compose-connect-device#2) |
| Samsung Galaxy | 「端末情報 › ソフトウェア情報」で「ビルド番号」をタップ。 | 設定画面の下部付近。 [Samsung Support](https://www.samsung.com/us/support/answer/ANS10003430/) |
| Xiaomi、Redmi、POCO | 「端末情報」で HyperOS の「OS バージョン」または MIUI の「MIUI バージョン」をタップ。機種によっては「詳細情報と仕様」または「すべての仕様」にあります。 | 「追加設定 › 開発者向けオプション」。旧 MIUI では「その他の設定」の場合があります。 [Xiaomi developer options](https://www.mi.com/global/support/faq/details/KA-168765/) · [Xiaomi MIUI USB debugging](https://www.mi.com/global/support/article/KA-06515/) |
| OPPO | 「デバイス情報」または「端末情報」から「バージョン」を開き、ColorOS 14–16 は「バージョン番号」、6–13 は「ビルド番号」をタップ。 | 14.1–16 は「システムとアップデート」、13–14 と 6–11 は「追加設定」、12 は「システム設定」。 [OPPO ColorOS 11 to 16](https://support.oppo.com/au/answer/?aid=neu9332) · [OPPO ColorOS 6 to 11](https://support.oppo.com/id/answer/?aid=2030190) · [OPPO older build number path](https://support.oppo.com/uk/answer/?a_id=10309) |
| vivo、iQOO | 「端末情報 › ソフトウェア情報」の「バージョン」をタップ。「ソフトウェアバージョン」や「ビルド番号」の場合もあります。 | 機種により「システム管理」または「システム」。 [vivo manual](https://de-gdpr-exstatic-vivofs.vivo.com/sFhAQhTYYDsNOJz1/1752720786878/81eed887f307e94a0d05b2f9d2e5a86c.pdf) · [iQOO manual](https://eu-exstatic-vivofs.vivo.com/8Xa6evfY85lu15Pb/1665478526153/dae33c484c3491379d87884ece23a815.pdf) |
| OnePlus | 「端末情報」または「デバイス情報」で「ビルド番号」を探します。「バージョン」があれば先に開きます。 | 設定で「開発者向けオプション」を検索。 [OnePlus Support](https://service.oneplus.com/in/search/search-detail?id=op5091) · [Android Developers](https://developer.android.com/studio/debug/dev-options.html) |
| Motorola | 「端末情報」で「ビルド番号」をタップ。「端末情報」が「システム」内の機種もあります。 | 「システム › 開発者向けオプション」。一部は「システム › 詳細設定」。 [Motorola Developer options](https://en-us.support.motorola.com/app/answers/detail/a_id/159678/~/developer-options) · [Motorola older menu path](https://en-us.support.motorola.com/app/answers/detail/a_id/158583) |
| realme | 「デバイス情報 › バージョン」で「ビルド番号」をタップ。 | realme UI 6–7 は「システムとアップデート」、3–5 は「システム設定」または「追加設定」、1–2 は「追加設定」。 [realme USB debugging](https://www.realme.com/in/support/kw/doc/2105688) · [realme menu locations](https://www.realme.com/ph/support/kw/doc/2062261) |
| その他の Android | 「端末情報」の「ビルド番号」を探します。先に「ソフトウェア情報」を開く機種もあります。 | 設定で「開発者向けオプション」を検索。新しい Android では通常「システム」または「システム › 詳細設定」、旧版では設定画面に直接表示される場合があります。 [Android Developers](https://developer.android.com/studio/debug/dev-options.html) |

## 端末が表示されない場合

- 新しいターミナルで `adb devices` を実行します。`unauthorized` は許可待ちです。端末のロックを解除して確認画面を探し、必要に応じて再接続します。
- 一覧に全く表示されない場合は別のポートと、データ転送できることが確認済みのケーブルを試します。Windows ではメーカーの [ADB USB ドライバー](https://developer.android.com/studio/run/oem-usb) が必要な場合があります。
- ADB または FFmpeg が見つからない場合は [Windows インストールガイド](INSTALLER.ja.md) を参照してください。[Android 接続ヘルプ](https://developer.android.com/studio/run/device)
