"""Collect storage evidence inside a disposable, instrumented sitting image."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import time


def attached_partitions():
    rows = {}
    for device in Path('/sys/class/block').iterdir():
        if not (device / 'partition').exists():
            continue
        result = subprocess.run(['blkid', '-p', '-o', 'export', '/dev/' + device.name],
                                text=True, capture_output=True)
        fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        label = fields.get('LABEL')
        if label in ('W3INTERNAL', 'W3TRANSFER', 'W3SWAP'):
            if label in rows:
                raise RuntimeError('duplicate test partition')
            rows[label] = {'type': fields.get('TYPE'), 'dev': (device / 'dev').read_text().strip(),
                           'disk': device.resolve().parent.name}
    return rows


def observe():
    deadline = time.monotonic() + 25
    while True:
        parts = attached_partitions()
        if len(parts) == 3 or time.monotonic() >= deadline:
            break
        time.sleep(0.25)
    record = {'partitions': parts, 'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    with gzip.open('/proc/config.gz', 'rt') as config:
        record['swap_excluded'] = '# CONFIG_SWAP is not set' in config.read().splitlines()
    swaps = Path('/proc/swaps')
    record['active_swap'] = swaps.read_text().splitlines()[1:] if swaps.exists() else []
    mounts = {}
    block_mounts = []
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        left, right = line.split(' - ', 1)
        dev, _, path, flags = left.split()[2:6]
        fs, source, _ = right.split(None, 2)
        if path in ('/', '/home', '/run', '/tmp', '/var'):
            mounts[path] = [fs, flags.split(',')[0]]
        if Path('/sys/dev/block', dev).exists():
            block_mounts.append([path, source, dev])
    record['mounts'] = mounts
    record['block_mounts'] = block_mounts
    runtime = Path('/run/user/1000')
    st = runtime.stat()
    record['private_runtime'] = [st.st_uid, st.st_mode & 0o777, st.st_dev == Path('/run').stat().st_dev]
    previous = []
    written = []
    for directory in ('/home/live/Sitting', '/run/user/1000', '/tmp', '/var/log'):
        marker = Path(directory, '.w3-cold-boot-public-fixture')
        if marker.exists():
            previous.append(directory)
            continue
        with marker.open('xb') as file:
            file.write(record['boot'].encode())
            file.flush()
            os.fsync(file.fileno())
        written.append(directory)
    os.sync()
    record.update(previous=previous, written=written)
    return record


if __name__ == '__main__':
    with open('/dev/ttyS0', 'w') as serial:
        print('W3-STORAGE', json.dumps(observe(), sort_keys=True), file=serial, flush=True)
