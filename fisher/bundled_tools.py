# SPDX-License-Identifier: GPL-3.0-only
"""Keep bundled ADB in a stable per-user location for its background server."""
import hashlib
import os
import shutil
from pathlib import Path


def _digest(path):
    h=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def prepare_adb(bundle_tools, local_root):
    source=Path(bundle_tools)
    names=('adb.exe','AdbWinApi.dll','AdbWinUsbApi.dll')
    hashes={name:_digest(source/name) for name in names}
    version=hashlib.sha256(''.join(hashes.values()).encode('ascii')).hexdigest()[:20]
    destination=Path(local_root)/'SweepAssistant'/'tools'/version
    destination.mkdir(parents=True,exist_ok=True)
    for name in names:
        target=destination/name
        if target.exists() and _digest(target)==hashes[name]:continue
        temp=destination/(name+'.'+str(os.getpid())+'.tmp')
        try:
            shutil.copyfile(source/name,temp)
            if _digest(temp)!=hashes[name]:raise OSError('內附 ADB 複製驗證失敗')
            os.replace(temp,target)
        finally:
            if temp.exists():temp.unlink()
    return destination
