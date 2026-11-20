import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time


def plate_exit(bundle, runtime, sig):
    runtime.mkdir(mode=0o700)
    plan = bundle / 'public-plan.txt'
    handback = runtime / 'handback.txt'
    answers = (bundle / 'public-test-answers').read_bytes().splitlines(keepends=True)
    env = {'PATH': '/usr/bin:/bin', 'XDG_RUNTIME_DIR': str(runtime), 'LANG': 'C'}
    p = subprocess.Popen([bundle / 'review-mr-sitting', 'sit', '--plan', plan, '--hand-back', handback],
                         stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, env=env)
    private = runtime / 'refugium-sitting'
    try:
        p.stdin.write(b''.join(answers[:12]))
        p.stdin.flush()
        marker = b'make plate "SEED C" now'
        pending = b''
        deadline = time.monotonic() + 15
        with selectors.DefaultSelector() as poll:
            poll.register(p.stderr, selectors.EVENT_READ)
            while marker not in pending:
                if not poll.select(max(0, deadline - time.monotonic())):
                    raise RuntimeError('the candidate did not reach the plate screen')
                chunk = os.read(p.stderr.fileno(), 8192)
                if not chunk:
                    raise RuntimeError('the candidate exited before displaying its plate')
                pending = pending[-len(marker):] + chunk
        if not (private / 'plates').is_file():
            raise RuntimeError('the expected RAM-only plate file was absent before the signal')
        status = Path(f'/proc/{p.pid}/status').read_text().splitlines()
        locked_kib = int(next(line for line in status if line.startswith('VmLck:')).split()[1])
        p.send_signal(sig)
        p.wait(timeout=10)
        final = p.stderr.read()
        stop_report = b'the sitting stopped' in final
        return {'signal': sig.name, 'exit': p.returncode, 'locked_kib_before_signal': locked_kib,
                'private_dir_after': private.exists(), 'plates_after': (private / 'plates').exists(),
                'handback_after': handback.exists(), 'stop_report': stop_report,
                'claims_memory_wiped': b'are wiped from this computer' in final}
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
        p.stdin.close()
        p.stderr.close()


def check(root, work, command, require, blocked, component):
    location = os.environ.get('W3_REVIEW_BUNDLE')
    if not location:
        raise blocked('supply the compiled W1T review bundle and its public test vector')
    if set(os.listdir('/sys/class/net')) != {'lo'}:
        raise blocked('the ordinary helper requires an offline guest or isolated network namespace')
    fs = command(['stat', '-f', '-c', '%T', work])
    if fs.returncode != 0 or fs.stdout.strip() != b'tmpfs':
        raise blocked('the live plate fixture requires a test directory on tmpfs')
    bundle = Path(location).resolve()
    term = plate_exit(bundle, work / 'term', signal.SIGTERM)
    kill = plate_exit(bundle, work / 'kill', signal.SIGKILL)
    report = os.environ.get('W3_END_OBSERVATIONS')
    if report:
        with Path(report).open('x') as out:
            json.dump([term, kill], out, indent=2)
            out.write('\n')
    failure = 'cleanup report differs from the observed outcome'
    require(term['exit'] == 1 and term['stop_report'] and not term['private_dir_after'] and
            not term['handback_after'], failure)
    require(kill['exit'] == -signal.SIGKILL and not kill['stop_report'] and
            not kill['claims_memory_wiped'] and not kill['handback_after'], failure)
    if not component:
        require(not term['claims_memory_wiped'], failure)
        raise blocked('measure locked cleanup on the strict image, including a partial cleanup failure')
