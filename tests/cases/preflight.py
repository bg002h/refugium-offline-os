import importlib.util
import os
import sys
import gzip


def check(root, work, command, require, blocked, component):
    target=root/'image/stick/preflight.py'
    # Control: a stock Debian session can start a normal program with no preflight at all.
    baseline=command([sys.executable,'-B','-c','print("wallet entry reached")'])
    if not target.is_file():
        require(b'wallet entry reached' not in baseline.stdout,'unsafe boot reached the wallet')
    spec=importlib.util.spec_from_file_location('w3_preflight',target)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for d in ('proc/sys/kernel','sys/class/net/lo','etc/refugium','usr/lib/refugium','usr/bin','run/user/1000','home/live','tmp'):
        (work/d).mkdir(parents=True,exist_ok=True)
    (work/'run/user/1000').chmod(0o700)
    config=''.join('CONFIG_'+k+'=y\n' for k in mod.REQUIRED)
    config_file=work/'proc/config.gz'
    config_file.write_bytes(gzip.compress(config.encode()))
    (work/'etc/os-release').write_text('ID=mr-sitting-stick\n')
    (work/'proc/sys/kernel/osrelease').write_text('6.12.118-mr-sitting\n')
    (work/'proc/self').mkdir()
    mounts='''1 0 0:1 / / ro - squashfs /dev/loop0 ro
2 1 0:2 / /proc rw - proc proc rw
3 1 0:3 / /sys rw - sysfs sysfs rw
4 1 0:4 / /run rw - tmpfs tmpfs rw
5 1 0:5 / /home rw - tmpfs tmpfs rw
6 1 0:6 / /tmp rw - tmpfs tmpfs rw
'''
    m=work/'proc/self/mountinfo';m.write_text(mounts)
    binary=work/'usr/bin/mr-sitting'; binary.write_bytes(b'test strict input')
    import hashlib
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    (work/'usr/lib/refugium/strict-helper.sha256').write_text(digest+'\n')
    def seen(limits=(67108864,67108864)):
        return mod.check(work, '/run/user/1000',os.getuid(),limits)
    require(seen() is None,'valid boot refused')
    for key in ('SWAP','NETDEVICES','MODULES','HIBERNATION'):
        config_file.write_bytes(gzip.compress((config+'CONFIG_'+key+'=y\n').encode()))
        require(seen()==mod.KERNEL,'unsafe boot reached the wallet')
    config_file.unlink(); require(seen()==mod.KERNEL,'unsafe boot reached the wallet')
    config_file.write_bytes(gzip.compress(config.encode()))
    net=work/'sys/class/net/extra';net.mkdir()
    require(seen()==mod.NETWORK,'unsafe boot reached the wallet');net.rmdir()
    m.write_text(mounts+'7 1 8:1 / /mnt/other ro - vfat /dev/sda1 ro\n')
    require(seen()==mod.STORAGE,'unsafe boot reached the wallet');m.write_text(mounts)
    (work/'proc/swaps').write_text('Filename Type Size Used Priority\n/zram partition 10 0 5\n')
    require(seen()==mod.STORAGE,'unsafe boot reached the wallet');(work/'proc/swaps').unlink()
    require(seen((8388608,8388608))==mod.MEMORY,'unsafe boot reached the wallet')
    binary.write_bytes(b'ordinary helper')
    require(seen()==mod.MEMORY,'unsafe boot reached the wallet')

    if not component:
        raise blocked('booted GUI success and preflight refusal paths are required')
