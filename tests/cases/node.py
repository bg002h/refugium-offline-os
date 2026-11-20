import os
from pathlib import Path


def check(root,work,command,require,blocked,component):
    value=os.environ.get('W3_NODE_ROOT')
    if not value: raise blocked('supply the node image root')
    path=Path(value)
    require(not (path/'usr/bin/mr-sitting').exists(),'secret-handling helper present on node')
    require('ID=refugium-node' in (path/'etc/os-release').read_text().splitlines(),'node identity differs')
    if not component: raise blocked('node boot and requested removable mount are required')
