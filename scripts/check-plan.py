#!/usr/bin/env python3
"""Compare the plan's acceptance commands and coverage map to the specification."""
import argparse
import csv
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TEST_ROW = re.compile(r'^\| ([BSUR]\d\d) \| (.+?) \| ([a-z]+) \| (.+?) \|$')
TEXT_ROW = re.compile(r'^\| (D\d\d) \| (.+?) \| (.+?) \|$')
PLAN_ROW = re.compile(r'^\| ([a-z]+) \| .+? \| `python3 tests/accept.py ([a-z]+)` \| `FAIL ([a-z]+): (.+?)` \|$')


def spec_items(spec):
    items = {}
    tests = set()
    for line in spec.splitlines():
        m = TEST_ROW.fullmatch(line)
        t = TEXT_ROW.fullmatch(line)
        if m:
            key, contract, name, expected = m.groups()
            if name in tests:
                raise ValueError(f'duplicate test {name}')
            tests.add(name)
            quote = contract + ' ' + expected
        elif t:
            key, condition, message = t.groups()
            quote = condition + ' ' + message
        elif line and not line.startswith(('#', '|')):
            # Prose is covered as well. A changed paragraph invalidates its map entry.
            key = f'P{1 + sum(k.startswith("P") for k in items):02d}'
            quote = line
        else:
            continue
        if key in items:
            raise ValueError(f'duplicate specification item {key}')
        items[key] = quote
    if not tests or not items:
        raise ValueError('specification has no acceptance requirements')
    return items, tests


def check(spec, plan, coverage):
    items, tests = spec_items(spec)
    planned = {}
    for line in plan.splitlines():
        m = PLAN_ROW.fullmatch(line)
        if m:
            name, command, result, reason = m.groups()
            if name in planned or len({name, command, result}) != 1:
                raise ValueError(f'inconsistent plan row {name}')
            planned[name] = reason
    if set(planned) != tests:
        raise ValueError('plan commands differ from specification tests')
    rows = list(csv.DictReader(coverage.splitlines(), delimiter='\t'))
    if {r['id'] for r in rows} != set(items) or len(rows) != len(items):
        raise ValueError('coverage IDs differ from specification')
    for row in rows:
        key = row['id']
        if row['quote'] != items[key]:
            raise ValueError(f'stale coverage quote {key}')
        names = set(row['tests'].split(','))
        if not names or not names <= tests:
            raise ValueError(f'unknown coverage test for {key}')
        contract = next((m for line in spec.splitlines() if (m := TEST_ROW.fullmatch(line)) and m[1] == key), None)
        if contract and contract[3] not in names:
            raise ValueError(f'coverage omits primary test for {key}')
    return len(tests), len(items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broken-control', action='store_true')
    args = parser.parse_args()
    folder = ROOT / 'design'
    spec = (folder / 'SPEC_w3_stick.md').read_text()
    plan = (folder / 'PLAN_w3_stick.md').read_text()
    coverage = (folder / 'PLAN_w3_stick-coverage.tsv').read_text()
    if args.broken_control:
        coverage = coverage.replace('B01\t', 'absent\t', 1)
    try:
        tests, items = check(spec, plan, coverage)
    except (ValueError, KeyError) as error:
        print(f'FAIL plan: {error}', file=sys.stderr)
        return 1
    print(f'PASS plan: {tests} tests, {items} mapped specification items')
    return 0


if __name__ == '__main__':
    sys.exit(main())
