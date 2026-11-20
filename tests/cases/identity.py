import os
from pathlib import Path


def check(root,work,command,require,blocked,component):
    source=os.environ.get('W3_IDENTITY_ROOT')
    if not source: raise blocked('supply an observation root of the booted image')
    r=Path(source)
    ids=[s for s in (r/'etc/os-release').read_text().splitlines() if s.startswith('ID=')]
    release=(r/'proc/sys/kernel/osrelease').read_text().strip()
    require(ids in (['ID=mr-sitting-stick'],['ID="mr-sitting-stick"']) and release.endswith('-mr-sitting'),'wrong kernel identity accepted')
    require(sorted(f.name for f in (r/'sys/class/net').iterdir())==['lo'],'wrong kernel identity accepted')
    if component: return
    raise blocked('invoke the packaged helper across individual identity and network-property controls')
