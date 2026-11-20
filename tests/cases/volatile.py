from pathlib import Path
import os


def check(root,work,command,require,blocked,component):
    control=os.environ.get('W3_MOUNTINFO')
    if not control:
        raise blocked('booted image mount inventory is required')
    mount_text=Path(control).read_text()
    lines=mount_text.splitlines()
    roots=[l for l in lines if len(l.split())>5 and l.split()[4]=='/']
    require(len(roots)==1 and ' - squashfs ' in roots[0] and 'ro' in roots[0].split()[5].split(','),'persistent storage was used')
    for path in ('/run','/home','/tmp'):
        require(any(l.split()[4]==path and ' - tmpfs ' in l for l in lines),'persistent storage was used')
    if not os.environ.get('W3_COLD_BOOT_RESULTS'):
        raise blocked('cold boot, internal disk and preinserted USB byte comparisons are required')
    raise blocked('complete-image cold boot runner is pending')
