#!/usr/bin/env python3
"""Build a base root filesystem in a new directory inside a dedicated Debian build VM."""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=['sitting-stick','node'])
    parser.add_argument('work',type=Path,help='fresh build directory')
    args=parser.parse_args()
    if os.geteuid()!=0 or subprocess.run(['systemd-detect-virt','--quiet','--vm']).returncode:
        parser.error('a dedicated Debian build VM is required')
    base=json.loads((ROOT/'image/base.lock.json').read_text())
    version=subprocess.check_output(['dpkg-query','-W','-f=${Version}','live-build'],text=True)
    if version!=base['live_build_version']:
        parser.error('live-build version differs from lock')
    profile=json.loads((ROOT/'image/profiles'/(args.role+'.json')).read_text())
    args.work.mkdir(exist_ok=False)
    env=dict(os.environ,LC_ALL='C',TZ='UTC',SOURCE_DATE_EPOCH=str(base['source_date_epoch']),DEBIAN_FRONTEND='noninteractive')
    opts=['lb','config','--ignore-system-defaults','--distribution',base['suite'],'--architectures',base['architecture'],
          '--binary-images','tar','--linux-packages','none','--initramfs','none','--debian-installer','none',
          '--apt-recommends','false','--apt-secure','true','--apt-indices','false','--firmware-chroot','false',
          '--firmware-binary','false','--archive-areas','main','--updates','false','--security','true',
          '--mirror-bootstrap',base['debian'],'--mirror-chroot',base['debian'],'--mirror-chroot-security',base['security'],
          '--debootstrap-options','--variant=minbase --include=ca-certificates']
    subprocess.run(opts,env=env,cwd=args.work,check=True)
    common=['systemd-sysv','udev','util-linux','python3','locales']
    packages=common+profile['packages']
    if args.role=='sitting-stick': packages+=['seatd','libpam-systemd','xkb-data','dbus','dialog']
    listing=args.work/'config/package-lists/refugium.list.chroot'
    listing.write_text('\n'.join(sorted(set(packages)))+'\n')
    for stage in ('bootstrap','chroot'):
        subprocess.run(['lb',stage],env=env,cwd=args.work,check=True)


if __name__=='__main__':
    main()
