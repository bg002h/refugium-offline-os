import json
import os
from pathlib import Path


def check(root,work,command,require,blocked,component):
    base = json.loads((root / 'image/base.lock.json').read_text())
    require(base.get('suite') == 'noble' and base['architecture'] == 'amd64',
            'image base differs from the receiver-supported target')
    folder=Path(os.environ.get('W3_PROFILES',root/'image/profiles'))
    if not folder.is_dir():
        raise blocked('no role manifests supplied')
    roles={p.stem:json.loads(p.read_bytes()) for p in folder.glob('*.json')}
    require(roles.keys()=={'sitting-stick','node'},'image roles share the wrong kernel')
    sitting,node=roles['sitting-stick'],roles['node']
    def symbols(role):
        return set((root/'image/kernel'/role['config']).read_text().splitlines())
    require(sitting['config']!=node['config'] and sitting['suffix']=='-mr-sitting' and node['suffix']=='-mr-node',
            'image roles share the wrong kernel')
    require('CONFIG_NETDEVICES=y' not in symbols(sitting) and 'CONFIG_NETDEVICES=y' in symbols(node),
            'image roles share the wrong kernel')
    require({'CONFIG_FRAMEBUFFER_CONSOLE=y', 'CONFIG_DRM_FBDEV_EMULATION=y'} <= symbols(sitting),
            'sitting kernel cannot display boot refusals on the framebuffer console')
    require('mr-sitting' in sitting['applications'] and 'mr-sitting' not in node['applications'],
            'image roles share the wrong kernel')
    require(set(sitting['applications'])=={'mr','mr-sitting','mr-gui','me','picotool'},'application roles differ')
