import os
from pathlib import Path
import sys


def check(root,work,command,require,blocked):
    # Validate that the host-side baseline has the interface that a mistaken image would expose.
    actual=sorted(p.name for p in Path('/sys/class/net').iterdir())
    probe=root/'scripts/probe-kernel.py'
    if not probe.exists():
        if actual==['lo']:
            raise blocked('a booted baseline with a network interface is required')
        require(actual==['lo'],'unexpected network interface')
    settings={key:os.environ.get(key) for key in ('W3_KERNEL','W3_CONFIG')}
    if not all(settings.values()):
        raise blocked('set W3_KERNEL and W3_CONFIG to a built kernel and its resolved config')
    result=command([sys.executable,'-B',probe,'--kernel',settings['W3_KERNEL'],'--config',settings['W3_CONFIG'],'--work',work])
    require(result.returncode==0 and b'W3-PROBE PASS' in result.stdout,'unexpected network interface')
    # Full acceptance also checks the contents of the actual image and a live USB Ethernet insertion.
    if not os.environ.get('W3_IMAGE_OBSERVATIONS'):
        raise blocked('complete-image driver inventory and USB hotplug observations are required')
    from_image=root/'tests'/'image-driver-inventory.py'
    if not from_image.is_file():
        raise blocked('complete-image inventory runner is pending')
    result=command([sys.executable,'-B',from_image,os.environ['W3_IMAGE_OBSERVATIONS']])
    require(result.returncode==0,'unexpected network interface')
