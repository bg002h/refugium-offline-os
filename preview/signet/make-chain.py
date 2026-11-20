#!/usr/bin/env python3
"""Create a new sparse 56 GiB public signet data disk, ready to sync from an archival peer."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
args = parser.parse_args()
target = args.output.absolute()
if target.exists() or target.is_symlink():
    parser.error('Choose a new output file')
with tempfile.TemporaryDirectory(prefix='.signet-', dir=target.parent) as tmp:
    work = Path(tmp)
    seed = work / 'root'
    (seed / 'signet/chainstate').mkdir(parents=True)
    disk = work / 'disk'
    with disk.open('xb') as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.truncate(56 * 1024**3)
    subprocess.run(['mke2fs', '-q', '-t', 'ext4', '-m', '0', '-L', 'SIGNET_CHAIN',
                    '-d', seed, disk], check=True)
    os.link(disk, target)
