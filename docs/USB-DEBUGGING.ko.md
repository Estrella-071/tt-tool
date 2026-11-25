# Android에서 USB 디버깅 켜기

[English](USB-DEBUGGING.md) · [繁體中文](USB-DEBUGGING.zh-TW.md) · [日本語](USB-DEBUGGING.ja.md) · [한국어](USB-DEBUGGING.ko.md)

1. 아래 표에서 휴대전화의 버전 또는 빌드 번호 항목을 찾아 일곱 번 누르고, 요청되면 화면 잠금 PIN을 입력해 개발자 옵션을 표시합니다. 이미 표시되어 있다면 다음 단계로 이동합니다.
2. **개발자 옵션**에서 **USB 디버깅**을 켜고 휴대전화의 확인 창에서 허용합니다.
3. 잠금을 해제한 상태로 데이터 전송이 가능한 USB 케이블을 사용해 PC에 연결합니다. USB 디버깅 허용 여부를 묻는 창에서 신뢰하는 PC의 RSA 키를 승인합니다.
4. tt tool의 기기 메뉴에서 **다시 검색**을 선택합니다. 여러 기기가 있으면 휴대전화를 선택합니다. [Android ADB 가이드](https://developer.android.com/tools/adb#Enabling)

## 제조사별 경로

메뉴 이름은 모델, 지역, 운영체제 버전에 따라 달라질 수 있습니다. 메뉴를 표시한 뒤 위치를 찾지 못하면 설정에서 **개발자 옵션**을 검색하세요.

| 휴대전화 | 개발자 옵션 표시 | USB 디버깅 위치 |
| --- | --- | --- |
| Google Pixel | **휴대전화 정보**에서 **빌드 번호**를 누릅니다. | **시스템 › 개발자 옵션**, 이전 버전은 **시스템 › 고급**에서 찾습니다. [Android Developers](https://developer.android.com/codelabs/basic-android-kotlin-compose-connect-device#2) |
| Samsung Galaxy | **휴대전화 정보 › 소프트웨어 정보**에서 **빌드 번호**를 누릅니다. | 설정 기본 화면 하단 부근에서 찾습니다. [Samsung Support](https://www.samsung.com/us/support/answer/ANS10003430/) |
| Xiaomi, Redmi, POCO | **휴대전화 정보**에서 HyperOS의 **OS 버전** 또는 MIUI의 **MIUI 버전**을 누릅니다. 일부 기기는 **상세 정보 및 사양** 또는 **전체 사양**에 있습니다. | **추가 설정 › 개발자 옵션**. 구형 MIUI에서는 **기타 설정**일 수 있습니다. [Xiaomi developer options](https://www.mi.com/global/support/faq/details/KA-168765/) · [Xiaomi MIUI USB debugging](https://www.mi.com/global/support/article/KA-06515/) |
| OPPO | **기기 정보** 또는 **휴대전화 정보**에서 **버전**을 엽니다. ColorOS 14–16에서는 **버전 번호**, 6–13에서는 **빌드 번호**를 누릅니다. | 14.1–16은 **시스템 및 업데이트**, 13–14와 6–11은 **추가 설정**, 12는 **시스템 설정**에서 찾습니다. [OPPO ColorOS 11 to 16](https://support.oppo.com/au/answer/?aid=neu9332) · [OPPO ColorOS 6 to 11](https://support.oppo.com/id/answer/?aid=2030190) · [OPPO older build number path](https://support.oppo.com/uk/answer/?a_id=10309) |
| vivo, iQOO | **휴대전화 정보 › 소프트웨어 정보**의 **버전**을 누릅니다. **소프트웨어 버전** 또는 **빌드 번호**일 수도 있습니다. | 기기에 따라 **시스템 관리** 또는 **시스템**에서 찾습니다. [vivo manual](https://de-gdpr-exstatic-vivofs.vivo.com/sFhAQhTYYDsNOJz1/1752720786878/81eed887f307e94a0d05b2f9d2e5a86c.pdf) · [iQOO manual](https://eu-exstatic-vivofs.vivo.com/8Xa6evfY85lu15Pb/1665478526153/dae33c484c3491379d87884ece23a815.pdf) |
| OnePlus | **휴대전화 정보** 또는 **기기 정보**에서 **빌드 번호**를 찾습니다. **버전**이 있으면 먼저 엽니다. | 설정에서 **개발자 옵션**을 검색합니다. [OnePlus Support](https://service.oneplus.com/in/search/search-detail?id=op5091) · [Android Developers](https://developer.android.com/studio/debug/dev-options.html) |
| Motorola | **휴대전화 정보**에서 **빌드 번호**를 누릅니다. 일부 모델은 **시스템** 안에 **휴대전화 정보**가 있습니다. | **시스템 › 개발자 옵션**, 일부 버전은 **시스템 › 고급**에 있습니다. [Motorola Developer options](https://en-us.support.motorola.com/app/answers/detail/a_id/159678/~/developer-options) · [Motorola older menu path](https://en-us.support.motorola.com/app/answers/detail/a_id/158583) |
| realme | **기기 정보 › 버전**에서 **빌드 번호**를 누릅니다. | realme UI 6–7은 **시스템 및 업데이트**, 3–5는 **시스템 설정** 또는 **추가 설정**, 1–2는 **추가 설정**에 있습니다. [realme USB debugging](https://www.realme.com/in/support/kw/doc/2105688) · [realme menu locations](https://www.realme.com/ph/support/kw/doc/2062261) |
| 기타 Android | **휴대전화 정보**에서 **빌드 번호**를 찾습니다. 일부 기기는 **소프트웨어 정보**를 먼저 열어야 합니다. | 설정에서 **개발자 옵션**을 검색합니다. 최신 Android는 대개 **시스템** 또는 **시스템 › 고급**, 이전 버전은 설정 기본 화면에 표시될 수 있습니다. [Android Developers](https://developer.android.com/studio/debug/dev-options.html) |

## 휴대전화가 표시되지 않을 때

- 새 터미널에서 `adb devices`를 실행합니다. `unauthorized`는 승인을 기다리는 상태입니다. 휴대전화 잠금을 해제하고 디버깅 확인 창을 살핀 후 필요하면 다시 연결합니다.
- 기기가 전혀 표시되지 않으면 다른 포트와 데이터 전송이 확인된 케이블을 사용합니다. Windows에는 제조사의 [ADB USB 드라이버](https://developer.android.com/studio/run/oem-usb)가 필요할 수 있습니다.
- ADB 또는 FFmpeg를 찾을 수 없으면 [Windows 설치 안내](INSTALLER.ko.md)를 참조하세요. [Android 기기 연결 도움말](https://developer.android.com/studio/run/device)
