# SPDX-License-Identifier: GPL-3.0-only
"""Desktop maintenance actions for the Windows installation."""
import json
import re
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtNetwork, QtWidgets

from .config import DATA_ROOT, ROOT
from .project import PROJECT_URL, VERSION

LATEST_API = "https://api.github.com/repos/Estrella-071/tt-tool/releases/latest"
LATEST_PAGE = PROJECT_URL + "/releases/latest"
RELEASE_JSON_LIMIT = 1024 * 1024
UNINSTALL_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    r"\{74A2509B-977F-47DC-8C34-409B3CB77523}_is1"
)


def version_parts(version):
    match = re.fullmatch(r"v?([0-9]{1,6})\.([0-9]{1,6})\.([0-9]{1,6})", version)
    if not match:
        raise ValueError("Expected a three-part tt tool release version")
    return tuple(map(int, match.groups()))


def latest_version(payload):
    release = json.loads(payload)
    if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
        raise ValueError("Expected a published stable release")
    return ".".join(map(str, version_parts(release.get("tag_name", ""))))


def uninstall_program(install_root):
    if install_root is None or sys.platform != "win32":
        return None

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            command, _ = winreg.QueryValueEx(key, "UninstallString")
        if not isinstance(command, str):
            return None
        path = Path(command.strip().strip('"')).resolve()
        if (path.parent == install_root.resolve()
                and re.fullmatch(r"unins[0-9]{3}\.exe", path.name, re.IGNORECASE)
                and path.is_file() and path.with_suffix(".dat").is_file()):
            return path
    except (OSError, ValueError):
        pass
    return None


class Maintenance(QtCore.QObject):
    version = VERSION

    def __init__(self, window, install_root=None):
        super().__init__(window)
        self.window = window
        self.install_root = Path(install_root) if install_root is not None else None
        self.network = QtNetwork.QNetworkAccessManager(self)
        self.reply = None

    def menu(self, anchor):
        tr = self.window.tr
        menu = QtWidgets.QMenu(anchor)
        check = menu.addAction(tr("正在檢查更新…" if self.reply else "檢查更新"), self.check_updates)
        check.setEnabled(self.reply is None)
        menu.addAction(tr("開啟檔案位置"), self.open_app_folder)
        menu.addAction(tr("開啟設定資料夾"), self.open_data_folder)
        if uninstall_program(self.install_root) is not None:
            menu.addSeparator()
            menu.addAction(tr("解除安裝…"), self.uninstall)
        return menu

    def dialog(self, title, message, action=None, *, destructive=False):
        """Use the main window's palette and button treatment for maintenance."""
        dialog = QtWidgets.QDialog(self.window, QtCore.Qt.WindowType.FramelessWindowHint)
        dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        dialog.setWindowTitle(self.window.tr(title))
        dialog.setMinimumWidth(390)
        dialog.setMaximumWidth(490)
        outer = QtWidgets.QVBoxLayout(dialog)
        outer.setContentsMargins(0, 0, 0, 0)
        surface = QtWidgets.QFrame(dialog)
        surface.setObjectName("shell")
        content = QtWidgets.QVBoxLayout(surface)
        content.setContentsMargins(28, 22, 28, 24)
        content.setSpacing(12)
        heading = self.window.label(title, "heading")
        content.addWidget(heading)
        detail = self.window.label(message, "controlSubtitle")
        detail.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        content.addWidget(detail)
        content.addSpacing(10)
        controls = QtWidgets.QHBoxLayout()
        controls.addStretch()
        close_text = "取消" if destructive else "關閉"
        close = self.window.button(close_text, dialog.reject)
        controls.addWidget(close)
        close.setDefault(True)
        close.setFocus()
        if action:
            confirm = self.window.button(action, dialog.accept, "danger" if destructive else "primary")
            confirm.setAutoDefault(False)
            controls.addWidget(confirm)
        content.addLayout(controls)
        outer.addWidget(surface)
        try:
            return dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
        finally:
            dialog.deleteLater()

    def check_updates(self):
        if self.reply is not None:
            return
        request = QtNetwork.QNetworkRequest(QtCore.QUrl(LATEST_API))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent", b"tt-tool/" + self.version.encode("ascii"))
        request.setAttribute(QtNetwork.QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QtNetwork.QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        reply = self.network.get(request)
        self.reply = reply
        reply.setReadBufferSize(RELEASE_JSON_LIMIT + 1)
        reply.readyRead.connect(self.limit_reply)
        deadline = QtCore.QTimer(reply)
        deadline.setSingleShot(True)
        deadline.timeout.connect(reply.abort)
        reply.finished.connect(deadline.stop)
        reply.finished.connect(self.update_ready)
        deadline.start(8000)

    def limit_reply(self):
        if self.reply.bytesAvailable() > RELEASE_JSON_LIMIT:
            self.reply.abort()

    def update_ready(self):
        reply, self.reply = self.reply, None
        try:
            status = reply.attribute(QtNetwork.QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if reply.error() != QtNetwork.QNetworkReply.NetworkError.NoError or status != 200:
                raise ValueError("Could not fetch the latest release")
            newest = latest_version(bytes(reply.readAll()))
        except (ValueError, TypeError):
            self.offer_releases("無法檢查更新", "目前無法連線確認版本。你可以開啟發布頁查看。")
        else:
            installed = version_parts(self.version)
            available = version_parts(newest)
            fields = {"current": self.version, "latest": newest}
            if available > installed:
                message = self.window.tr("目前版本為 v{current}，可下載 v{latest}。").format(**fields)
                self.offer_releases("有新版本", message)
            else:
                source = ("目前版本 v{current} 已是最新。" if available == installed
                          else "目前版本 v{current} 比公開版 v{latest} 新。")
                message = self.window.tr(source).format(**fields)
                self.dialog("更新檢查", message)
        finally:
            reply.deleteLater()

    def offer_releases(self, title, message):
        if (self.dialog(title, message, "開啟發布頁")
                and not QtGui.QDesktopServices.openUrl(QtCore.QUrl(LATEST_PAGE))):
            self.dialog("無法開啟發布頁", LATEST_PAGE)

    def open_app_folder(self):
        self.open_folder(self.install_root if self.install_root is not None else ROOT)

    def open_data_folder(self):
        self.open_folder(DATA_ROOT)

    def open_folder(self, path):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path))):
            self.dialog("無法開啟資料夾", str(path))

    def uninstall(self):
        if not self.dialog("解除安裝 tt tool？", "正在執行的活動將結束。已儲存的設定與校正資料會保留。",
                           "解除安裝", destructive=True):
            return
        program = uninstall_program(self.install_root)
        fallback = "請從 Windows 的「已安裝的應用程式」解除安裝。"
        if program is None:
            self.dialog("找不到解除安裝程式", fallback)
            return
        # Release the phone session before handing off to the uninstaller.
        if self.window.runner:
            self.window.disconnect()
        started, _ = QtCore.QProcess.startDetached(
            str(program), ["/SILENT", "/NORESTART"], str(program.parent.parent),
        )
        if started:
            self.window.close()
        else:
            self.dialog("無法啟動解除安裝程式", fallback)
