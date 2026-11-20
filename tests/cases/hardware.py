import json
import os
from pathlib import Path


def check(root,work,command,require,blocked,component):
    records=os.environ.get('W3_HARDWARE_RECORDS')
    if not records: raise blocked('two physical qualification records are required')
    matrix=json.loads(Path(records).read_bytes())
    variants=set()
    measurements={'uefi_boot','gui','usb_hid','wallet_terminal','return_to_wallet','read_only_import','public_export','cdc_acm','bootsel_info','ethernet_rejected'}
    for run in matrix:
        require(run.get('kind')=='physical' and all(run.get(key) for key in ('model','firmware','boot_policy','port','image_sha256','operator_record')),'physical support claim lacks a matching run')
        require(all(run.get('observed',{}).get(k) is True for k in measurements),'physical support claim lacks a matching run')
        variants.add(run.get('processor_vendor'))
    require({'Intel','AMD'}<=variants,'physical support claim lacks a matching run')
