"""Exercise an ordinary W1T candidate with the upstream public signet vector in RAM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import tempfile


def exercise(bundle, runtime):
    helper = bundle / 'review-mr-sitting'
    codec = bundle / 'review-codec'
    plan = bundle / 'public-plan.txt'
    env = dict(PATH='/usr/bin:/bin', XDG_RUNTIME_DIR=str(runtime), LANG='C')
    handback = runtime / 'refugium-handback-0000000c.txt'
    answers = (bundle / 'public-test-answers').read_bytes()
    result = subprocess.run([helper, 'sit', '--plan', plan, '--hand-back', handback],
                            env=env, input=answers, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=45)
    record = {'uid': os.getuid(), 'limit': resource.getrlimit(resource.RLIMIT_MEMLOCK),
              'sit_exit': result.returncode, 'handback': handback.is_file()}
    if handback.is_file():
        public = handback.read_bytes()
        changed = runtime / 'different-plan'
        changed.write_bytes(plan.read_bytes().replace(b'person holder\n', b'person guest\n'))
        def accepts(source):
            outcome = subprocess.run([codec, 'handback', '0000000c', source], input=public,
                                     capture_output=True, timeout=5)
            return outcome.returncode == 0 and outcome.stdout == b'handback 0000000c\n'
        record['matched'] = accepts(plan)
        record['changed_plan_rejected'] = not accepts(changed)
        if record['matched']:
            record['public_handback_sha256'] = hashlib.sha256(public).hexdigest()
    invalid = runtime / 'public-invalid'
    invalid.write_bytes(b'public-invalid-fixture\n')
    def insufficient():
        resource.setrlimit(resource.RLIMIT_MEMLOCK, (128 << 10, 128 << 10))
    with invalid.open('rb', buffering=0) as file:
        low = subprocess.run([helper, 'root', '--network', 'signet', '--letters', 'none', '--from', 'coins'],
                             stdin=file, env=env, capture_output=True, preexec_fn=insufficient, timeout=10)
        record.update(low_exit=low.returncode, low_bytes_read=file.tell(),
                      low_lock_warning=b'lock its memory' in low.stderr)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(dir=os.environ['XDG_RUNTIME_DIR']) as runtime:
        record = exercise(args.bundle, Path(runtime))
    print('W3-REVIEW', json.dumps(record, sort_keys=True), flush=True)
