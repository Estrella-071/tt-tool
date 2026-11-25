# SPDX-License-Identifier: GPL-3.0-only
"""Validate and stream the Windows installer from the project's GitHub release."""
import hashlib
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from PySide6 import QtCore, QtNetwork

from .project import PROJECT_URL

MAX_INSTALLER_SIZE = 512 * 1024 * 1024
MAX_REDIRECTS = 3
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
DOWNLOAD_HOSTS = frozenset({
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
    "github-releases.githubusercontent.com",
})
HTTP_STATUS = QtNetwork.QNetworkRequest.Attribute.HttpStatusCodeAttribute


@dataclass(frozen=True)
class UpdateAsset:
    name: str
    url: str
    size: int
    sha256: str


def release_asset(release, version):
    """Return the exact published installer, with its GitHub-supplied digest."""
    tag = f"v{version}"
    assets = release.get("assets")
    if release.get("tag_name") != tag or not isinstance(assets, list):
        return None
    name = f"tt-tool-{version}-windows-x64-setup.exe"
    matches = [asset for asset in assets if isinstance(asset, dict) and asset.get("name") == name]
    if len(matches) != 1:
        return None
    match = matches[0]
    size = match.get("size")
    digest = match.get("digest")
    url = f"{PROJECT_URL}/releases/download/{tag}/{name}"
    if (match.get("state") != "uploaded" or match.get("browser_download_url") != url
            or type(size) is not int or not 0 < size <= MAX_INSTALLER_SIZE
            or not isinstance(digest, str) or not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest)):
        return None
    return UpdateAsset(name, url, size, digest[7:].lower())


def installed_helper(root, version):
    if sys.platform != "win32" or root is None:
        return None
    helper = root / "app" / f"tt-tool-update-{version}.exe"
    runtime = root / "runtime/pythonw.exe"
    if runtime.resolve() != Path(sys.executable).resolve() or not helper.is_file():
        return None
    return helper


def process_identity():
    """Return the current PID and Win32 process creation timestamp."""
    import ctypes
    from ctypes.wintypes import FILETIME

    creation, exited, kernel, user = (FILETIME() for _ in range(4))
    # -1 is the Win32 pseudo-handle for the current process.
    if not ctypes.windll.kernel32.GetProcessTimes(
        ctypes.c_void_p(-1), *(ctypes.byref(value) for value in (creation, exited, kernel, user))
    ):
        raise OSError("Could not read the current Windows process identity")
    return str(os.getpid()), str((creation.dwHighDateTime << 32) | creation.dwLowDateTime)


def trusted_redirect(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and parsed.netloc in DOWNLOAD_HOSTS
                and bool(parsed.path) and not parsed.fragment)
    except ValueError:
        return False


class InstallerFile:
    def __init__(self, asset):
        self.asset = asset
        base = os.getenv("TMP") or os.getenv("TEMP") if sys.platform == "win32" else None
        self.directory = Path(tempfile.mkdtemp(prefix="tt-tool-update-", dir=base))
        self.installer = self.directory / asset.name
        self.partial = self.directory / "download.part"
        self.received = 0
        self.digest = hashlib.sha256()
        try:
            self.stream = self.partial.open("xb")
        except OSError:
            self.directory.rmdir()
            raise

    def write(self, data):
        size = self.received + len(data)
        if size > self.asset.size:
            raise ValueError("Installer is larger than the published asset")
        self.stream.write(data)
        self.digest.update(data)
        self.received = size

    def verify(self):
        self.stream.close()
        if self.received != self.asset.size or self.digest.hexdigest() != self.asset.sha256:
            raise ValueError("Installer does not match the published asset")
        if sys.platform == "win32":
            # Keep the Internet zone on the verified file when it is renamed.
            with open(f"{self.partial}:Zone.Identifier", "xb") as marker:
                marker.write(b"[ZoneTransfer]\r\nZoneId=3\r\n")
        self.partial.rename(self.installer)

    def cleanup(self):
        self.stream.close()
        self.partial.unlink(missing_ok=True)
        self.installer.unlink(missing_ok=True)
        self.directory.rmdir()


class InstallerDownload(QtCore.QObject):
    progress = QtCore.Signal(float)
    verified = QtCore.Signal()
    failed = QtCore.Signal()

    def __init__(self, network, asset, parent=None):
        super().__init__(parent)
        self.network = network
        self.file = InstallerFile(asset)
        self.reply = None
        self.redirects = 0
        self.deadline = QtCore.QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(self._fail)

    def start(self):
        self.deadline.start(10 * 60 * 1000)
        self._request(QtCore.QUrl(self.file.asset.url))

    def _request(self, url):
        request = QtNetwork.QNetworkRequest(url)
        request.setRawHeader(b"User-Agent", b"tt-tool-updater")
        request.setRawHeader(b"Accept-Encoding", b"identity")
        request.setAttribute(QtNetwork.QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QtNetwork.QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        request.setTransferTimeout(20_000)
        reply = self.network.get(request)
        self.reply = reply
        reply.setReadBufferSize(256 * 1024)
        reply.readyRead.connect(lambda: self._read(reply))
        reply.finished.connect(lambda: self._finish(reply))

    def _read(self, reply):
        if self.reply is not reply:
            return
        if reply.attribute(HTTP_STATUS) != 200:
            reply.read(reply.bytesAvailable())
            return
        try:
            self._write_reply(reply)
        except (OSError, ValueError):
            self._fail()

    def _write_reply(self, reply):
        remaining = self.file.asset.size - self.file.received
        self.file.write(bytes(reply.read(min(reply.bytesAvailable(), remaining + 1))))
        self.progress.emit(self.file.received / self.file.asset.size)

    def _next_url(self, reply):
        if self.redirects >= MAX_REDIRECTS:
            return None
        target = reply.attribute(QtNetwork.QNetworkRequest.Attribute.RedirectionTargetAttribute)
        if not isinstance(target, QtCore.QUrl) or not target.isValid() or target.isEmpty():
            return None
        url = reply.url().resolved(target)
        return url if trusted_redirect(bytes(url.toEncoded()).decode("ascii")) else None

    def _finish(self, reply):
        if self.reply is not reply:
            return
        self.reply = None
        try:
            self._resolve(reply)
        except (OSError, ValueError):
            self._fail()
        finally:
            reply.deleteLater()

    def _resolve(self, reply):
        status = reply.attribute(HTTP_STATUS)
        if reply.error() != QtNetwork.QNetworkReply.NetworkError.NoError:
            raise ValueError("Installer download failed")
        if status in REDIRECT_CODES:
            redirect = self._next_url(reply)
            if redirect is None:
                raise ValueError("Untrusted installer redirect")
            self.redirects += 1
            self._request(redirect)
            return
        if status != 200:
            raise ValueError("Installer download failed")
        self._write_reply(reply)
        self.file.verify()
        self.deadline.stop()
        self.verified.emit()

    def stop(self):
        self.deadline.stop()
        reply, self.reply = self.reply, None
        if reply is not None:
            reply.abort()
            reply.deleteLater()

    def _fail(self):
        self.stop()
        self.failed.emit()
