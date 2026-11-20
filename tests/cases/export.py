import os
from pathlib import Path


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
    fixture=os.environ.get('W3_SIGNET_HANDBACK',root/'tests/fixtures/public-handback.txt')
    handback=Path(fixture).read_bytes()
    require(command([binary,'handback','0000000c',plan],input=handback).returncode==0,'valid hand-back refused')
    bad=work/'plan';bad.write_bytes(plan.read_bytes()+b'\n')
    require(command([binary,'handback','0000000c',bad],input=handback).returncode==2,'private or unmatched file exported')
    bad.write_bytes(plan.read_bytes().replace(b'person holder\n',b'person guest\n'))
    require(command([binary,'plan','0000000c'],input=bad.read_bytes()).returncode==0,'valid plan refused')
    different=command([binary,'handback','0000000c',bad],input=handback)
    require(different.returncode==2 and different.stdout==b'','private or unmatched file exported')
    if not component: raise blocked('the output-mount isolation and durability cases require the booted image')
