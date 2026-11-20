#!/usr/bin/env python3
"""Validate the immutable image and the login session before starting the holder UI."""
import gzip
import hashlib
import os
from pathlib import Path, PurePosixPath
import resource
import stat
import sys

KERNEL='This stick could not verify its offline kernel. Power off and boot a verified Refugium sitting stick.'
NETWORK='This stick could not verify that networking is disabled. Power off and boot a verified Refugium sitting stick.'
STORAGE='This stick could not verify its RAM-only session. Power off and boot a verified Refugium sitting stick.'
MEMORY='This stick could not verify its memory protection. Power off and boot a verified Refugium sitting stick.'
REQUIRED='NET UNIX SYSFS TMPFS IKCONFIG_PROC USB_ACM USB_STORAGE USB_HID'.split()
FORBIDDEN='NETDEVICES INET IPV6 WIRELESS BT MODULES MEDIA_SUPPORT DVB_CORE USB_SERIAL USB_GADGET SWAP HIBERNATION COREDUMP KEXEC KEXEC_FILE'.split()


def mount_table(file):
    mounts={}
    for line in file.read_text().splitlines():
        left,right=line.split(' - ',1)
        fields=left.split()
        filesystem,source,_=right.split(None,2)
        path=fields[4].replace('\\040',' ').replace('\\011','\t').replace('\\012','\n').replace('\\134','\\')
        if path in mounts:
            raise ValueError('stacked mounts on one mount point')
        mounts[path]=(filesystem,set(fields[5].split(',')),source,fields[2])
    return mounts


def covering(mounts, directory):
    parts=PurePosixPath(directory)
    for candidate in (parts,*parts.parents):
        if str(candidate) in mounts:
            return mounts[str(candidate)]
    raise ValueError('unmounted path')


def storage_ok(root,runtime,uid,mounts):
    # Root is a read-only squashfs. Writable home, temporary and runtime are separate tmpfs mounts.
    fs,opts,root_source,_=mounts['/']
    if fs!='squashfs' or 'ro' not in opts or not root_source.startswith('/dev/loop'):
        return False
    if mounts['/proc'][0]!='proc' or mounts['/sys'][0]!='sysfs':
        return False
    if not runtime or not PurePosixPath(runtime).is_absolute() or '..' in PurePosixPath(runtime).parts:
        return False
    statbuf=(root/runtime.lstrip('/')).stat()
    if statbuf.st_uid!=uid or not stat.S_ISDIR(statbuf.st_mode) or stat.S_IMODE(statbuf.st_mode)!=0o700:
        return False
    for directory in ('/home','/tmp','/run',runtime):
        if covering(mounts,directory)[0]!='tmpfs':
            return False
    for path,(fs,opts,source,dev) in mounts.items():
        if path!='/' and (source.startswith('/dev/') or dev.split(':')[0]!='0') and fs not in {'devtmpfs','devpts'}:
            return False
    try:
        swaps=(root/'proc/swaps').read_text().splitlines()
    except FileNotFoundError:
        # procfs and the resolved SWAP=n were checked independently.
        return True
    return len(swaps)==1 and swaps[0].split()==['Filename','Type','Size','Used','Priority']


def check(root,runtime,uid,limits):
    stage=KERNEL
    try:
        mounts=mount_table(root/'proc/self/mountinfo')
        if mounts['/proc'][0]!='proc' or mounts['/sys'][0]!='sysfs':
            return KERNEL
        ids=[l for l in (root/'etc/os-release').read_text().splitlines() if l.startswith('ID=')]
        if ids not in (['ID=mr-sitting-stick'],['ID="mr-sitting-stick"']):
            return KERNEL
        if not (root/'proc/sys/kernel/osrelease').read_text().strip().endswith('-mr-sitting'):
            return KERNEL
        with gzip.open(root/'proc/config.gz','rt') as src:
            config=set(src.read().splitlines())
        if any(f'CONFIG_{key}=y' not in config for key in REQUIRED):
            return KERNEL
        if any(f'CONFIG_{key}={value}' in config for key in FORBIDDEN for value in ('y','m')):
            return KERNEL
        stage=NETWORK
        if sorted(p.name for p in (root/'sys/class/net').iterdir())!=['lo']:
            return NETWORK
        stage=STORAGE
        if not storage_ok(root,runtime,uid,mounts):
            return STORAGE
        stage=MEMORY
        if limits!=(67108864,67108864):
            return MEMORY
        expected=(root/'usr/lib/refugium/strict-helper.sha256').read_text().strip()
        with (root/'usr/bin/mr-sitting').open('rb') as binary:
            if hashlib.file_digest(binary,'sha256').hexdigest()!=expected:
                return MEMORY
    except (OSError,EOFError,ValueError,KeyError,IndexError):
        return stage
    return None


def main():
    message=check(Path('/'),os.environ.get('XDG_RUNTIME_DIR',''),os.getuid(),resource.getrlimit(resource.RLIMIT_MEMLOCK))
    if message:
        print(message,file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    sys.exit(main())
