"""Run as the live user inside the wallet's D-Bus session on a disposable test image."""
import os
import subprocess


def main():
    address = os.environ['DBUS_SESSION_BUS_ADDRESS']
    bus = ['busctl', '--timeout=5', '--address=' + address]
    chooser = subprocess.run(
        [*bus, 'introspect', 'org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop',
         'org.freedesktop.portal.FileChooser'], capture_output=True, text=True)
    available = any(line.split()[:2] == ['.OpenFile', 'method'] for line in chooser.stdout.splitlines())
    print(f'W3-PORTAL FileChooser rc={chooser.returncode} OpenFile={available} err={chooser.stderr.strip()}')
    names = subprocess.run([*bus, '--acquired', '--no-pager', 'list'], capture_output=True, text=True, check=True)
    acquired = [line.split()[0] for line in names.stdout.splitlines()
                if line.startswith('org.freedesktop.') and '.portal.' in line]
    print('W3-PORTAL acquired=' + ' '.join(acquired))


if __name__ == '__main__':
    main()
