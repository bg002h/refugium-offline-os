#!/usr/bin/env python3
"""Build a W1T review bundle from a local commit and its vendored dependencies."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def public_answers(source):
    # Use the upstream line test's public values and response order. Refuse a changed grammar.
    def vector(name):
        value = re.search(r'pub fn ' + name + r'\(\) -> String \{\s*unbroken\(\s*"([^"]+)"', source)
        return value[1].replace('|', '').replace(' zzz', '')

    def constant(name):
        return re.search(r'pub const ' + name + r': &str = "([^"]*)";', source)[1]

    known = {'&coins': vector('c_coins'), '&words': vector('c_words'),
             'PW_FLIPS': constant('PW_FLIPS'), 'PW_CHECK': constant('PW_CHECK')}
    sequence = re.search(r'pub fn c_answers\(\) -> String \{.*?script\(&\[(.*?)\]\)', source, re.S)[1]
    answers = []
    for value in sequence.split(','):
        token = value.strip()
        if token:
            answers.append(token[1:-1] if re.fullmatch(r'"[^"]*"', token) else known[token])
    return '\n'.join(answers) + '\n'


def vendor_config(lock):
    lines = ['[source.crates-io]', 'replace-with="vendored-sources"',
             '[source.vendored-sources]', 'directory="src/vendor"']
    sources = {p['source'] for p in lock['package'] if p.get('source', '').startswith('git+')}
    for source in sorted(sources):
        url, revision = source[4:].split('?rev=')
        rev, resolved = revision.split('#')
        if rev != resolved or not re.fullmatch(r'[0-9a-f]{40}', resolved):
            raise ValueError('expected a git dependency pinned to a full commit')
        lines.extend([f'[source."{url}?rev={rev}"]', f'git="{url}"', f'rev="{rev}"',
                      'replace-with="vendored-sources"'])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('revision', help='full mr commit to test')
    parser.add_argument('work', type=Path, help='new directory for the checkout and its review bundle')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.revision):
        parser.error('supply a full commit ID')
    work = args.work.resolve()
    work.mkdir(mode=0o700, exist_ok=False)
    src, bundle, cargo, tmp = (work / n for n in ('src', 'bundle', 'cargo-home', 'tmp'))
    for directory in (src, bundle, cargo, tmp):
        directory.mkdir()
    archive = work / 'source.tar'
    subprocess.run(['git', '-C', args.repo.resolve(), 'archive', '--output', archive, args.revision],
                   check=True)
    with tarfile.open(archive) as source:
        source.extractall(src, filter='data')
    archive.unlink()
    lock = tomllib.loads((src / 'Cargo.lock').read_text())
    (cargo / 'config.toml').write_text(vendor_config(lock))
    codec_source = src / 'crates/mr-codec/src/bin'
    codec_source.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'image/tools/w3-public-file.rs', codec_source / 'w3-public-file.rs')
    toolchain = tomllib.loads((src / 'rust-toolchain.toml').read_text())['toolchain']['channel']
    env = dict(os.environ, CARGO_HOME=str(cargo), CARGO_TARGET_DIR=str(work / 'target'),
               TMPDIR=str(tmp), RUSTUP_TOOLCHAIN=toolchain, CARGO_NET_OFFLINE='true')
    subprocess.run(['cargo', 'build', '--offline', '--locked', '-p', 'mr-sitting', '-p', 'mr-codec',
                    '--bin', 'mr-sitting', '--bin', 'w3-public-file'], cwd=src, env=env, check=True)
    for binary, name in [('mr-sitting', 'review-mr-sitting'), ('w3-public-file', 'review-codec')]:
        subprocess.run(['objcopy', '--strip-debug', work / 'target/debug' / binary, bundle / name],
                       check=True)
    fixture = (src / 'crates/mr-sitting/tests/common/mod.rs').read_text()
    (bundle / 'public-test-answers').write_text(public_answers(fixture))
    (bundle / 'revision').write_text(args.revision + '\n')
    shutil.copyfile(ROOT / 'tests/fixtures/public-plan.txt', bundle / 'public-plan.txt')
    shutil.copyfile(ROOT / 'tests/guest/observe-reviewed-helper.py', bundle / 'observe-reviewed-helper.py')


if __name__ == '__main__':
    main()
