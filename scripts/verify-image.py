#!/usr/bin/env python3
"""Authenticate a release image or the written image-length prefix of a drive on Linux."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

IMAGE_FAILURE = 'Image verification failed. No drive was written.'
READBACK_FAILURE = 'The written drive could not be verified. Keep the previous stick.'


def unique_fields(pairs):
    fields = {}
    for name, value in pairs:
        if name in fields:
            raise ValueError('duplicate manifest field')
        fields[name] = value
    return fields


def authenticated_manifest(args):
    with args.manifest.open('rb') as source:
        data = source.read(16385)
    if not data or len(data)>16384:
        raise ValueError('invalid manifest length')
    # Verify the very bytes subsequently parsed, including on removable storage.
    with os.fdopen(os.memfd_create('w3-release-manifest'), 'w+b') as copy:
        copy.write(data)
        copy.flush()
        copy.seek(0)
        fd = copy.fileno()
        verified = subprocess.run(
            ['minisign','-V','-q','-p',args.key,'-x',args.signature,'-m',f'/proc/self/fd/{fd}'],
            pass_fds=(fd,), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if verified.returncode:
        raise ValueError('signature did not verify')
    fields = json.loads(data.decode('utf-8'),object_pairs_hook=unique_fields)
    if not isinstance(fields,dict) or set(fields) != {'role','version','bytes','sha256'}:
        raise ValueError('unexpected fields')
    if fields['role']!=args.role or fields['version']!=args.version:
        raise ValueError('role or release mismatch')
    if type(fields['bytes']) is not int or fields['bytes']<=0:
        raise ValueError('invalid byte count')
    if not isinstance(fields['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',fields['sha256']):
        raise ValueError('invalid digest')
    return fields


def check_content(path, length, expected, readback):
    digest = hashlib.sha256()
    with path.open('rb',buffering=0) as stream:
        remaining = length
        while remaining:
            block = stream.read(min(remaining,1024*1024))
            if not block:
                return False
            remaining -= len(block)
            digest.update(block)
        if not readback and stream.read(1):
            return False
    return digest.hexdigest() == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('image','readback'))
    parser.add_argument('--key',type=Path,required=True)
    parser.add_argument('--signature',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--role',choices=('sitting-stick','node'),required=True)
    parser.add_argument('--version',required=True)
    parser.add_argument('path',type=Path)
    args = parser.parse_args()
    readback = args.operation=='readback'
    try:
        fields = authenticated_manifest(args)
        if check_content(args.path,fields['bytes'],fields['sha256'],readback):
            return 0
    except (OSError, ValueError, RecursionError):
        pass
    print(READBACK_FAILURE if readback else IMAGE_FAILURE,file=sys.stderr)
    return 1


if __name__=='__main__':
    sys.exit(main())
