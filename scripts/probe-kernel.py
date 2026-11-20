#!/usr/bin/env python3
"""Boot a Linux kernel with two isolated virtual NICs and exercise a real memory lock."""
import argparse
import gzip
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
REQUIRED='NET UNIX SYSFS DEVTMPFS TMPFS USB USB_XHCI_HCD USB_ACM USB_HID USB_STORAGE SCSI BLK_DEV_SD VFAT_FS IKCONFIG IKCONFIG_PROC'.split()
FORBIDDEN='NETDEVICES INET IPV6 WIRELESS BT USB_NET_CDCETHER USB_NET_RNDIS_HOST DVB_CORE MODULES SWAP HIBERNATION COREDUMP'.split()


def run(args):
    cfg=set(args.config.read_text().splitlines())
    if any('CONFIG_'+k+'=y' not in cfg for k in REQUIRED):
        return False
    if any('CONFIG_'+k+'='+v in cfg for k in FORBIDDEN for v in ('y','m')) or any(k.startswith('CONFIG_') and k.endswith('=m') for k in cfg):
        return False
    with tempfile.TemporaryDirectory(dir=args.work) as tmp:
        work=Path(tmp)
        for name in ('proc','sys','dev'):
            (work/name).mkdir()
        env=dict(os.environ,TMPDIR=str(work),XDG_CACHE_HOME=str(work),XDG_RUNTIME_DIR=str(work))
        subprocess.run(['cc','-O2','-Wall','-Wextra','-Werror','-static',str(ROOT/'tests/guest/kernel-init.c'),'-o','init'],cwd=work,env=env,check=True)
        cpio=subprocess.run(['cpio','--quiet','-o','-H','newc','--owner','0:0'],input=b'proc\nsys\ndev\ninit\n',stdout=subprocess.PIPE,cwd=work,env=env,check=True)
        initrd=work/'probe.gz'
        initrd.write_bytes(gzip.compress(cpio.stdout,mtime=0))
        acceleration='kvm' if os.access('/dev/kvm',os.R_OK|os.W_OK) else 'tcg'
        cmd=['qemu-system-x86_64','-no-user-config','-nodefaults','-machine','q35,accel='+acceleration,'-m','512','-smp','2','-no-reboot','-display','none','-monitor','none','-serial','stdio','-kernel',str(args.kernel.resolve()),'-initrd',str(initrd),'-append','console=ttyS0 rdinit=/init panic=-1 loglevel=3','-netdev','hubport,id=a,hubid=1','-device','e1000,netdev=a','-netdev','hubport,id=b,hubid=1','-device','virtio-net-pci,netdev=b']
        vm=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=work,env=env,timeout=50,check=False)
        observations=[s for s in vm.stdout.decode(errors='replace').splitlines() if s.startswith('W3-PROBE')]
        for line in observations: print(line)
        return vm.returncode == 0 and bool(observations) and observations[-1]=='W3-PROBE PASS'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args()
    args.work=args.work.resolve()
    try:
        args.work.mkdir(mode=0o700,parents=True,exist_ok=True)
        return 0 if run(args) else 1
    except (OSError,subprocess.SubprocessError) as err:
        print(str(err),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
