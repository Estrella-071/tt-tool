# SPDX-License-Identifier: GPL-3.0-only
"""Offline Android USB debugging instructions. Sources: docs/USB-DEBUGGING.md."""

BRANDS = (
    ("pixel", "Google Pixel"),
    ("samsung", "Samsung Galaxy"),
    ("xiaomi", "Xiaomi / Redmi / POCO"),
    ("oppo", "OPPO"),
    ("vivo", "vivo / iQOO"),
    ("oneplus", "OnePlus"),
    ("motorola", "Motorola"),
    ("realme", "realme"),
    ("other", "Other Android"),
)

_SOURCES = {
    "pixel": "https://developer.android.com/codelabs/basic-android-kotlin-compose-connect-device#2",
    "samsung": "https://www.samsung.com/us/support/answer/ANS10003430/",
    "xiaomi": "https://www.mi.com/global/support/faq/details/KA-168765/",
    "oppo": "https://support.oppo.com/au/answer/?aid=neu9332",
    "vivo": "https://de-gdpr-exstatic-vivofs.vivo.com/sFhAQhTYYDsNOJz1/1752720786878/81eed887f307e94a0d05b2f9d2e5a86c.pdf",
    "oneplus": "https://service.oneplus.com/in/search/search-detail?id=op5091",
    "motorola": "https://en-us.support.motorola.com/app/answers/detail/a_id/159678/~/developer-options",
    "realme": "https://www.realme.com/in/support/kw/doc/2105688",
    "other": "https://developer.android.com/studio/debug/dev-options.html",
}

# Each locale contains the path to reveal Developer options and the path to USB debugging.
_PATHS = {
    "pixel": {
        "en": (
            "Open Settings › About phone. Tap Build number seven times.",
            "Go to Settings › System › Developer options. On older Android versions, "
            "look under System › Advanced. Turn on USB debugging.",
        ),
        "zh_TW": (
            "開啟「設定 › 關於手機」，連點「版本號碼」七次。",
            "前往「設定 › 系統 › 開發人員選項」。較舊的 Android 版本請在「系統 › 進階」下尋找。開啟「USB 偵錯」。",
        ),
        "ja": (
            "「設定 › デバイス情報」を開き、「ビルド番号」を 7 回タップします。",
            "「設定 › システム › 開発者向けオプション」を開き、「USB デバッグ」をオンにします。"
            "旧バージョンでは「システム › 詳細設定」の中にある場合があります。",
        ),
        "ko": (
            "설정 › 휴대전화 정보에서 빌드 번호를 7번 누릅니다.",
            "설정 › 시스템 › 개발자 옵션에서 USB 디버깅을 켭니다. 이전 Android에서는 시스템 › 고급을 확인합니다.",
        ),
    },
    "samsung": {
        "en": (
            "Open Settings › About phone › Software information. Tap Build number seven times.",
            "Go back to the main Settings menu and open Developer options near the bottom. Turn on USB debugging.",
        ),
        "zh_TW": (
            "開啟「設定 › 關於手機 › 軟體資訊」，連點「版本號碼」七次。",
            "回到「設定」主畫面，在接近底部的位置開啟「開發人員選項」，再開啟「USB 偵錯」。",
        ),
        "ja": (
            "「設定 › 端末情報 › ソフトウェア情報」を開き、「ビルド番号」を 7 回タップします。",
            "設定のメイン画面に戻り、下部の「開発者向けオプション」で「USB デバッグ」をオンにします。",
        ),
        "ko": (
            "설정 › 휴대전화 정보 › 소프트웨어 정보에서 빌드번호를 7번 누릅니다.",
            "설정 첫 화면 하단의 개발자 옵션을 열고 USB 디버깅을 켭니다.",
        ),
    },
    "xiaomi": {
        "en": (
            "In Settings › About phone, tap OS version (HyperOS) or MIUI version seven times. "
            "On some models the entry is under Detailed info and specs or All specs.",
            "Go to Settings › Additional settings › Developer options and turn on USB debugging. "
            "Some older MIUI versions call Additional settings More settings.",
        ),
        "zh_TW": (
            "在「設定 › 關於手機」連點「OS 版本」（HyperOS）或「MIUI 版本」七次。部分型號要先進入「詳細資訊與規格」或「所有規格」。",
            "前往「設定 › 其他設定 › 開發人員選項」，開啟「USB 偵錯」。舊版 MIUI 可能將「其他設定」稱為「更多設定」。",
        ),
        "ja": (
            "「設定 › デバイス情報」で「OS バージョン」（HyperOS）または「MIUI バージョン」を 7 回タップします。"
            "機種によっては「詳細情報と仕様」または「すべての仕様」の中にあります。",
            "「設定 › 追加設定 › 開発者向けオプション」で「USB デバッグ」をオンにします。"
            "旧バージョンの MIUI では「追加設定」が「その他の設定」と表示されることがあります。",
        ),
        "ko": (
            "설정 › 휴대전화 정보에서 OS 버전(HyperOS) 또는 MIUI 버전을 7번 누릅니다. "
            "일부 모델에서는 상세 정보 및 사양 또는 모든 사양을 먼저 엽니다.",
            "설정 › 추가 설정 › 개발자 옵션에서 USB 디버깅을 켭니다. 이전 MIUI에서는 추가 설정이 기타 설정으로 표시될 수 있습니다.",
        ),
    },
    "oppo": {
        "en": (
            "Open Settings › About device (or About phone) › Version. Tap Version No. seven times "
            "on ColorOS 14–16, or Build number seven times on ColorOS 6–13.",
            "In Settings, open Developer options and enable USB debugging. Look under System & update "
            "(14.1–16), Additional settings (13–14 and 6–11), or System settings (12).",
        ),
        "zh_TW": (
            "前往「設定 › 關於本機（或關於手機）› 版本」。ColorOS 14–16 連點「版本編號」七次，"
            "ColorOS 6–13 連點「版本號碼（Build number）」七次。",
            "從「設定」進入「開發人員選項」並開啟「USB 偵錯」。入口位於「系統與更新」（14.1–16）、"
            "「其他設定」（13–14、6–11），或「系統設定」（12）。",
        ),
        "ja": (
            "「設定 › デバイスについて（または端末情報）› バージョン」を開きます。ColorOS 14～16 では"
            "「バージョン番号」、6～13 では「ビルド番号」を 7 回タップします。",
            "「開発者向けオプション」で「USB デバッグ」をオンにします。設定内の「システムと更新」（14.1～16）、"
            "「その他の設定」（13～14、6～11）、または「システム設定」（12）にあります。",
        ),
        "ko": (
            "설정 › 디바이스 정보(또는 휴대전화 정보) › 버전을 엽니다. ColorOS 14~16에서는 버전 번호를, "
            "6~13에서는 빌드 번호를 7번 누릅니다.",
            "설정에서 개발자 옵션을 열고 USB 디버깅을 켭니다. 시스템 및 업데이트(14.1~16), "
            "추가 설정(13~14 및 6~11) 또는 시스템 설정(12)을 확인합니다.",
        ),
    },
    "vivo": {
        "en": (
            "Open Settings › About phone › Software information. Tap Version seven times. "
            "Some vivo and iQOO models label it Software version or Build number.",
            "Go to Settings › System management › Developer options and turn on USB debugging. "
            "Some models place Developer options under System instead.",
        ),
        "zh_TW": (
            "開啟「設定 › 關於手機 › 軟體資訊」，連點「版本號碼」七次。部分 vivo、iQOO 型號顯示「軟體版本」或「組建編號」。",
            "前往「設定 › 系統管理 › 開發人員選項」，開啟「USB 偵錯」。部分型號的入口位於「系統」下。",
        ),
        "ja": (
            "「設定 › 端末情報 › ソフトウェア情報」で「バージョン」を 7 回タップします。"
            "vivo や iQOO の機種によっては「ソフトウェアバージョン」または「ビルド番号」と表示されます。",
            "「設定 › システム管理 › 開発者向けオプション」で「USB デバッグ」をオンにします。"
            "機種によっては「システム」の中にあります。",
        ),
        "ko": (
            "설정 › 휴대전화 정보 › 소프트웨어 정보에서 버전을 7번 누릅니다. "
            "일부 vivo 및 iQOO 모델에서는 소프트웨어 버전이나 빌드 번호로 표시됩니다.",
            "설정 › 시스템 관리 › 개발자 옵션에서 USB 디버깅을 켭니다. 일부 모델에서는 시스템 아래에 개발자 옵션이 있습니다.",
        ),
    },
    "oneplus": {
        "en": (
            "Open Settings › About phone (or About device). Find Build number, opening Version if present, and tap it seven times.",
            "Return to Settings and search for Developer options. Open the result and turn on USB debugging.",
        ),
        "zh_TW": (
            "開啟「設定 › 關於手機（或關於本機）」，尋找「版本號碼（Build number）」並連點七次。若有「版本」子選單，請先開啟。",
            "回到「設定」搜尋「開發人員選項」，開啟搜尋結果並開啟「USB 偵錯」。",
        ),
        "ja": (
            "「設定 › 端末情報（またはデバイスについて）」で「ビルド番号」を 7 回タップします。"
            "「バージョン」があれば先に開きます。",
            "設定で「開発者向けオプション」を検索して開き、「USB デバッグ」をオンにします。",
        ),
        "ko": (
            "설정 › 휴대전화 정보(또는 디바이스 정보)에서 빌드 번호를 7번 누릅니다. 버전 메뉴가 있다면 먼저 엽니다.",
            "설정에서 개발자 옵션을 검색해 연 다음 USB 디버깅을 켭니다.",
        ),
    },
    "motorola": {
        "en": (
            "Open Settings › About phone, or Settings › System › About phone on some models. Tap Build number seven times.",
            "Go to Settings › System › Developer options. If the System page has Advanced, check there. Turn on USB debugging.",
        ),
        "zh_TW": (
            "開啟「設定 › 關於手機」。部分型號要先進入「設定 › 系統 › 關於手機」。連點「版本號碼」七次。",
            "前往「設定 › 系統 › 開發人員選項」。若「系統」下有「進階」，也可在其中尋找。開啟「USB 偵錯」。",
        ),
        "ja": (
            "「設定 › デバイス情報」で「ビルド番号」を 7 回タップします。機種によっては先に「設定 › システム」を開きます。",
            "「設定 › システム › 開発者向けオプション」で「USB デバッグ」をオンにします。"
            "「詳細設定」が表示される場合はその中も確認します。",
        ),
        "ko": (
            "설정 › 휴대전화 정보에서 빌드 번호를 7번 누릅니다. 일부 모델에서는 설정 › 시스템을 먼저 엽니다.",
            "설정 › 시스템 › 개발자 옵션에서 USB 디버깅을 켭니다. 시스템에 고급 메뉴가 있으면 그 안을 확인합니다.",
        ),
    },
    "realme": {
        "en": (
            "Open Settings › About device › Version and tap Build number seven times.",
            "Open Developer options and enable USB debugging. In Settings, look under System & Updates "
            "(realme UI 6–7), System settings or Additional settings (3–5), or Additional settings (1–2).",
        ),
        "zh_TW": (
            "開啟「設定 › 關於本機 › 版本」，連點「版本號碼（Build number）」七次。",
            "進入「開發人員選項」並開啟「USB 偵錯」。在「設定」下尋找「系統與更新」（realme UI 6–7）"
            "、「系統設定／其他設定」（3–5），或「其他設定」（1–2）。",
        ),
        "ja": (
            "「設定 › デバイスについて › バージョン」で「ビルド番号」を 7 回タップします。",
            "「開発者向けオプション」で「USB デバッグ」をオンにします。設定内の「システムと更新」（realme UI 6～7）"
            "、「システム設定／その他の設定」（3～5）、または「その他の設定」（1～2）にあります。",
        ),
        "ko": (
            "설정 › 디바이스 정보 › 버전에서 빌드 번호를 7번 누릅니다.",
            "개발자 옵션에서 USB 디버깅을 켭니다. 설정의 시스템 및 업데이트(realme UI 6~7)나 "
            "시스템 설정이나 추가 설정(3~5), 또는 추가 설정(1~2)을 확인합니다.",
        ),
    },
    "other": {
        "en": (
            "Find Build number under Settings › About phone. You may need to open Software information first. "
            "Tap Build number seven times.",
            "Search Settings for Developer options and turn on USB debugging. The menu is usually under "
            "System on newer Android versions or on the main Settings page on older versions.",
        ),
        "zh_TW": (
            "在「設定 › 關於手機」尋找「版本號碼」，有些型號要先開啟「軟體資訊」。連點「版本號碼」七次。",
            "在「設定」搜尋「開發人員選項」並開啟「USB 偵錯」。較新的 Android 通常放在「系統」下，"
            "較舊的版本可能直接顯示在「設定」主畫面。",
        ),
        "ja": (
            "「設定 › 端末情報」で「ビルド番号」を 7 回タップします。機種によっては先に「ソフトウェア情報」を開きます。",
            "設定で「開発者向けオプション」を検索して開き、「USB デバッグ」をオンにします。"
            "新しい Android では通常「システム」の中にあり、旧バージョンでは設定のメイン画面に表示される場合があります。",
        ),
        "ko": (
            "설정 › 휴대전화 정보에서 빌드 번호를 7번 누릅니다. 기종에 따라 소프트웨어 정보를 먼저 열어야 합니다.",
            "설정에서 개발자 옵션을 검색해 USB 디버깅을 켭니다. 최근 Android는 주로 시스템 아래에, "
            "이전 버전은 설정 첫 화면에 표시됩니다.",
        ),
    },
}

_CONNECTION_STEPS = {
    "en": (
        "Confirm your phone's screen lock if prompted.",
        "Keep the phone unlocked and connect it to your PC with a USB data cable.",
        "When the phone asks to allow USB debugging, approve the RSA key for a computer you trust. "
        "Return to tt tool and select Scan again.",
    ),
    "zh_TW": (
        "若出現提示，請完成手機的螢幕鎖定驗證。",
        "保持手機解鎖，用支援資料傳輸的 USB 線連接電腦。",
        "在手機的 USB 偵錯提示中核准可信任電腦的 RSA 金鑰。回到 tt tool，按「重新偵測」。",
    ),
    "ja": (
        "求められた場合は画面ロックの認証を行います。",
        "画面ロックを解除したまま、データ通信対応の USB ケーブルで PC に接続します。",
        "USB デバッグの確認が表示されたら、信頼できる PC の RSA 鍵を許可します。tt tool に戻って「再検出」を押します。",
    ),
    "ko": (
        "메시지가 표시되면 화면 잠금을 인증합니다.",
        "잠금을 해제한 상태에서 데이터 전송을 지원하는 USB 케이블로 PC에 연결합니다.",
        "USB 디버깅 허용 메시지가 표시되면 신뢰하는 PC의 RSA 키를 승인합니다. tt tool로 돌아와 다시 검색을 누릅니다.",
    ),
}


def guide_for(brand_id: str, language: str) -> tuple[tuple[str, ...], str]:
    """Return the localized setup steps and official source URL without network access."""
    brand = brand_id if brand_id in _PATHS else "other"
    locale = language if language in _CONNECTION_STEPS else "en"
    reveal, enable = _PATHS[brand][locale]
    confirm_lock, connect, authorize = _CONNECTION_STEPS[locale]
    return (f"{reveal} {confirm_lock}", enable, connect, authorize), _SOURCES[brand]
