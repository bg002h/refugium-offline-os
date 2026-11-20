import os
from pathlib import Path
import subprocess
import tomllib


def check(root,work,command,require,blocked,component):
    policy=root/'image/stick/alacritty.toml'
    launcher=root/'image/stick/x-terminal-emulator'
    grid=Path(os.environ['W3_TERMINAL_GRID']) if 'W3_TERMINAL_GRID' in os.environ else None
    if not policy.exists():
        if grid is None: raise blocked('no terminal capture or image-owned configuration')
        import json
        capture=json.loads(grid.read_text())['raw']
        require(capture['len']==capture['visible_lines'],'terminal exposed protected history or text')
    config=tomllib.loads(policy.read_text())
    require(config['scrolling']['history']==0 and config.get('ipc_socket') is False and config.get('live_config_reload') is False and config['terminal']['osc52']=='Disabled','terminal exposed protected history or text')
    for bad in (['--ref-test'],['-e'],['-e','--ref-test'],['-e','/bin/sh','-x'],['-e','/usr/bin/env','--ref-test']):
        result=command([launcher,*bad],env={'PATH':'/usr/bin:/bin','XDG_RUNTIME_DIR':str(work)})
        require(result.returncode==2,'terminal exposed protected history or text')
    if component: return
    raise blocked('shipping compositor, live history and accessibility positive controls are required')
