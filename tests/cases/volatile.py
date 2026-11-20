import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
from uuid import UUID


MOUNTS = {'/': ['squashfs', 'ro'], '/home': ['tmpfs', 'rw'], '/run': ['tmpfs', 'rw'],
          '/tmp': ['tmpfs', 'rw'], '/var': ['overlay', 'rw']}
MARKERS = {'/home/live/Sitting', '/run/user/1000', '/tmp', '/var/log'}
FAILURE = 'persistent storage was used'


def create_disk(work, name, filesystems):
    # Format regular files, then embed them in real partitions without a host loop device.
    start = 2048
    partitions = []
    for label, kind in filesystems:
        size = (8 if kind == 'swap' else 64) << 20
        path = work / (label + '.fs')
        with path.open('xb') as file:
            file.truncate(size)
        if kind == 'swap':
            path.chmod(0o600)
            command = ['mkswap', '-L', label, str(path)]
        else:
            command = ['mkfs.fat', '--invariant', '-F', '32', '-n', label, str(path)]
        subprocess.run(command, check=True, capture_output=True)
        partitions.append((start, size // 512, '82' if kind == 'swap' else 'c', path))
        start += size // 512
    disk = work / name
    with disk.open('xb') as file:
        file.truncate((start + 2048) * 512)
    table = 'label: dos\n' + ''.join(f'{offset},{length},{kind}\n'
                                      for offset, length, kind, _ in partitions)
    subprocess.run(['sfdisk', '--no-reread', '--no-tell-kernel', str(disk)],
                   input=table, text=True, check=True, capture_output=True)
    with disk.open('r+b') as out:
        for offset, _, _, payload in partitions:
            out.seek(offset * 512)
            with payload.open('rb') as source:
                shutil.copyfileobj(source, out)
    return disk


def acceptable(record):
    parts = record['partitions']
    types = {label: entry['type'] for label, entry in parts.items()}
    if types != {'W3TRANSFER': 'vfat', 'W3INTERNAL': 'vfat', 'W3SWAP': 'swap'}:
        return False
    if parts['W3INTERNAL']['disk'] != parts['W3SWAP']['disk']:
        return False
    if parts['W3TRANSFER']['disk'] == parts['W3INTERNAL']['disk']:
        return False
    mounted = record['block_mounts']
    return (len(mounted) == 1 and mounted[0][:2] == ['/', '/dev/loop0'] and
            mounted[0][2] not in {p['dev'] for p in parts.values()} and
            record['mounts'] == MOUNTS and record['swap_excluded'] is True and
            record['active_swap'] == [] and record['private_runtime'] == [1000, 0o700, True] and
            record['previous'] == [] and set(record['written']) == MARKERS)


def check(root, work, command, require, blocked, component):
    if component or os.environ.get('W3_MOUNTINFO'):
        mountinfo = os.environ.get('W3_MOUNTINFO')
        if not mountinfo:
            raise blocked('booted image mount inventory is required')
        entries = {}
        for line in Path(mountinfo).read_text().splitlines():
            left, right = line.split(' - ', 1)
            path, flags = left.split()[4:6]
            entries[path] = [right.split()[0], flags.split(',')[0]]
        require(all(entries.get(p) == expected for p, expected in MOUNTS.items()), FAILURE)
        if component:
            return
    image = os.environ.get('W3_COLD_IMAGE')
    if not image:
        raise blocked('supply the sitting image with the disposable cold-boot observer')
    vm = runpy.run_path(str(root / 'tests/boot-development-image.py'))
    firmware = Path(os.environ.get('W3_OVMF_CODE', '/usr/share/edk2/x64/OVMF_CODE.4m.fd'))
    nvram = Path(os.environ.get('W3_OVMF_VARS', '/usr/share/edk2/x64/OVMF_VARS.4m.fd'))
    evidence = os.environ.get('W3_COLD_EVIDENCE')
    if evidence:
        work = Path(evidence).resolve()
        work.mkdir(mode=0o700, exist_ok=False)
    shutil.copyfile(nvram, work / 'vars.fd')
    disks = [create_disk(work, 'internal.img', [('W3INTERNAL', 'vfat'), ('W3SWAP', 'swap')]),
             create_disk(work, 'transfer.img', [('W3TRANSFER', 'vfat')])]
    before = [vm['digest'](disk) for disk in disks]
    records = []
    for index in range(2):
        console = f'boot-{index + 1}.log'
        vm['boot'](Path(image).resolve(strict=True), firmware, work,
                   lambda log: any(l.startswith('W3-STORAGE {') and l.endswith('}')
                                   for l in log.splitlines()), console)
        lines = (work / console).read_text(errors='replace').splitlines()
        require('W3-BOOT identity VERSION_CODENAME=noble ID=mr-sitting-stick' in lines, FAILURE)
        observed = [json.loads(l.removeprefix('W3-STORAGE ')) for l in lines if l.startswith('W3-STORAGE ')]
        require(len(observed) == 1 and acceptable(observed[0]), FAILURE)
        records.append(observed[0])
        require([vm['digest'](disk) for disk in disks] == before, FAILURE)
    require(UUID(records[0]['boot']) != UUID(records[1]['boot']), FAILURE)
    (work / 'result.json').write_text(json.dumps({'sha256_each_boot': before, 'boots': records}, indent=2) + '\n')
