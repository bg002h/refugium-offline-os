#!/usr/bin/env python3
"""Render a session-libvirt domain for an unsigned signet test image."""
import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('image', type=Path, help='read-only boot disk')
parser.add_argument('chain', type=Path, help='writable SIGNET_CHAIN filesystem')
parser.add_argument('state', type=Path, help='existing private directory for firmware state and serial output')
parser.add_argument('code', type=Path, help='OVMF x86-64 CODE flash')
parser.add_argument('vars_template', type=Path, help='matching clean OVMF VARS template')
args = parser.parse_args()
for path in (args.image, args.chain, args.code, args.vars_template):
    if not path.is_file():
        parser.error(f'Missing file {path}')
if not args.state.is_dir():
    parser.error('Create the state directory first')
if args.image.samefile(args.chain):
    parser.error('Supply separate boot and chain disks')

ET.register_namespace('qemu', 'http://libvirt.org/schemas/domain/qemu/1.0')
tree = ET.parse(Path(__file__).with_name('domain.xml'))
tree.find('os/loader').text = str(args.code.resolve())
nvram = tree.find('os/nvram')
nvram.set('template', str(args.vars_template.resolve()))
nvram.text = str(args.state.resolve() / 'guest-vars.fd')
for disk in tree.findall('devices/disk'):
    path = args.chain if disk.find('readonly') is None else args.image
    disk.find('source').set('file', str(path.resolve()))
tree.find('devices/serial/source').set('path', str(args.state.resolve() / 'boot.log'))
tree.write(sys.stdout, encoding='unicode')
print()
