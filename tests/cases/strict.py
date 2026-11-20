import os
from pathlib import Path
import resource
import subprocess


def check(root,work,command,require,blocked):
    selected=os.environ.get('W3_HELPER')
    if not selected:
        raise blocked('set W3_HELPER to the packaged mr-sitting executable')
    path=Path(selected).resolve()
    if not path.is_file(): raise blocked('mr-sitting is missing')
    message=b'mr-sitting could not secure its memory. No secret was read. Restart the sitting stick and try again.\n'
    marker=work/'nonsecret-input'
    marker.write_bytes(b'fixture is public and is not a draw\n')
    def lower_limit():
        resource.setrlimit(resource.RLIMIT_MEMLOCK,(131072,131072))
    with marker.open('rb',buffering=0) as stdin:
        try:
            run=command([path,'root','--network','signet','--letters','none','--from','coins'],stdin=stdin,
                        env={'LANG':'C','PATH':'/usr/bin:/bin','XDG_RUNTIME_DIR':str(work)},preexec_fn=lower_limit,timeout=3)
        except subprocess.TimeoutExpired:
            require(False,'helper accepted input before a strict lock')
        require(run.returncode==2 and run.stderr==message and run.stdout==b'' and stdin.tell()==0,
                'helper accepted input before a strict lock')
    if not os.environ.get('W3_GUEST_STRICT_RESULTS'):
        raise blocked('normal-limit guest and all four subcommands require image integration')
    raise blocked('complete-image strict runner is pending')
