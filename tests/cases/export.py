import os


def check(root,work,command,require,blocked,component):
    binary=os.environ.get('W3_PUBLIC_CODEC')
    fake=b'refugium-plates 1\nfixture only\n'
    name='refugium-handback-0000000c.txt'
    if not binary:
        if os.environ.get('W3_NEGATIVE_NAME_ONLY')=='1':
            require(not name.startswith('refugium-handback-'),'private or unmatched file exported')
        raise blocked('set W3_PUBLIC_CODEC to the pinned codec utility')
    plan=root/'tests/fixtures/public-plan.txt'
    r=command([binary,'handback','0000000c',plan],input=fake)
    require(r.returncode==2 and not r.stdout,'private or unmatched file exported')
    # Valid and misplaced hand-backs must come from the pinned signet sitting fixture.
    fixture=os.environ.get('W3_SIGNET_HANDBACK')
    if not fixture: raise blocked('a paired, public signet hand-back is required')
    from pathlib import Path
    handback=Path(fixture).read_bytes()
    require(command([binary,'handback','0000000c',plan],input=handback).returncode==0,'valid hand-back refused')
    bad=work/'plan';bad.write_bytes(plan.read_bytes()+b'\n')
    require(command([binary,'handback','0000000c',bad],input=handback).returncode==2,'private or unmatched file exported')
    if not component: raise blocked('the output-mount isolation and durability cases require the booted image')
