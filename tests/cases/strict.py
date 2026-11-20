import os
from pathlib import Path
import resource
import subprocess
import json


def check(root,work,command,require,blocked,component):
    selected=os.environ.get('W3_HELPER')
    if not selected:
        raise blocked('set W3_HELPER to the packaged mr-sitting executable')
    path=Path(selected).resolve()
    if not path.is_file(): raise blocked('mr-sitting is missing')
    message=b'mr-sitting could not secure its memory. No secret was read. Restart the sitting stick and try again.\n'
    marker=work/'nonsecret-input'
    marker.write_bytes(b'public-invalid-fixture\n')
    def lower_limit():
        resource.setrlimit(resource.RLIMIT_MEMLOCK,(131072,131072))
    plan=root/'tests/fixtures/public-plan.txt'
    handback=root/'tests/fixtures/public-handback.txt'
    entries={
        'sit': ['--plan',plan,'--hand-back',work/'new-handback.txt'],
        'verify': ['--plan',plan,'--hand-back',handback,'--key','C'],
        'root': ['--network','signet','--letters','none','--from','coins'],
        'child': ['--network','signet','--letters','B'],
    }
    records={}
    for verb, args in entries.items():
        runtime=work/verb
        runtime.mkdir(mode=0o700)
        with marker.open('rb',buffering=0) as stdin:
            try:
                run=command([path,verb,*args],stdin=stdin,env={'XDG_RUNTIME_DIR':str(runtime)},
                            preexec_fn=lower_limit,timeout=10)
                records[verb]={'exit':run.returncode,'bytes_read':stdin.tell(),
                               'strict_refusal':run.stderr==message and run.stdout==b'',
                               'lock_warning':b'lock its memory' in run.stderr}
            except subprocess.TimeoutExpired:
                records[verb]={'exit':None,'bytes_read':stdin.tell(),'strict_refusal':False}
    if location:=os.environ.get('W3_STRICT_OBSERVATIONS'):
        with Path(location).open('x') as out:
            json.dump(records,out,indent=2)
            out.write('\n')
    require(all(r['exit']==2 and r['bytes_read']==0 and r['strict_refusal'] for r in records.values()),
            'helper accepted input before a strict lock')
    if component: return
    if not os.environ.get('W3_GUEST_STRICT_RESULTS'):
        raise blocked('normal-limit guest and all four subcommands require image integration')
    raise blocked('complete-image strict runner is pending')
