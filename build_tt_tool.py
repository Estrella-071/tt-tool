# SPDX-License-Identifier: GPL-3.0-only
"""Build the tt tool Windows x64 installer from a clean source tree."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_windows import fetch, unpack_runtime, unpack_wheel, validate_runtime
from fisher.config import ROOT
from fisher.project import VERSION

NAME = f"tt-tool-{VERSION}-windows-x64"
COMPONENTS = ROOT / "packaging" / "tt-tool-runtime.lock.json"
LAUNCHER = "tt_tool_launcher.py"
PHONE_MODULES = (
    "__init__", "adb", "adb_help", "config", "contact", "controller", "device_profiles",
    "emulators", "i18n", "maintenance", "phase", "phone_runtime", "phone_vision",
    "project", "ruins", "updater",
    "ruins_battle_result", "ruins_chest", "ruins_diagnostics", "ruins_geometry",
    "ruins_odds", "ruins_runtime", "speed", "templates", "vision", "visual_settings",
)


def copy_payload(payload, cache):
    base = json.loads((ROOT / "packaging/windows-runtime.lock.json").read_text(encoding="utf-8"))
    extra = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    if base["target"] != "windows-x86_64" or base["schema_version"] != 1:
        raise ValueError("Unsupported Windows runtime lock")
    wheels = [item for item in base["wheels"] if item["name"] in ("numpy", "opencv_python_headless")]
    wheels.extend(extra["wheels"])
    runtime = payload / "runtime"
    packages = runtime / "Lib" / "site-packages"
    unpack_runtime(fetch(base["python"], cache), runtime)
    for wheel in wheels:
        unpack_wheel(fetch(wheel, cache), packages)

    # Phone capture uses an external FFmpeg process, independent of OpenCV video I/O.
    for plugin in (packages / "cv2").glob("opencv_videoio_ffmpeg*_64.dll"):
        plugin.unlink()
    validate_runtime(runtime, required=(
        "python.exe", "pythonw.exe", "python312.dll", "vcruntime140.dll", "vcruntime140_1.dll",
        "LICENSE.txt", "Lib/site-packages/numpy/__init__.py", "Lib/site-packages/cv2/__init__.py",
        "Lib/site-packages/PySide6/plugins/platforms/qwindows.dll",
    ))

    app = payload / "app"
    app.mkdir()
    shutil.copyfile(ROOT / "qt_fishing.py", app / "qt_fishing.py")
    shutil.copyfile(ROOT / "packaging" / LAUNCHER, app / LAUNCHER)
    compile_update_helper(app)
    (app / "fisher").mkdir()
    for module in PHONE_MODULES:
        name = f"fisher/{module}.py"
        shutil.copyfile(ROOT / name, app / name)
    for folder in ("assets/templates", "assets/ruins"):
        target = app / folder
        target.mkdir(parents=True)
        for source in (ROOT / folder).glob("*.png"):
            shutil.copyfile(source, target / source.name)
    for source in ("LICENSE", "NOTICE.md", "docs/THIRD-PARTY.md"):
        destination = payload / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, destination)
    shutil.copyfile(ROOT / "packaging/tt-tool.ico", payload / "tt-tool.ico")
    dependencies = {"target": base["target"], "python": base["python"], "wheels": wheels}
    (payload / "DEPENDENCIES.json").write_text(json.dumps(dependencies, indent=2) + "\n", encoding="utf-8")


def compile_update_helper(app):
    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    target = app / f"tt-tool-update-{VERSION}.exe"
    subprocess.run(
        [str(compiler), "/nologo", "/optimize+", "/warnaserror+", "/target:winexe", "/platform:x64",
         "/reference:System.Windows.Forms.dll", f"/out:{target}", str(ROOT / "packaging/update-handoff.cs")],
        check=True, timeout=60,
    )


def smoke_payload(payload, data):
    env = os.environ.copy()
    env.update(TT_TOOL_DATA_DIR=str(data), QT_QPA_PLATFORM="windows")
    argv = [str(payload / "runtime/python.exe"), "-I", "-B", str(payload / "app" / LAUNCHER), "--check"]
    subprocess.run(argv, cwd=data.parent, env=env, check=True, timeout=60)


def build(cache, output, iscc, check_only):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tt-tool-build-") as temp:
        scratch = Path(temp)
        payload = scratch / "payload"
        copy_payload(payload, cache)
        smoke_payload(payload, scratch / "smoke-data")
        if check_only:
            print("Windows x64 payload and Qt startup verified.")
            return
        subprocess.run(
            [str(iscc), f"/DPayloadDir={payload}", f"/DAppVersion={VERSION}",
             f"/F{NAME}-setup", f"/O{output}", str(ROOT / "packaging/tt-tool.iss")],
            check=True, timeout=900,
        )
    if not (output / f"{NAME}-setup.exe").is_file():
        raise FileNotFoundError("Installer missing after compilation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--cache", type=Path, default=ROOT / ".build-cache")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--iscc", type=Path, help="Path to the Inno Setup 7 x64 ISCC.exe")
    parser.add_argument("--check-payload", action="store_true", help="Validate the runtime and Qt startup only")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Windows is required for the Qt startup check")
    if not args.check_payload and (args.iscc is None or not args.iscc.is_file()):
        parser.error("Pass the path to ISCC.exe or use --check-payload")
    build(args.cache.resolve(), args.output.resolve(), args.iscc.resolve() if args.iscc else None, args.check_payload)


if __name__ == "__main__":
    main()
