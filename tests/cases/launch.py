"""Check the wallet-to-terminal-to-helper handoff observed in a development VM."""
import json
import os
from pathlib import Path

FAILURE = 'terminal launch contract changed'


def capture_ok(rows):
    wallet_pid = None
    for processes, plans in rows:
        names = {process['name'] for process in processes}
        if wallet_pid is not None and names.isdisjoint({'alacritty', 'mr-sitting'}):
            if any(p['name'] == 'mr-gui' and p['pid'] == wallet_pid for p in processes):
                return True
        by_name = {p['name']: p for p in processes}
        if not {'alacritty', 'mr-sitting'} <= names:
            continue
        terminal, helper = by_name['alacritty'], by_name['mr-sitting']
        parent = next((p for p in processes if p['pid'] == terminal['ppid']), None)
        if not parent or parent['name'] != 'mr-gui' or not parent['gui_marker']:
            return False
        if any(p['uid'] != 1000 or p['limit'] != ['67108864', '67108864'] for p in (parent, terminal, helper)):
            return False
        if terminal['gui_marker'] or helper['gui_marker'] or set(helper['env_keys']) != {'LANG', 'PATH', 'TERM', 'XDG_RUNTIME_DIR'}:
            return False
        if len(plans) != 1 or Path(plans[0]).parent != Path("/home/live/Holder's sitting folder"):
            return False
        plan = Path(plans[0])
        handback = plan.with_name(plan.name.replace('refugium-plan-', 'refugium-handback-', 1))
        if handback == plan or helper['args'] != ['sit', '--plan', str(plan), '--hand-back', str(handback)]:
            return False
        wallet_pid = parent['pid']
    return False


def check(root, work, command, require, blocked, component):
    source = os.environ.get('W3_DESKTOP_SERIAL')
    if not source:
        raise blocked('supply the development VM serial capture of the public wallet journey')
    lines = Path(source).read_text(errors='replace').splitlines()
    rows = [json.loads(line.removeprefix('W3-LAUNCH ')) for line in lines if line.startswith('W3-LAUNCH ')]
    require(capture_ok(rows), FAILURE)
    if not component:
        raise blocked('qualify the production helper and exercise power-off confirmation on the stick')
