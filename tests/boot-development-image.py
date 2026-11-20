#!/usr/bin/env python3
"""Boot an instrumented development image from emulated USB and check its serial observations."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def check_boot(role, output):
    lines = output.splitlines()
    interface_rows = [line.removeprefix('W3-BOOT interfaces ') for line in lines
                      if line.startswith('W3-BOOT interfaces ')]
    if len(interface_rows) != 1:
        return False
    interfaces = set(interface_rows[0].split(','))
    markers = ['W3-BOOT pid1 systemd', 'VERSION_CODENAME=noble', 'W3-BOOT helper_installed False',
               'W3-BOOT complete 1',
               'W3-BOOT mount / squashfs ro,', 'W3-BOOT mount /var overlay rw,']
    markers.extend(f'W3-BOOT mount {p} tmpfs rw,' for p in ('/home', '/run', '/tmp'))
    if role == 'node':
        # Both emulated PCI adapters must bind a driver on this guest.
        if not {'lo', 'enp0s3', 'enp0s4'} <= interfaces:
            return False
        markers.extend(['ID=ubuntu', 'VARIANT_ID=refugium-node', '-mr-node'])
    else:
        # This development image deliberately omits the strict helper.
        markers.extend(['ID=mr-sitting-stick', '-mr-sitting', 'W3-BOOT proc_swaps False',
                        'preflight.py', 'status=2', 'ActiveState=failed',
                        'W3-BOOT session LimitMEMLOCK=67108864',
                        'W3-BOOT session LimitMEMLOCKSoft=67108864'])
        markers.extend(f'W3-BOOT application {name} 0 ' for name in ('mr-gui', 'mr', 'me', 'picotool'))
        if interfaces != {'lo'}:
            return False
    return all(marker in output for marker in markers)


def review_observation(output):
    rows = [line.removeprefix('W3-REVIEW ') for line in output.splitlines()
            if line.startswith('W3-REVIEW ') and line.endswith('}')]
    if len(rows) == 1:
        return json.loads(rows[0])
    return None


def boot(image, firmware, work, check, console_name='console.log'):
    argv = ['qemu-system-x86_64', '-nodefaults', '-no-user-config', '-no-reboot',
            '-machine', 'q35,accel=kvm', '-cpu', 'host', '-m', '4096', '-smp', '2',
            '-display', 'none', '-monitor', 'none', '-serial', 'file:' + console_name,
            '-drive', f'if=pflash,unit=0,format=raw,readonly=on,file={firmware}',
            '-drive', 'if=pflash,unit=1,format=raw,file=vars.fd', '-device', 'virtio-vga',
            '-device', 'qemu-xhci,id=xhci', '-device', 'usb-kbd,bus=xhci.0',
            '-drive', f'if=none,id=stick,format=raw,readonly=on,file={image}',
            '-device', 'usb-storage,bus=xhci.0,drive=stick,bootindex=1',
            '-drive', 'if=virtio,format=raw,file=internal.img',
            '-drive', 'if=none,id=transfer,format=raw,file=transfer.img',
            '-device', 'usb-storage,bus=xhci.0,drive=transfer',
            '-netdev', 'hubport,id=n0,hubid=7', '-device', 'e1000,netdev=n0',
            '-netdev', 'hubport,id=n1,hubid=7', '-device', 'virtio-net-pci,netdev=n1']
    console = work / console_name
    with (work / (console_name + '.qemu')).open('x') as log:
        vm = subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline and vm.poll() is None:
                if console.exists() and check(console.read_text(errors='replace')):
                    return
                time.sleep(0.5)
            else:
                raise RuntimeError(f'expected boot observations missing; inspect {console}')
        finally:
            if vm.poll() is None:
                vm.terminate()
                try:
                    vm.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    vm.kill()
                    vm.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['sitting-stick', 'node'])
    parser.add_argument('image', type=Path)
    parser.add_argument('work', type=Path, help='a new directory for this VM and its console log')
    parser.add_argument('--firmware', type=Path, required=True, help='OVMF code image')
    parser.add_argument('--vars-template', type=Path, required=True, help='matching OVMF variable store')
    parser.add_argument('--reviewed-helper', action='store_true',
                        help='also run the public W1T control embedded in a diagnostic stick')
    args = parser.parse_args()
    if args.reviewed_helper and args.role != 'sitting-stick':
        parser.error('the reviewed helper control requires the sitting-stick role')
    image = args.image.resolve(strict=True)
    firmware = args.firmware.resolve(strict=True)
    work = args.work.resolve()
    work.mkdir(mode=0o700, parents=False, exist_ok=False)
    shutil.copyfile(args.vars_template, work / 'vars.fd')
    disks = [work / 'internal.img', work / 'transfer.img']
    for disk in disks:
        with disk.open('xb') as file:
            file.truncate(16 << 20)
    before = [digest(disk) for disk in disks]
    boot(image, firmware, work, lambda output: check_boot(args.role, output) and
         (not args.reviewed_helper or review_observation(output) is not None))
    if [digest(disk) for disk in disks] != before:
        raise SystemExit(f'FAIL {args.role}: an attached disk changed')
    if args.reviewed_helper:
        observation = review_observation((work / 'console.log').read_text(errors='replace'))
        if not (observation['uid'] == 1000 and observation['limit'] == [64 << 20, 64 << 20] and
                observation['sit_exit'] == 0 and observation['matched'] and observation['changed_plan_rejected']):
            raise SystemExit(f'FAIL reviewed helper: public signet run differs; inspect {work}')
        print(json.dumps(observation, sort_keys=True))
    print(f'PASS {args.role}: USB boot observations matched; attached disks retained their hashes')


if __name__ == '__main__':
    main()
