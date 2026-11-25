# SPDX-License-Identifier: GPL-3.0-only
"""Desktop maintenance actions for the Windows installation."""
import json
import re
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtNetwork, QtWidgets

from .config import DATA_ROOT, ROOT
from .project import PROJECT_URL, VERSION
from .updater import InstallerDownload, installed_helper, process_identity, release_asset

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
    return parse_release(payload)[1]


def parse_release(payload):
    release = json.loads(payload)
    if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
        raise ValueError("Expected a published stable release")
    version = ".".join(map(str, version_parts(release.get("tag_name", ""))))
    return release, version


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
        command = command.strip()
        quoted = re.fullmatch(r'"([^"]+)"(?: /SILENT /NORESTART /TTTOOLPROMPT)?', command)
        path = Path(quoted[1] if quoted else command).resolve()
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
        self.download = None

    def menu(self, anchor):
        tr = self.window.tr
        menu = QtWidgets.QMenu(anchor)
        check = menu.addAction(tr("正在檢查更新…" if self.reply else "檢查更新"), self.check_updates)
        check.setEnabled(self.reply is None and self.download is None)
        menu.addAction(tr("開啟檔案位置"), self.open_app_folder)
        menu.addAction(tr("開啟設定資料夾"), self.open_data_folder)
        if uninstall_program(self.install_root) is not None:
            menu.addSeparator()
            menu.addAction(tr("解除安裝…"), self.uninstall)
        return menu

    def panel(self, title, *, width=490):
        dialog = QtWidgets.QDialog(self.window, QtCore.Qt.WindowType.FramelessWindowHint)
        dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        dialog.setWindowTitle(self.window.tr(title))
        dialog.setFixedWidth(width)
        outer = QtWidgets.QVBoxLayout(dialog)
        outer.setContentsMargins(0, 0, 0, 0)
        surface = QtWidgets.QFrame(dialog)
        surface.setObjectName("shell")
        content = QtWidgets.QVBoxLayout(surface)
        content.setContentsMargins(28, 22, 28, 24)
        content.setSpacing(12)
        heading = self.window.label(title, "heading")
        content.addWidget(heading)
        outer.addWidget(surface)
        return dialog, content

    def dialog(self, title, message, action=None, *, destructive=False, option=None):
        """Present a styled confirmation, with an optional off-by-default choice."""
        dialog, content = self.panel(title)
        detail = self.window.label(message, "controlSubtitle")
        detail.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        content.addWidget(detail)
        choice = None
        if option:
            choice = QtWidgets.QCheckBox(self.window.tr(option), dialog)
            content.addWidget(choice)
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
        try:
            accepted = dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
            return (accepted, choice.isChecked()) if choice is not None else accepted
        finally:
            dialog.deleteLater()

    def check_updates(self):
        if self.reply is not None or self.download is not None:
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
        if self.reply is not None and self.reply.bytesAvailable() > RELEASE_JSON_LIMIT:
            self.reply.abort()

    def update_ready(self):
        reply, self.reply = self.reply, None
        try:
            status = reply.attribute(QtNetwork.QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            if reply.error() != QtNetwork.QNetworkReply.NetworkError.NoError or status != 200:
                raise ValueError("Could not fetch the latest release")
            payload = bytes(reply.read(RELEASE_JSON_LIMIT + 1))
            if len(payload) > RELEASE_JSON_LIMIT:
                raise ValueError("Release data exceeds the response limit")
            release, newest = parse_release(payload)
        except (ValueError, TypeError):
            self.offer_releases("無法檢查更新", "目前無法連線確認版本。你可以開啟發布頁查看。")
        else:
            installed = version_parts(self.version)
            available = version_parts(newest)
            fields = {"current": self.version, "latest": newest}
            if available > installed:
                message = self.window.tr("目前版本為 v{current}，可下載 v{latest}。").format(**fields)
                helper = installed_helper(self.install_root, self.version)
                asset = release_asset(release, newest)
                if helper is not None and asset is not None:
                    self.offer_update(message, asset)
                else:
                    self.offer_releases("有新版本", message)
            else:
                source = ("目前版本 v{current} 已是最新。" if available == installed
                          else "目前版本 v{current} 比公開版 v{latest} 新。")
                message = self.window.tr(source).format(**fields)
                self.offer_releases("更新檢查", message)
        finally:
            reply.deleteLater()

    def offer_releases(self, title, message):
        if self.dialog(title, message, "開啟發布頁"):
            self.open_release_page()

    def open_release_page(self):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(LATEST_PAGE)):
            self.dialog("無法開啟發布頁", LATEST_PAGE)

    def offer_update(self, message, asset):
        dialog, content = self.panel("有新版本")
        content.addWidget(self.window.label(message, "controlSubtitle"))
        controls = QtWidgets.QHBoxLayout()
        controls.addStretch()
        controls.addWidget(self.window.button("關閉", dialog.reject))
        page = self.window.button("開啟發布頁", lambda: dialog.done(2))
        controls.addWidget(page)
        download = self.window.button("下載並安裝", dialog.accept, "primary")
        controls.addWidget(download)
        content.addLayout(controls)
        try:
            selection = dialog.exec()
        finally:
            dialog.deleteLater()
        if selection == QtWidgets.QDialog.DialogCode.Accepted:
            self.start_download(asset)
        elif selection == 2:
            self.open_release_page()

    def start_download(self, asset):
        try:
            job = InstallerDownload(self.network, asset, self)
        except OSError:
            self.download_error()
            return
        self.download = job
        dialog, content = self.panel("正在下載更新…")
        progress = QtWidgets.QProgressBar(dialog)
        progress.setRange(0, 100)
        progress.setValue(0)
        content.addWidget(progress)
        controls = QtWidgets.QHBoxLayout()
        controls.addStretch()
        controls.addWidget(self.window.button("取消", dialog.reject))
        content.addLayout(controls)
        job.progress.connect(lambda value: progress.setValue(int(value * 100)))
        job.verified.connect(dialog.accept)
        job.failed.connect(lambda: dialog.done(2))
        dialog.finished.connect(lambda result: self.download_finished(job, dialog, result))
        dialog.open()
        job.start()

    def download_finished(self, job, dialog, result):
        dialog.deleteLater()
        job.stop()
        handed_off = False
        try:
            if result == QtWidgets.QDialog.DialogCode.Accepted:
                handed_off = self.install_update(job.file)
        finally:
            if not handed_off:
                try:
                    job.file.cleanup()
                except OSError:
                    result = 2
            self.download = None
            job.deleteLater()
        if result == 2:
            self.download_error()

    def download_error(self):
        self.offer_releases("無法下載更新", "更新未完成。你可以從發布頁下載安裝程式重試。")

    def install_update(self, file):
        if not self.dialog(
            "更新已驗證", "將結束目前活動、安裝更新並重新開啟 tt tool。Windows 可能會顯示安全性提示。",
            "安裝更新",
        ):
            return False
        helper = installed_helper(self.install_root, self.version)
        started = False
        if helper is not None:
            arguments = self.install_arguments(file)
            if arguments is not None:
                started, _ = QtCore.QProcess.startDetached(str(helper), arguments, str(helper.parent))
        if started:
            self.window.close()
            return True
        self.offer_releases("無法安裝更新", "更新未完成。你可以從發布頁下載安裝程式重試。")
        return False

    def install_arguments(self, file):
        try:
            pid, created = process_identity()
        except OSError:
            return None
        return [pid, created, str(file.installer), file.asset.sha256, self.window.tr("無法安裝更新"),
                self.window.tr("更新未完成。你可以從發布頁下載安裝程式重試。")]

    def open_app_folder(self):
        self.open_folder(self.install_root if self.install_root is not None else ROOT)

    def open_data_folder(self):
        self.open_folder(DATA_ROOT)

    def open_folder(self, path):
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path))):
            self.dialog("無法開啟資料夾", str(path))

    def uninstall(self):
        question = self.window.tr("tt tool 將關閉，正在執行的活動也會結束。是否繼續解除安裝？")
        location = self.window.tr("安裝位置")
        confirmed, clear_data = self.dialog(
            "解除安裝 tt tool？", f"{question}\n\n{location}\n{self.install_root}",
            "解除安裝", destructive=True, option="一併清除 tt tool 的本機資料",
        )
        if not confirmed:
            return
        program = uninstall_program(self.install_root)
        fallback = "請從 Windows 的「已安裝的應用程式」解除安裝。"
        if program is None:
            self.dialog("找不到解除安裝程式", fallback)
            return
        # Release the phone session before handing off to the uninstaller.
        if self.window.runner:
            self.window.disconnect()
        arguments = ["/SILENT", "/NORESTART", "/TTTOOLCOMPLETE"]
        if clear_data:
            arguments.append("/TTTOOLCLEARDATA")
        started, _ = QtCore.QProcess.startDetached(str(program), arguments, str(program.parent.parent))
        if started:
            self.window.close()
        else:
            self.dialog("無法啟動解除安裝程式", fallback)
