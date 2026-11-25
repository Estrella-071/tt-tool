# Windows x64 설치 안내

[English](INSTALLER.md) · [繁體中文](INSTALLER.zh-TW.md) · [日本語](INSTALLER.ja.md) · [한국어](INSTALLER.ko.md)

[tt-tool-1.0.6-windows-x64-setup.exe 다운로드](https://github.com/Estrella-071/tt-tool/releases/download/v1.0.6/tt-tool-1.0.6-windows-x64-setup.exe). Windows 10 22H2 또는 Windows 11 x64에서 사용할 수 있습니다. 설치 프로그램에는 Python, Qt와 로컬 이미지 인식 패키지가 포함됩니다. 휴대전화 연결에는 [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools)와 [FFmpeg](https://ffmpeg.org/download.html#build-windows)가 필요합니다.

## 설치와 실행

1. 설치 프로그램을 실행하고 English, 繁體中文, 日本語, 한국어 중 선택합니다. 앱을 처음 열 때 선택한 언어가 적용됩니다.
2. 처음 설치할 때 폴더를 변경할 수 있습니다. 기본 위치는 현재 사용자의 `%LOCALAPPDATA%\Programs\tt tool`입니다.
3. 만들 바로가기를 선택합니다. 시작 메뉴 바로가기는 기본 선택되어 있고 바탕 화면 바로가기는 기본 해제되어 있습니다.
4. 마지막 화면에서 설치 후 실행을 선택할 수 있습니다. 나중에 바로가기를 사용해도 됩니다. 외부 바로가기를 모두 해제해도 설치 폴더 안에 **tt tool** 바로가기가 남습니다.

설치 폴더에는 전체 GPL 라이선스가 포함되며 **관리 → 라이선스 보기**에서도 읽을 수 있습니다.

tt tool은 사용자 `Path`에서 `adb.exe`와 `ffmpeg.exe`를 찾습니다. 기기 메뉴의 **연결 도구**에서 실행 파일을 직접 선택한 다음 **확인하고 다시 시도**할 수 있습니다. 앱의 **USB 연결 안내** 또는 [제조사별 안내](USB-DEBUGGING.ko.md)에 따라 휴대전화를 준비하세요. Android는 `screenrecord --time-limit 0`을 지원해야 합니다.

## 업데이트

앱에 이전 버전 번호 v1.1.0, v1.2.0 또는 v1.3.0이 표시되면 앱을 닫고 기존 설치 폴더에 v1.0.6 설치 프로그램을 한 번 실행하세요. 설정은 유지되며 이후 새 버전의 앱 내 업데이트를 사용할 수 있습니다. 이전 릴리스 v1.0.2~v1.0.4에는 원래 설치 파일과 체크섬이 포함됩니다.

설치된 v1.0.5 이상에서는 **관리 → 업데이트 확인**을 선택합니다. 요청 시 GitHub의 최신 안정 버전을 확인합니다. 검증 가능한 설치 파일이 있으면 **다운로드 및 설치**를 선택해 다운로드할 수 있으며 도중에 취소할 수 있습니다. SHA-256을 비교한 뒤 현재 활동을 중지하고 창을 닫아 기존 위치에 설치할지 확인합니다. 설치 진행 상황이 표시되며 완료 후 tt tool이 다시 열립니다.

업데이트가 완료되거나 실패하거나 취소되면 임시 설치 파일이 정리됩니다. 앱 내 업데이트를 사용할 수 없거나 소스에서 실행할 때는 **릴리스 페이지 열기**에서 직접 설치 파일을 다운로드할 수 있습니다. 업데이트 후 설정, 표시 언어, 보정값과 로컬 로그가 유지됩니다.

## 파일과 제거

**관리**에서 **파일 위치 열기** 또는 **설정 폴더 열기**를 선택합니다. 소스 버전의 `phone_settings.json`과 `tt_tool_ui.json`을 `%LOCALAPPDATA%\tt-tool\data`로 옮기려면 두 앱을 모두 먼저 닫으세요.

설치 버전은 tt tool의 **제거…** 또는 Windows 설정의 **설치된 앱**에서 제거할 수 있습니다. 확인 화면에 설치 폴더가 표시됩니다. tt tool에서 시작하면 활동과 앱을 종료하기 전에 확인합니다. 제거 프로그램은 진행 상황과 결과를 표시하고 최신 안정 버전 릴리스 페이지를 여는 버튼을 제공합니다.

설정, 보정값, 진단 로그는 기본적으로 `%LOCALAPPDATA%\tt-tool\data`에 보존됩니다. 이 폴더도 제거하려면 로컬 데이터 삭제 항목을 선택하세요.

## 다운로드 검증

설치 정보의 게시자는 **71**입니다. 설치 프로그램에 Authenticode 서명이 없으므로 Windows에서 **알 수 없는 게시자**로 표시될 수 있습니다. 직접 다운로드한 파일의 SHA-256을 [같은 GitHub 릴리스의 체크섬](https://github.com/Estrella-071/tt-tool/releases/download/v1.0.6/SHA256SUMS.txt)과 비교할 수 있습니다.

```powershell
Get-FileHash .\tt-tool-1.0.6-windows-x64-setup.exe -Algorithm SHA256
```

## 설치 프로그램 빌드 및 검증

Windows x64, Python 3.12, [Inno Setup 7 x64](https://jrsoftware.org/inno-setup/downloads)를 사용합니다. [한국어 README](../README.ko.md)에 따라 Python 환경을 준비한 뒤 저장소 루트에서 실행하세요.

```powershell
.\.venv\Scripts\python.exe selfcheck.py
.\.venv\Scripts\python.exe build_tt_tool.py --iscc "C:\Program Files\Inno Setup 7\ISCC.exe"
```

빌드는 고정된 매니페스트와 의존성을 비교하고 독립 실행 환경과 Qt 시작을 확인합니다. 설치 파일은 `dist\`에 생성됩니다. `.\.venv\Scripts\python.exe build_tt_tool.py --check-payload`로 실행 환경만 별도 확인할 수 있습니다.

릴리스할 커밋에서 빌드하고 [Windows 설치 워크플로](https://github.com/Estrella-071/tt-tool/actions/workflows/tt-tool-installer.yml)로 설치, 바로가기 실행, 업데이트, 제거를 검증합니다. 해당 실행에서 생성된 EXE와 체크섬을 사용하고 릴리스 태그가 검증된 커밋을 가리키게 합니다.

[타사 구성 요소와 소스 코드](THIRD-PARTY.ko.md)
