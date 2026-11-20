"""Check the session bus that the wallet uses on the booted stick."""
import os
from pathlib import Path

FAILURE = 'wallet could not export the plan'


def check(root, work, command, require, blocked, component):
    source = os.environ.get('W3_DESKTOP_SERIAL')
    if not source:
        raise blocked('supply the serial capture from a booted stick with the folder-chooser probe')
    lines = Path(source).read_text(errors='replace').splitlines()
    require('W3-BOOT identity VERSION_CODENAME=noble ID=mr-sitting-stick' in lines, FAILURE)
    require(any(line.startswith('W3-PORTAL FileChooser rc=0 OpenFile=True ') for line in lines), FAILURE)
    backend = 'org.freedesktop.impl.portal.desktop.gtk'
    require(any(backend in line.split('=', 1)[1].split()
                for line in lines if line.startswith('W3-PORTAL acquired=')), FAILURE)
    if not component:
        raise blocked('the complete desktop case requires a wallet export after production preflight')
