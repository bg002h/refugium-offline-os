"""Observe a disposable public-fixture wallet journey on the guest serial console."""
import json
import os
from pathlib import Path
import time

FOLDER = Path("/home/live/Holder's sitting folder")
PROGRAMS = {'weston', 'mr-gui', 'alacritty', 'mr-sitting'}


def process_row(proc):
    name = (proc / 'exe').resolve(strict=True).name
    if name not in PROGRAMS:
        return None
    fields = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines() if ':' in line)
    limit = next(line for line in (proc / 'limits').read_text().splitlines() if line.startswith('Max locked memory'))
    keys = {item.split(b'=', 1)[0].decode() for item in (proc / 'environ').read_bytes().split(b'\0') if item}
    row = dict(name=name, pid=int(proc.name), ppid=int(fields['PPid']), uid=int(fields['Uid'].split()[0]),
               limit=limit.split()[-3:-1], gui_marker='W3_GUI_ONLY' in keys)
    if name == 'mr-sitting':
        args = [os.fsdecode(a) for a in (proc / 'cmdline').read_bytes().split(b'\0')[1:] if a]
        # The only helper invocation this public fixture uses has two public file arguments.
        if len(args) == 5 and args[0] == 'sit' and args[1::2] == ['--plan', '--hand-back']:
            row['args'] = [arg if i not in (2, 4) or Path(arg).parent == FOLDER else '<other path>'
                           for i, arg in enumerate(args)]
        else:
            row['args'] = ['<unexpected invocation>']
        row['env_keys'] = sorted(keys)
    return row


def main():
    previous = None
    with open('/dev/ttyS0', 'w', buffering=1) as serial:
        for _ in range(1200):
            processes = []
            for proc in Path('/proc').glob('[0-9]*'):
                try:
                    row = process_row(proc)
                except (OSError, ValueError, KeyError, StopIteration):
                    continue
                if row:
                    processes.append(row)
            plans = sorted(str(p) for p in FOLDER.glob('refugium-plan-????????.txt'))
            sample = [sorted(processes, key=lambda p: p['pid']), plans]
            if sample != previous:
                print('W3-LAUNCH', json.dumps(sample), file=serial)
                previous = sample
            time.sleep(.5)


if __name__ == '__main__':
    main()
