import os
from pathlib import Path


def check(root,work,command,require,blocked,component):
    binary=os.environ.get('W3_PUBLIC_CODEC')
    invalid=b'refugium-plan 1\nnetwork signet\nplan-id 01234567\n\nprivate fixture data\n'
    if not binary:
        if os.environ.get('W3_NEGATIVE_HEADER_ONLY')=='1':
            require(not invalid.startswith(b'refugium-plan 1\n'),'unsafe import or source changed')
        raise blocked('set W3_PUBLIC_CODEC to the pinned codec utility')
    r=command([binary,'plan','01234567'],input=invalid)
    require(r.returncode==2 and not r.stdout,'unsafe import or source changed')
    good=(root/'tests/fixtures/public-plan.txt').read_bytes()
    r=command([binary,'plan','0000000c'],input=good)
    require(r.returncode==0 and r.stdout==b'plan 0000000c cold\n','unsafe import or source changed')
    require(command([binary,'plan','01234567'],input=good).returncode==2,'unsafe import or source changed')
    if not component: raise blocked('read-only FAT32 and graphical import on the image are required')
