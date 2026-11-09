#!/usr/bin/env python3
"""Verify the source19 home-buy ware restore (source fix e075f0ac) on product cores.

borg_think_home_buy_useful() took the trial quantity (and charges) off
its copy of the home ware before the pack-room checks, but the two
"require two empty slots" checks skipped the ware with a bare continue,
leaving the copy reduced instead of restored from borg_safe_shops.
Later store steps read that copy: with exactly one free pack slot and a
single weapon in the home, the weapon was left at quantity zero and the
backup-weapon step skipped it.  The correction restores the ware before
each of those continues.
The single mode fails before (the backup-weapon step skips the zeroed
ware) and passes after (it buys).  The pair mode is a second flip on
this product, disclosed: its outcome row (buys_home_ware0=1) matches
the kit's recorded row in both phases, but the scenario's own
self-check fails before the fix here, because the carried
urgentshop-23/starvealch-18 changes in this module alter that
secondary self-check (the kit's before-row passed on the pristine
base); after the fix it passes.  The roomy and stack controls pass in
both phases with byte-identical logs.
Fixture: kit 40495b33a5136be40b09b317f731f60841686c00 at head fbd96fa79610d00a148372efd55a63ee5da13c66. Normal phases only. Before phases
(the pre-fix build) fail the flip mode; after phases pass every mode;
control logs are byte-identical across the correction.

Run under the shared native lock after this tree's gate build, with the
before snapshot built at the before commit (its gate result recorded
under --before-gate).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BEFORE = 'f8ecd11c7d16348894db9d8ef4485d7cfe3a7696'
FIX = 'e075f0ac7c618fdd32eb5bd4b49d1936e8738da4'
EVIDENCE = 'fbd96fa79610d00a148372efd55a63ee5da13c66'
PIN = '40495b33a5136be40b09b317f731f60841686c00'
PREFIX = 'docs/audit/c-reports/homebuyqty-19/'
SOURCE = 'src/borg/borg-store-buy.c'
MODES = ('single', 'pair', 'roomy', 'stack')
SUITE = 'native-c/homebuyqty-19'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-gate', required=True, type=Path,
                   help='result.json of the gate run at the before commit')
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--product-gate', default=ROOT / 'artifacts/native/result.json', type=Path)
    p.add_argument('--fix', required=True, help='applied product commit')
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()

    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)

    (out / 'scenario.c').write_bytes(read(EVIDENCE, PREFIX + 'scenario.c'))
    (out / 'profile/borg.txt').write_bytes(read(EVIDENCE, PREFIX + 'borg.txt'))
    same = subprocess.run(
        ['git', 'diff', '--exit-code', PIN, EVIDENCE, '--',
         PREFIX + 'scenario.c', PREFIX + 'borg.txt', PREFIX + 'profile'],
        cwd=ROOT, capture_output=True)
    assert same.returncode == 0, 'runtime fixtures changed since the run pin'
    before, build = args.before_build.resolve(), args.product_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / SOURCE).parent.mkdir(parents=True)
        (d / SOURCE).write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / SOURCE).read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered, 'product module != before + source diff'
    # Single-step PR: the fix commit itself touches only SOURCE, and the
    # tree-level scope from BEFORE to HEAD is SOURCE alone.
    fix_scope = subprocess.check_output(
        ['git', 'diff', '--name-only', FIX + '^', FIX, '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert fix_scope == [SOURCE], fix_scope
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', BEFORE, 'HEAD', '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert changed == [SOURCE], changed
    subprocess.run(['git', 'merge-base', '--is-ancestor', args.fix, 'HEAD'], cwd=ROOT, check=True)

    before_gate = json.loads(args.before_gate.resolve().read_text())
    assert before_gate['success'] and before_gate['commit'] == BEFORE
    product_gate = json.loads(args.product_gate.resolve().read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert product_gate['success']
    subprocess.run(['git', 'merge-base', '--is-ancestor', product_gate['commit'], 'HEAD'],
                   cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--exit-code', product_gate['commit'], 'HEAD', '--',
                    'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)

    report = {
        'fixture_commit': EVIDENCE, 'fixture_pin': PIN,
        'fixture_sha256': sha(out / 'scenario.c'),
        'source_fix': FIX, 'fix': args.fix,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE,
        'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': head,
        'product_native_gate': product_gate,
        'product_binary_sha256': sha(build / 'game/angband'),
        'phases': {}, 'verified': False,
    }
    for phase, core in (('before', before), ('after', build)):
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                   '-I' + str(ROOT / 'src/tests'), str(out / 'scenario.c'),
                   *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, **{'HB19_MODE': mode,
                                        'HB19_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            omatch = re.search(r'OUTCOME (.*)', text)
            rows[mode] = {
                'exit': result.returncode,
                'passed': SUITE + ' finished: 1/1 passed' in text,
                'outcome': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch[1])} if omatch else {},
                'log_sha256': sha(log),
            }
            print(phase, mode, rows[mode], flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command,
                                   'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    b, a = report['phases']['before']['cases'], report['phases']['after']['cases']
    for mode in MODES:
        assert b[mode]['exit'] == 0 and a[mode]['exit'] == 0, mode
    assert not b['single']['passed'] and b['single']['outcome'] == {'buys_home_ware0': 0}
    assert a['single']['passed'] and a['single']['outcome'] == {'buys_home_ware0': 1}
    # pair is a second flip on this product: its outcome row (buys=1)
    # matches the kit's recorded row in both phases, but the scenario's
    # own self-check fails before the fix on the consumer -- the carried
    # urgentshop-23/starvealch-18 changes in this module alter the
    # scenario's secondary self-check (the kit's before-row passed on
    # the pristine base).  Disclosed in the verifier commit and doc.
    assert not b['pair']['passed'] and a['pair']['passed'], 'pair'
    assert b['pair']['outcome'] == a['pair']['outcome'] == {'buys_home_ware0': 1}
    for mode in ('roomy', 'stack'):
        assert b[mode]['passed'] and a[mode]['passed'], mode
        assert b[mode]['outcome'] == a[mode]['outcome'], (mode, 'outcome changed')
    for mode in ('roomy', 'stack'):
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], (mode, 'log changed')
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
