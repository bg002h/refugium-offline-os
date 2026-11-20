import os
from pathlib import Path


def check(root,work,command,require,blocked,component):
    # The same function can be run inside the booted image while the public fixture is on screen.
    selection=os.environ.get('W3_SESSION_PIDS')
    if not selection:
        raise blocked('supply the observed GUI, terminal, launched helper and direct helper PIDs in the image')
    pids=selection.split(',')
    if len(pids)!=4 or not all(x.isdigit() for x in pids):
        raise blocked('four live PIDs are required')
    def values(pid):
        process=Path('/proc')/pid
        row=next(s for s in (process/'limits').read_text().splitlines() if s.startswith('Max locked memory'))
        caps={s.split(':')[0]:int(s.split(':')[1].strip(),16) for s in (process/'status').read_text().splitlines() if s.startswith(('CapEff:','CapPrm:'))}
        return row.split()[-3:-1],caps,process
    try:
        measured=[values(x) for x in pids]
    except (OSError,StopIteration):
        raise blocked('a selected process exited before observation')
    for limit,caps,_ in measured:
        require(limit==['67108864','67108864'] and caps.keys()=={'CapEff','CapPrm'} and not any(v & (1<<14) for v in caps.values()),'session limit is not 67108864 bytes')
    if component: return
    expected=['mr-gui','alacritty','mr-sitting','mr-sitting']
    require(len(set(pids))==4,'launched and direct process identities were not observed')
    for (_,_,p),name in zip(measured,expected,strict=True):
        require((p/'exe').resolve().name==name,'session process identity differs')
