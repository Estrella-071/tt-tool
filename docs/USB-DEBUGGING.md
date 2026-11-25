# Enable USB debugging on Android

[English](USB-DEBUGGING.md) · [繁體中文](USB-DEBUGGING.zh-TW.md) · [日本語](USB-DEBUGGING.ja.md) · [한국어](USB-DEBUGGING.ko.md)

1. Use the menu path below for your phone to reveal **Developer options**. Tap the indicated version or build field seven times and enter your phone's lock-screen PIN if requested. If Developer options is already available, proceed to the next step.
2. Open **Developer options**, turn on **USB debugging**, and confirm the prompt on the phone.
3. Keep the phone unlocked and connect it to your computer with a USB data cable. When the phone shows **Allow USB debugging?**, approve the RSA key for a computer you trust.
4. In tt tool, open the device selector and choose **Scan again**. Select your phone if more than one is listed. [Android Developers ADB guide](https://developer.android.com/tools/adb#Enabling)

## Paths by phone brand

Menu names can vary with the model, region and OS version. If the paths differ after you reveal the menu, search the phone's Settings for **Developer options**.

| Phone | Reveal Developer options | Find the USB debugging switch |
| --- | --- | --- |
| Google Pixel | Under **About phone**, tap **Build number**. | Look in **System › Developer options**, or **System › Advanced** on older releases. [Android Developers](https://developer.android.com/codelabs/basic-android-kotlin-compose-connect-device#2) |
| Samsung Galaxy | Under **About phone › Software information**, tap **Build number**. | Look near the bottom of the main Settings screen. [Samsung Support](https://www.samsung.com/us/support/answer/ANS10003430/) |
| Xiaomi, Redmi and POCO | Under **About phone**, tap **OS version** on HyperOS or **MIUI version** on MIUI. Some models place it under **Detailed info and specs** or **All specs**. | Look under **Additional settings › Developer options**. Older MIUI may show **More settings**. [Xiaomi developer options](https://www.mi.com/global/support/faq/details/KA-168765/) · [Xiaomi MIUI USB debugging](https://www.mi.com/global/support/article/KA-06515/) |
| OPPO | Under **About device** or **About phone**, open **Version**. Tap **Version No.** on ColorOS 14 to 16 or **Build number** on 6 to 13. | Look in **System & update** on 14.1 to 16, **Additional settings** on 13 to 14 and 6 to 11, or **System settings** on 12. [OPPO ColorOS 11 to 16](https://support.oppo.com/au/answer/?aid=neu9332) · [OPPO ColorOS 6 to 11](https://support.oppo.com/id/answer/?aid=2030190) · [OPPO older build number path](https://support.oppo.com/uk/answer/?a_id=10309) |
| vivo and iQOO | Under **About phone › Software information**, tap **Version**. Some phones call it **Software version** or **Build number**. | Look under **System management** or **System**, depending on the phone. [vivo manual](https://de-gdpr-exstatic-vivofs.vivo.com/sFhAQhTYYDsNOJz1/1752720786878/81eed887f307e94a0d05b2f9d2e5a86c.pdf) · [iQOO manual](https://eu-exstatic-vivofs.vivo.com/8Xa6evfY85lu15Pb/1665478526153/dae33c484c3491379d87884ece23a815.pdf) |
| OnePlus | Find **Build number** in **About phone** or **About device**. Open **Version** first if it is present. | Search Settings for **Developer options**. [OnePlus Support](https://service.oneplus.com/in/search/search-detail?id=op5091) · [Android Developers](https://developer.android.com/studio/debug/dev-options.html) |
| Motorola | Under **About phone**, tap **Build number**. Some models place **About phone** under **System**. | Look under **System › Developer options**. Some versions put it under **System › Advanced**. [Motorola Developer options](https://en-us.support.motorola.com/app/answers/detail/a_id/159678/~/developer-options) · [Motorola older menu path](https://en-us.support.motorola.com/app/answers/detail/a_id/158583) |
| realme | Under **About device › Version**, tap **Build number**. | Look in **System & Updates** on realme UI 6 and 7, **System settings** or **Additional settings** on 3 to 5, or **Additional settings** on 1 and 2. [realme USB debugging](https://www.realme.com/in/support/kw/doc/2105688) · [realme menu locations](https://www.realme.com/ph/support/kw/doc/2062261) |
| Other Android | Look for **Build number** under **About phone**. Some phones require opening **Software information** first. | Search Settings for **Developer options**. Newer Android versions usually place it under **System** or **System › Advanced**. Older versions can show it directly on the main Settings page. [Android Developers](https://developer.android.com/studio/debug/dev-options.html) |

## If the phone still does not appear

- Open a new terminal and run `adb devices`. A phone marked `unauthorized` is waiting for permission. Unlock it, check for the debugging prompt, and reconnect if the prompt has not appeared.
- If the phone does not appear at all, try another port and a cable you know transfers data. Windows may require the manufacturer's [ADB USB driver](https://developer.android.com/studio/run/oem-usb).
- If tt tool cannot find ADB or FFmpeg, follow the [Windows installer guide](INSTALLER.md). [Android Developers device connection help](https://developer.android.com/studio/run/device)
