# Windows 설치 프로그램 재배포 공지

[English](THIRD-PARTY.md) · [繁體中文](THIRD-PARTY.zh-TW.md) · [日本語](THIRD-PARTY.ja.md) · 한국어

tt tool는 GPL-3.0 전용으로 배포됩니다. 번들로 제공되는 `LICENSE` 및 `NOTICE.md`를 참조하세요. 해당 애플리케이션, 설치 프로그램 및 업데이트 소스는 [v1.0.6 소스 tree](https://github.com/Estrella-071/tt-tool/tree/v1.0.6). 설치 프로그램에는 전화 앱용 소스 파일도 포함되어 있습니다.

- Qt 6.11.0, PySide6 Essentials 6.11.0 및 Shiboken 6.11.0은 GPLv3 커뮤니티 라이센스 옵션에 따라 사용됩니다. GNU GPL 라이센스 텍스트는 `LICENSE`로 포함됩니다. Qt에서 [Qt 6.11.0 source](https://download.qt.io/archive/qt/6.11/6.11.0/single/) 및 [PySide6 및 Shiboken 6.11.0 source](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.0-src/)]를 다운로드합니다. 버전이 지정된 휠 URL과 다이제스트는 `DEPENDENCIES.json`에 있습니다. Qt 라이브러리는 별도의 파일로 설치됩니다. [Qt 라이센스 정보](https://doc.qt.io/qt-6/licensing.html) 및 [Python용 Qt 공지사항](https://doc.qt.io/qtforpython-6/licenses.html).
- CPython 및 Tcl/Tk 라이센스가 런타임과 함께 제공됩니다. NumPy 및 OpenCV 알림은 설치된 패키지 및 메타데이터 디렉터리에 있습니다. 정확한 버전과 다운로드 URL은 `DEPENDENCIES.json`에 있습니다. OpenCV 비디오 I/O 휠의 선택적 FFmpeg 바이너리는 제외됩니다.
- 설정 엔진은 Jordan Russell과 Martijn Laan의 [Inno Setup 7.1.1](https://github.com/jrsoftware/issrc/tree/is-7_1_1)]입니다. [해당 라이센스](https://github.com/jrsoftware/issrc/blob/is-7_1_1/license.txt)를 참조하세요.
- Android 플랫폼 도구 및 FFmpeg는 공식 다운로드 페이지에서 사용자가 별도로 설치합니다. 이는 번들 Python 런타임과 독립적입니다.
