#!/usr/bin/env python3
"""Assemble a Noble root filesystem for one image role in a dedicated build VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def write_role_identity(rootfs, profile):
    # Keep Ubuntu's version and codename for distro-aware applications.
    lines = (rootfs / 'usr/lib/os-release').read_text().splitlines()
    if 'ID=ubuntu' not in lines or 'VERSION_CODENAME=noble' not in lines:
        raise ValueError('base filesystem does not identify as Ubuntu Noble')
    lines = [line for line in lines if not line.startswith(('ID=', 'VARIANT_ID='))]
    lines.append('ID=' + profile['os_id'])
    if 'variant_id' in profile:
        lines.append('VARIANT_ID=' + profile['variant_id'])
    release = rootfs / 'etc/os-release'
    release.unlink(missing_ok=True)
    release.write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['sitting-stick', 'node'])
    parser.add_argument('work', type=Path, help='fresh directory for the build')
    parser.add_argument('--archive-keyring', type=Path,
                        default=Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg'))
    args = parser.parse_args()
    if os.geteuid() != 0 or subprocess.run(['systemd-detect-virt', '--quiet', '--vm']).returncode:
        parser.error('run as root in a dedicated build VM')
    base = json.loads((ROOT / 'image/base.lock.json').read_text())
    version = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', 'mmdebstrap'], text=True)
    if version != base['mmdebstrap_version']:
        parser.error('mmdebstrap version differs from lock')
    keyring = args.archive_keyring.resolve(strict=True)
    if hashlib.sha256(keyring.read_bytes()).hexdigest() != base['archive_keyring_sha256']:
        parser.error('Ubuntu archive keyring differs from lock')
    profile = json.loads((ROOT / 'image/profiles' / (args.role + '.json')).read_text())
    packages = {'ca-certificates', 'ubuntu-keyring', 'systemd-sysv', 'udev',
                'util-linux', 'python3', 'locales', *profile['packages']}
    if args.role == 'sitting-stick':
        packages.update(['seatd', 'libpam-systemd', 'xkb-data', 'dbus', 'dialog'])
    args.work.mkdir(exist_ok=False)
    sources = [f"deb {base['archive']} {pocket} main universe" for pocket in base['pockets']]
    env = dict(os.environ, LC_ALL='C', TZ='UTC', SOURCE_DATE_EPOCH=str(base['source_date_epoch']),
               DEBIAN_FRONTEND='noninteractive')
    subprocess.run([
        'mmdebstrap', '--mode=root', '--variant=minbase', '--format=directory',
        '--architectures=' + base['architecture'], '--keyring=' + str(keyring),
        '--include=' + ','.join(sorted(packages)), base['suite'], args.work / 'chroot', *sources
    ], env=env, check=True)
    write_role_identity(args.work / 'chroot', profile)
    if args.role == 'sitting-stick':
        session = args.work / 'chroot/etc/refugium'
        session.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'image/session/weston.ini', session / 'weston.ini')
        backgrounds = args.work / 'chroot/usr/share/backgrounds'
        backgrounds.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'image/session/refugium-offline.png', backgrounds / 'refugium-offline.png')
        portals = args.work / 'chroot/etc/xdg/xdg-desktop-portal'
        portals.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'image/session/refugium-portals.conf', portals / 'refugium-portals.conf')


if __name__ == '__main__':
    main()
