# SPDX-License-Identifier: GPL-3.0-only
"""Offline verification of GitHub download trust, limits, and cancellation."""
import hashlib
import os
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtNetwork, QtWidgets

from fisher.project import PROJECT_URL
from fisher.updater import HTTP_STATUS, InstallerDownload, release_asset, trusted_redirect

PAYLOAD = b"test data for Windows update verification"
VERSION = "9.2.1"
ASSET_NAME = f"tt-tool-{VERSION}-windows-x64-setup.exe"
ASSET_URL = f"{PROJECT_URL}/releases/download/v{VERSION}/{ASSET_NAME}"
DOWNLOAD_URL = "https://release-assets.githubusercontent.com/releases/tt-tool-setup.exe?signature=fixture"


def release_with_asset(**overrides):
    item = {"name": ASSET_NAME, "state": "uploaded", "browser_download_url": ASSET_URL,
            "size": len(PAYLOAD), "digest": "sha256:" + hashlib.sha256(PAYLOAD).hexdigest()}
    item.update(overrides)
    return {"tag_name": f"v{VERSION}", "assets": [item]}


class Reply(QtCore.QObject):
    readyRead = QtCore.Signal()
    finished = QtCore.Signal()

    def __init__(self, status, url, target=""):
        super().__init__()
        self.status = status
        self.source = QtCore.QUrl(url)
        self.target = QtCore.QUrl(target)
        self.buffer = b""
        self.aborted = False

    def url(self):
        return self.source

    def attribute(self, name):
        return self.status if name == HTTP_STATUS else self.target

    def setReadBufferSize(self, size):
        self.limit = size

    def bytesAvailable(self):
        return len(self.buffer)

    def read(self, size):
        chunk, self.buffer = self.buffer[:size], self.buffer[size:]
        return chunk

    def error(self):
        return QtNetwork.QNetworkReply.NetworkError.NoError

    def feed(self, content):
        self.buffer += content
        self.readyRead.emit()

    def abort(self):
        self.aborted = True
        self.finished.emit()


class UpdaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def job(self, *replies):
        asset = release_asset(release_with_asset(), VERSION)
        network = Mock()
        network.get.side_effect = replies
        job = InstallerDownload(network, asset)
        self.addCleanup(job.file.cleanup)
        self.addCleanup(job.stop)
        return job

    def test_asset_must_match_release_and_include_trusted_digest(self):
        self.assertIsNotNone(release_asset(release_with_asset(), VERSION))
        for override in ({"digest": None}, {"size": True}, {"size": 10**10},
                         {"state": "new"}, {"browser_download_url": ASSET_URL.replace("github.com", "example.com")},
                         {"name": "renamed.exe"}):
            with self.subTest(override=override):
                self.assertIsNone(release_asset(release_with_asset(**override), VERSION))

    def test_trusted_redirect_rejects_scheme_suffix_and_userinfo_spoofing(self):
        self.assertTrue(trusted_redirect(DOWNLOAD_URL))
        for url in (DOWNLOAD_URL.replace("https", "http"),
                    DOWNLOAD_URL.replace(".com/", ".com.example.org/"),
                    DOWNLOAD_URL.replace(".com/", ".com:8443/"),
                    DOWNLOAD_URL.replace(".com/", ".com@example.org/")):
            with self.subTest(url=url):
                self.assertFalse(trusted_redirect(url))

    def test_redirect_and_chunked_download_verify_original_bytes(self):
        redirect = Reply(302, ASSET_URL, DOWNLOAD_URL)
        response = Reply(200, DOWNLOAD_URL)
        job = self.job(redirect, response)
        verified = Mock()
        job.verified.connect(verified)
        job.start()
        redirect.finished.emit()
        self.assertEqual(job.network.get.call_args.args[0].url().toString(), DOWNLOAD_URL)
        response.feed(PAYLOAD[:10])
        response.feed(PAYLOAD[10:])
        response.finished.emit()
        verified.assert_called_once_with()
        self.assertEqual(job.file.installer.read_bytes(), PAYLOAD)
        self.assertFalse(job.file.partial.exists())

    def test_untrusted_redirect_never_requests_target(self):
        reply = Reply(302, ASSET_URL, "https://example.org/installer.exe")
        job = self.job(reply)
        failed = Mock()
        job.failed.connect(failed)
        job.start()
        reply.finished.emit()
        failed.assert_called_once_with()
        job.network.get.assert_called_once()
        self.assertFalse(job.file.installer.exists())

    def test_truncation_wrong_digest_and_overflow_never_create_installer(self):
        for payload in (PAYLOAD[:10], b"0" * len(PAYLOAD), PAYLOAD + b"1"):
            with self.subTest(length=len(payload)):
                reply = Reply(200, ASSET_URL)
                job = self.job(reply)
                failed = Mock()
                job.failed.connect(failed)
                job.start()
                reply.feed(payload)
                reply.finished.emit()
                failed.assert_called_once_with()
                self.assertFalse(job.file.installer.exists())

    def test_abort_ignores_late_signals(self):
        reply = Reply(200, ASSET_URL)
        job = self.job(reply)
        finished = Mock()
        job.verified.connect(finished)
        job.failed.connect(finished)
        job.start()
        reply.feed(PAYLOAD[:10])
        job.stop()
        reply.feed(PAYLOAD[10:])
        reply.finished.emit()
        self.assertTrue(reply.aborted)
        self.assertFalse(job.deadline.isActive())
        self.assertFalse(job.file.installer.exists())
        finished.assert_not_called()
