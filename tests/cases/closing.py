import os
from pathlib import Path


def check(root, work, command, require, blocked, component):
    executable = os.environ.get('W3_CLOSING_TEST_BIN')
    if not executable or not Path(executable).is_file():
        raise blocked('supply the mr-sitting unit-test executable from the reviewed W1T revision')
    source = os.environ.get('W3_MR_SOURCE')
    if not source or not (Path(source) / 'crates/mr-sitting/Cargo.toml').is_file():
        raise blocked('supply the matching W1T workspace so the upstream test can build its mr CLI')
    case = 'w1t_tests::wait::ms_w1t_check_spawn_fails'
    result = command([executable, '--exact', case, '--test-threads=1'],
                     cwd=source, env=dict(os.environ, TMPDIR=str(work), CARGO_NET_OFFLINE='true'), timeout=180)
    lines = result.stdout.decode(errors='replace').splitlines()
    require(result.returncode == 0 and f'test {case} ... ok' in lines and
            any(line.startswith('test result: ok. 1 passed; 0 failed;') for line in lines),
            'closing failure lost the safe waiting state')
    if not component:
        raise blocked('observe the lock through worker failure, retry and quit in the packaged strict helper')
