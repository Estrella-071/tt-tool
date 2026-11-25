# SPDX-License-Identifier: GPL-3.0-only
"""Local, device-specific correction learned from observed marker stops."""
import hashlib
import json
import math
import os
import statistics
from pathlib import Path


def _path(serial):
    root=os.environ.get('SWEEP_PROFILE_DIR') or str(Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'SweepAssistant')
    ident=hashlib.sha256(serial.encode('utf-8')).hexdigest()[:20]
    return Path(root) / (ident+'-v2.json')


def load_biases(serial):
    try:
        data=json.loads(_path(serial).read_text(encoding='utf-8'))
        samples=data.get('biases',[])
        if not isinstance(samples,list):return []
        return [float(x) for x in samples if isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and -.15<=x<=.15][-12:]
    except (OSError,ValueError,TypeError,AttributeError):return []


def adjusted_delay(serial, panel_delay, min_delay=.06):
    samples=load_biases(serial)
    return max(min_delay,min(.8,panel_delay-statistics.median(samples[-3:]))) if samples else panel_delay


def remember(serial, panel_delay, actual_delay):
    bias=panel_delay-actual_delay
    if not math.isfinite(bias) or not -.15<=bias<=.15:return False
    path=_path(serial);samples=(load_biases(serial)+[bias])[-12:]
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps({'biases':samples}),encoding='utf-8')
        os.replace(temp,path)
        return True
    except OSError:return False
