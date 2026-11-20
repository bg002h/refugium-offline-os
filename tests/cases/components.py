import hashlib
import json
import os
from pathlib import Path


def check(root,work,command,require,blocked,component):
    r=os.environ.get('W3_ROOT')
    lock=os.environ.get('W3_ACCEPTED_INPUTS')
    if not r or not lock: raise blocked('supply the extracted image root and independently authenticated inputs')
    source=Path(r)
    entries=json.loads(Path(lock).read_bytes())['applications']
    for e in entries:
        path=source/'usr/bin'/e['name']
        require(path.is_file(),'installed application differs from pin')
        with path.open('rb') as stream: actual=hashlib.file_digest(stream,'sha256').hexdigest()
        require(actual==e['artifact_sha256'],'installed application differs from pin')
    require({e['name'] for e in entries}=={'mr-gui','mr-sitting','mr','me','picotool'},'installed application differs from pin')
    dpkg=source/'var/lib/dpkg/status'
    require(dpkg.is_file(),'installed application differs from pin')
    packages={l.split(': ',1)[1] for l in dpkg.read_text().splitlines() if l.startswith('Package: ')}
    require(not packages & {'bitcoind','bitcoin-qt','bitcoin-satellite','blockstream-satellite','gr-dvbs2rx','leandvb','tsduck'},'installed application differs from pin')
    if not component: raise blocked('actual image execution and dynamic-library checks are required')
