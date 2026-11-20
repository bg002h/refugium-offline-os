"""Record boot observations on the serial port of a disposable development image."""
import os
from pathlib import Path
import subprocess


def observe(serial):
    def report(key, *values):
        print('W3-BOOT', key, *values, file=serial, flush=True)

    report('release', os.uname().release)
    release = Path('/etc/os-release').read_text().splitlines()
    report('identity', *(s for s in release if s.startswith(('ID=', 'VARIANT_ID=', 'VERSION_CODENAME='))))
    report('pid1', Path('/proc/1/comm').read_text().strip())
    report('interfaces', ','.join(sorted(os.listdir('/sys/class/net'))))
    report('proc_swaps', Path('/proc/swaps').exists())
    for row in Path('/proc/self/mountinfo').read_text().splitlines():
        fields = row.split()
        if fields[4] in ('/', '/run', '/home', '/tmp', '/var') or fields[4].startswith('/media/'):
            report('mount', fields[4], fields[fields.index('-') + 1], fields[5])
    report('helper_installed', Path('/usr/bin/mr-sitting').exists())
    if 'ID=mr-sitting-stick' in release:
        props = ['Result', 'ExecStartPre', 'ActiveState', 'LimitMEMLOCK', 'LimitMEMLOCKSoft']
        unit = subprocess.check_output(['systemctl', 'show', 'refugium-session.service',
                                        '--property=' + ','.join(props)], text=True)
        for line in unit.splitlines():
            report('session', line)
        for name, args in [('mr-gui', ['--version']), ('mr', ['--version']), ('me', ['--version']),
                           ('picotool', ['version'])]:
            try:
                result = subprocess.run(['/usr/bin/' + name, *args], capture_output=True, text=True,
                                        timeout=5)
                summary = (result.stdout + result.stderr).strip().splitlines()
                report('application', name, result.returncode, summary[0][:160] if summary else '')
            except (OSError, subprocess.TimeoutExpired) as error:
                report('application_error', name, str(error))
    report('complete', 1)


if __name__ == '__main__':
    with open('/dev/ttyS0', 'w') as serial:
        observe(serial)
