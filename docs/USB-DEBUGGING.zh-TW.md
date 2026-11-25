# 開啟 Android USB 偵錯

[English](USB-DEBUGGING.md) · [繁體中文](USB-DEBUGGING.zh-TW.md) · [日本語](USB-DEBUGGING.ja.md) · [한국어](USB-DEBUGGING.ko.md)

1. 依照下表找到手機的版本或組建欄位，連點七次，必要時輸入螢幕鎖定 PIN，開啟「開發人員選項」。若已開啟，直接進行下一步。
2. 在「開發人員選項」啟用「USB 偵錯」，並確認手機提示。
3. 保持手機解鎖，以 USB 資料線連接電腦。手機詢問是否允許 USB 偵錯時，確認信任這台電腦並允許 RSA 金鑰。
4. 在 tt tool 裝置選單選「重新偵測」。有多台裝置時選擇手機。[Android ADB 指南](https://developer.android.com/tools/adb#Enabling)

## 各品牌路徑

選單名稱會因型號、地區和系統版本而異。啟用後若找不到位置，可在手機設定搜尋「開發人員選項」。

| 手機 | 開啟開發人員選項 | USB 偵錯開關位置 |
| --- | --- | --- |
| Google Pixel | 「關於手機」中點按「版本號碼」。 | 「系統 › 開發人員選項」，舊版可能在「系統 › 進階」。 [Android Developers](https://developer.android.com/codelabs/basic-android-kotlin-compose-connect-device#2) |
| Samsung Galaxy | 「關於手機 › 軟體資訊」中點按「版本號碼」。 | 設定主畫面底部附近。 [Samsung Support](https://www.samsung.com/us/support/answer/ANS10003430/) |
| Xiaomi、Redmi、POCO | 在「關於手機」點按 HyperOS 的「作業系統版本」或 MIUI 的「MIUI 版本」。有些型號位於「詳細資訊與規格」或「所有規格」。 | 「其他設定 › 開發人員選項」，舊 MIUI 可能稱為「更多設定」。 [Xiaomi developer options](https://www.mi.com/global/support/faq/details/KA-168765/) · [Xiaomi MIUI USB debugging](https://www.mi.com/global/support/article/KA-06515/) |
| OPPO | 在「關於本機」或「關於手機」開啟「版本」。ColorOS 14–16 點按「版本號」，6–13 點按「版本號碼」。 | 14.1–16 在「系統與更新」，13–14 及 6–11 在「其他設定」，12 在「系統設定」。 [OPPO ColorOS 11 to 16](https://support.oppo.com/au/answer/?aid=neu9332) · [OPPO ColorOS 6 to 11](https://support.oppo.com/id/answer/?aid=2030190) · [OPPO older build number path](https://support.oppo.com/uk/answer/?a_id=10309) |
| vivo、iQOO | 「關於手機 › 軟體資訊」中點按「版本」，部分手機稱為「軟體版本」或「版本號碼」。 | 依機型位於「系統管理」或「系統」。 [vivo manual](https://de-gdpr-exstatic-vivofs.vivo.com/sFhAQhTYYDsNOJz1/1752720786878/81eed887f307e94a0d05b2f9d2e5a86c.pdf) · [iQOO manual](https://eu-exstatic-vivofs.vivo.com/8Xa6evfY85lu15Pb/1665478526153/dae33c484c3491379d87884ece23a815.pdf) |
| OnePlus | 在「關於手機」或「關於裝置」尋找「版本號碼」，必要時先開啟「版本」。 | 在設定搜尋「開發人員選項」。 [OnePlus Support](https://service.oneplus.com/in/search/search-detail?id=op5091) · [Android Developers](https://developer.android.com/studio/debug/dev-options.html) |
| Motorola | 在「關於手機」點按「版本號碼」，部分型號的「關於手機」位於「系統」。 | 「系統 › 開發人員選項」，部分版本位於「系統 › 進階」。 [Motorola Developer options](https://en-us.support.motorola.com/app/answers/detail/a_id/159678/~/developer-options) · [Motorola older menu path](https://en-us.support.motorola.com/app/answers/detail/a_id/158583) |
| realme | 在「關於裝置 › 版本」點按「版本號碼」。 | realme UI 6–7 在「系統與更新」，3–5 在「系統設定」或「其他設定」，1–2 在「其他設定」。 [realme USB debugging](https://www.realme.com/in/support/kw/doc/2105688) · [realme menu locations](https://www.realme.com/ph/support/kw/doc/2062261) |
| 其他 Android | 在「關於手機」尋找「版本號碼」，部分機型需先開啟「軟體資訊」。 | 搜尋「開發人員選項」。新版 Android 通常在「系統」或「系統 › 進階」，舊版可能在設定主畫面。 [Android Developers](https://developer.android.com/studio/debug/dev-options.html) |

## 手機仍未出現

- 開啟新的終端機並執行 `adb devices`。`unauthorized` 代表等待授權，請解鎖手機、確認偵錯提示，必要時重新連接。
- 若完全沒有裝置，換一個連接埠和確認可傳輸資料的線材。Windows 可能需要製造商的 [ADB USB 驅動程式](https://developer.android.com/studio/run/oem-usb)。
- 找不到 ADB 或 FFmpeg 時，參考 [Windows 安裝指南](INSTALLER.zh-TW.md)。[Android 裝置連線說明](https://developer.android.com/studio/run/device)
