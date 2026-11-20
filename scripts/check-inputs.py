#!/usr/bin/env python3
"""Check an unprivileged, offline bundle against an independently authenticated manifest digest."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import sys

ROOT=Path(__file__).resolve().parents[1]
DIGEST=re.compile(r'[0-9a-f]{64}')
FIELDS={'name','revision','source','source_sha256','artifact','artifact_sha256','license','recipe_sha256','lockfile_sha256','policy'}


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def unique(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError('duplicate field')
        out[k]=v
    return out


def bound_file(directory,name,digest):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*',name):
        raise ValueError('invalid filename')
    p=directory/name
    if not stat.S_ISREG(p.lstat().st_mode) or checksum(p)!=digest:
        raise ValueError('input digest mismatch')


def verify(directory,manifest,manifest_digest,role,required):
    data=manifest.read_bytes()
    if not DIGEST.fullmatch(manifest_digest) or hashlib.sha256(data).hexdigest()!=manifest_digest:
        raise ValueError('unbound manifest')
    obj=json.loads(data.decode('utf-8'),object_pairs_hook=unique)
    if not isinstance(obj,dict) or set(obj)!={'role','applications'} or obj['role']!=role or not isinstance(obj['applications'],list):
        raise ValueError('invalid role manifest')
    seen=set()
    for row in obj['applications']:
        if not isinstance(row,dict) or set(row)!=FIELDS or not all(isinstance(v,str) for v in row.values()):
            raise ValueError('invalid application record')
        name=row['name']
        if name not in required or name in seen:
            raise ValueError('unexpected application')
        if not re.fullmatch(r'[0-9a-f]{40}',row['revision']) or not row['license'].strip():
            raise ValueError('missing provenance')
        if not all(DIGEST.fullmatch(row[k]) for k in ('recipe_sha256','lockfile_sha256','source_sha256','artifact_sha256')):
            raise ValueError('invalid digest')
        if row['policy']!=('strict' if name=='mr-sitting' else 'standard'):
            raise ValueError('wrong memory policy')
        for key in ('source','artifact'):
            bound_file(directory,row[key],row[key+'_sha256'])
        seen.add(name)
    if seen!=required:
        raise ValueError('missing application')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=('sitting-stick','node'))
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--trusted-digest',required=True,help='manifest SHA-256 from the independently authenticated build lock')
    args=parser.parse_args()
    role=json.loads((ROOT/'image/profiles'/(args.role+'.json')).read_text())
    try:
        verify(args.bundle,args.bundle/'inputs.json',args.trusted_digest,args.role,set(role['applications']))
    except (ValueError,OSError,RecursionError):
        print('A required image input is missing or failed verification.',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    sys.exit(main())
