"""Identify removable transfer partitions and bind a selection to its disk generation."""
import json
from pathlib import Path
import re
import subprocess

BOOT_UUID='/sys/firmware/efi/efivars/LoaderDevicePartUUID-4a67b082-0a4c-41cf-b6c7-440b29bb8c4f'


def boot_partition_id():
    raw=Path(BOOT_UUID).read_bytes()
    value=raw[4:].decode('utf-16-le').rstrip('\x00').lower()
    if not re.fullmatch(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}',value):
        raise ValueError('unrecognized boot partition')
    return value


def hardware_identity(row):
    major_minor=row['maj:min']
    if not re.fullmatch(r'\d+:\d+',major_minor):
        raise ValueError('invalid device number')
    part=(Path('/sys/dev/block')/major_minor).resolve(strict=True)
    if not (part/'partition').is_file():
        return None
    seq=int((part.parent/'diskseq').read_text())
    for parent in part.parents:
        if (parent/'idVendor').is_file() and (parent/'idProduct').is_file():
            port=parent.name
            if not re.fullmatch(r'\d+-\d+(?:\.\d+)*',port):
                return None
            return port,seq,(parent/'idVendor').read_text().strip(),(parent/'idProduct').read_text().strip()
    return None


def candidates(rows,boot_id,hardware):
    boot=[r for r in rows if r.get('partuuid') and r['partuuid'].lower()==boot_id]
    if len(boot)!=1 or not boot[0].get('pkname'):
        return []
    result=[]
    for row in rows:
        if row.get('type')!='part' or not row.get('pkname') or row['pkname']==boot[0]['pkname']:
            continue
        identity=hardware(row)
        if not identity:
            continue
        port,seq,vendor,product=identity
        if (vendor,product)==('2e8a','000f'):
            continue
        token=f"{row['maj:min']}@{seq}/{port}"
        result.append(dict(row,token=token,port=port,diskseq=seq))
    return result


def select(rows,token):
    found=[r for r in rows if r['token']==token]
    return found[0] if len(found)==1 else None


def inventory():
    args=['/usr/bin/lsblk','--json','--list','--bytes','--paths','--output',
          'NAME,MAJ:MIN,TYPE,PKNAME,PARTUUID,SIZE,FSTYPE,FSVER']
    data=json.loads(subprocess.check_output(args,stderr=subprocess.DEVNULL))
    return candidates(data['blockdevices'],boot_partition_id(),hardware_identity)
