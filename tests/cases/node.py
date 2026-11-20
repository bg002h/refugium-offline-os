import os
from pathlib import Path


def check(root,work,command,require,blocked,component):
    value=os.environ.get('W3_NODE_ROOT')
    if not value: raise blocked('supply the node image root')
    path=Path(value)
    require(not (path/'usr/bin/mr-sitting').exists(),'secret-handling helper present on node')
    release = (path / 'etc/os-release').read_text().splitlines()
    require({'ID=ubuntu', 'VERSION_CODENAME=noble', 'VARIANT_ID=refugium-node'} <= set(release),
            'node is not recognized as Ubuntu Noble by the receiver installer')
    if not component: raise blocked('node boot and requested removable mount are required')
