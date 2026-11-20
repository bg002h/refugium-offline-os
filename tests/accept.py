#!/usr/bin/env python3
"""Run a named W3 acceptance case. Missing prerequisites are distinct from failures."""
import argparse
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class Blocked(Exception):
    """The case has no subject to observe."""


class Failure(Exception):
    """The observed behavior differs from the specification."""


def require(condition, reason):
    if not condition:
        raise Failure(reason)


def command(argv, **kwargs):
    return subprocess.run([str(part) for part in argv], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False, **kwargs)


def main():
    spec = (ROOT / 'design/SPEC_w3_stick.md').read_text()
    choices = re.findall(r'^\| [BSUR]\d\d \| .+? \| ([a-z]+) \|', spec, re.M)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=choices)
    parser.add_argument('--component',action='store_true',help='run only the implemented component checks')
    args = parser.parse_args()
    name = args.case
    source = ROOT / 'tests/cases' / f'{name}.py'
    cwd = Path(os.environ.get('W3_TEST_WORK', ROOT / '.work/tests')).resolve()
    cwd.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        if not source.is_file():
            raise Blocked('case implementation is pending')
        with tempfile.TemporaryDirectory(prefix=name+'-',dir=cwd) as tmp:
            test = runpy.run_path(str(source))
            test['check'](ROOT, Path(tmp), command, require, Blocked, args.component)
    except Blocked as error:
        print(f'BLOCKED {name}: {error}', file=sys.stderr)
        return 77
    except Failure as error:
        print(f'FAIL {name}: {error}', file=sys.stderr)
        return 1
    print(f'PASS {name}' + (' (component only)' if args.component else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
