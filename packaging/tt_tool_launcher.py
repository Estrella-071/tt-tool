# SPDX-License-Identifier: GPL-3.0-only
"""Entry point used by tt tool's Start Menu shortcut."""
import ctypes
import os
from pathlib import Path
import sys
import traceback


def run():
    app_directory = Path(__file__).resolve().parent
    sys.path.insert(0, str(app_directory))  # Python -I doesn't add the script directory.
    os.environ.setdefault("TT_TOOL_DATA_DIR", str(Path(os.environ["LOCALAPPDATA"]) / "tt-tool/data"))
    data = Path(os.environ["TT_TOOL_DATA_DIR"])
    data.mkdir(parents=True, exist_ok=True)

    import qt_fishing

    icon = app_directory.parent / "tt-tool.ico"
    if "--check" in sys.argv:
        from fisher.phone_vision import PhoneDetector
        from fisher.ruins import RuinsDetector

        app = qt_fishing.QtWidgets.QApplication([])
        assert app.platformName() == "windows", app.platformName()
        app.setStyleSheet(qt_fishing.STYLE)
        window = qt_fishing.FishingWindow(install_root=app_directory.parent)
        window.setWindowIcon(qt_fishing.QtGui.QIcon(str(icon)))
        window.show()
        app.processEvents()
        PhoneDetector(app_directory / "assets/templates", .68)
        RuinsDetector()
        window.close()
        print("tt tool Qt Win32 startup OK")
    else:
        qt_fishing.main(icon_path=icon, install_root=app_directory.parent)


if __name__ == "__main__":
    try:
        run()
    except Exception:
        if "--check" in sys.argv:
            raise
        details = traceback.format_exc()
        data_dir = os.environ.get("TT_TOOL_DATA_DIR")
        if data_dir:
            try:
                (Path(data_dir) / "startup-error.log").write_text(details, encoding="utf-8")
            except OSError:
                pass
        ctypes.windll.user32.MessageBoxW(None, details.splitlines()[-1], "tt tool", 0x10)
        raise SystemExit(1)
