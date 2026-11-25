# SPDX-License-Identifier: GPL-3.0-only
"""按明确的源文件清单生成发布包，排除本机运行数据。"""
from hashlib import sha256
import json
from pathlib import Path
import zipfile
from .config import DEFAULTS, ROOT, validate_config
from .templates import TEMPLATE_DEFINITIONS

PUBLIC_FILES = (
    "fisher/ruins.py", "fisher/ruins_runtime.py", "fisher/ruins_geometry.py", "fisher/ruins_odds.py", "fisher/ruins_diagnostics.py", "fisher/ruins_battle_result.py", "fisher/ruins_chest.py", "assets/ruins/digits.png", "assets/ruins/lobby_title.png",
    "fisher/device_profiles.py", "fisher/i18n.py", "fisher/visual_settings.py",
    "tests/test_ruins.py", "tests/test_ruins_odds.py", "tests/test_ruins_diagnostics.py", "tests/test_ruins_battle_result.py", "tests/test_ruins_chest.py", "tests/test_device_profiles.py", "tests/test_phone_adaptation.py", "tests/test_i18n.py", "tests/test_visual_settings.py", "tests/assets/ruins/error_dialog.png", "tests/assets/ruins/lobby_stream.png",
    "adb_app.py", "qt_fishing.py", "start_adb.bat", "fisher/adb.py", "fisher/phone_runtime.py", "tests/test_phone_recovery.py", "tests/assets/phone_idle_stalled.png",
    "fisher/phone_vision.py", "tests/test_adb.py", "tests/test_qt_layout.py", "tests/assets/phone_bite.png", "tests/assets/phone_weight_bronze.png", "docs/ADB.md", "docs/VALIDATION-ADB.md",
    "README.md", "LICENSE", "NOTICE.md", "CHANGELOG.md", "requirements.txt",
    "README.en.md", "README.zh-TW.md", "README.ja.md", "README.ko.md", "docs/EMULATOR.md",
    "fisher/adb_help.py", "docs/USB-DEBUGGING.md", "fisher/maintenance.py", "tests/test_maintenance.py",
    "docs/INSTALLER.md", "docs/THIRD-PARTY.md", "build_tt_tool.py",
    "packaging/tt-tool.iss", "packaging/tt-tool-messages.iss", "packaging/tt-tool.ico",
    "packaging/tt-tool-ui.iss", "packaging/tt_tool_launcher.py",
    "packaging/tt-tool-runtime.lock.json", "packaging/smoke-installer.ps1",
    ".github/workflows/tt-tool-installer.yml",
    ".gitignore", ".gitattributes", "config.example.json",
    "main.py", "desktop.py", "build_windows.py", "replay.py", "selfcheck.py", "build_release.py", "make_support_bundle.py",
    "fisher/__init__.py", "fisher/config.py", "fisher/controller.py", "fisher/runtime.py",
    "fisher/emulators.py", "tests/test_emulators.py", "tests/test_red_result.py", "tests/assets/record_weight_bronze.png",
    "tests/test_claim_result.py", "tests/assets/claim_button_scaled.png",
    "fisher/contact.py", "fisher/trial_capture.py", "tests/test_contact.py", "tests/test_trial.py", "docs/ALGORITHM.md",
    "fisher/jsonio.py", "tests/test_diagnostics.py", "tests/assets/timing_marker_clear.png", "tests/assets/timing_marker_split.png",
    "tests/test_followup.py", "tests/assets/timing_right_approach.png", "tests/assets/timing_hit_effect.png",
    "fisher/speed.py", "fisher/phase.py", "tests/test_phase.py", "tests/test_speed.py", "tests/test_arrival.py",
    "fisher/templates.py", "fisher/scheduling.py", "fisher/vision.py", "fisher/windows.py", "fisher/project.py", "fisher/packaging.py",
    "tests/fixtures.py", "tests/test_behavior.py", "tests/test_options.py", "tests/test_startup.py", "tests/test_release.py",
    "tests/test_desktop.py", "tests/test_windows_package.py",
    "packaging/windows-runtime.lock.json", "packaging/start.bat", "packaging/check.bat",
    "packaging/portable-readme.txt", "docs/WINDOWS.md",
    ".github/workflows/windows-portable.yml",
    "docs/DEVELOPMENT.md", "docs/PRIVACY.md", "docs/images/crop-example.png",
    ".github/ISSUE_TEMPLATE/bug_report.md",
) + tuple(
    f"docs/images/tt-tool/{locale}-{view}.png"
    for locale in ("zh_TW", "en", "ja", "ko")
    for view in ("main", "settings")
) + tuple(f"assets/templates/{name}.png" for name in TEMPLATE_DEFINITIONS) + tuple(f"tests/assets/ruins/{name}.png" for name in ("lobby", "lobby_multiplier_stream", "advance", "reward", "boss90", "boss45", "boss80", "boss80_stream", "boss80_bonus_stream", "boss90_bonus_stream", "boss70_bonus_stream", "boss55_bonus_stream", "boss55_bonus8_stream", "boss30_bonus_stream", "boss25_bonus8_stream", "boss25_bonus5_stuck", "boss20_stream", "boss20_bonus8_stream", "boss50_red", "milestone", "claim", "victory", "battle_win", "battle_loss", "chest_batch", "chest_confirm", "chest_split"))


def source_payloads(root=ROOT):
    root = Path(root)
    payloads = {}
    for name in PUBLIC_FILES:
        path = root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"发布文件不能是符号链接或越界路径：{name}")
        if not path.is_file():
            raise FileNotFoundError(f"缺少发布文件：{name}")
        payloads[name] = path.read_bytes()
    example = json.loads(payloads["config.example.json"].decode("utf-8"))
    validate_config(example)
    if example.get("profile") is not None or set(example)-set(DEFAULTS):
        raise ValueError("示例配置不得包含个人框选或额外字段")
    return payloads


def write_archive(path, payloads):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for name in payloads:
        if Path(name).is_absolute() or ".." in Path(name).parts or "\\" in name or name == "SHA256SUMS":
            raise ValueError(f"无效的压缩包路径：{name}")
    manifest = "\n".join(f"{sha256(data).hexdigest()}  {name}" for name,data in sorted(payloads.items()))+"\n"
    temp = path.with_suffix(path.suffix+".tmp")
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
            for name,data in sorted(payloads.items()):
                archive.writestr(name,data)
            archive.writestr("SHA256SUMS",manifest)
        with zipfile.ZipFile(temp) as archive:
            if archive.testzip() is not None:
                raise OSError("压缩包完整性校验失败")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return path
