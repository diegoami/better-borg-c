#!/usr/bin/env python3
"""Verify the source23 Alchemy cures (source fix 09c28cd59) on product cores.

A poisoned or bleeding Borg in town flowed to store index 3 and only
weighed that store's wares: index 3 was the Temple in older versions
but is the Bookseller in 4.2, while cure potions are sold in the
Alchemy shop, index 4. The character looked at books instead of buying
cures. The correction uses index 4 in both borg_think_shop_buy_useful()
and borg_choose_shop().
The poisoned and bleeding modes fail before (no cure bought) and pass
after (cure bought); the healthy control passes in both with a
byte-identical log.
Fixture: kit dbd9ddf1bddabb4c2b3d35099f9d0efd065ae2a3 at head e0ecd1ef777447ab02e84255be6717fea303921f, asserted byte-identical to
the run pin.
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
BEFORE = 'bd6c7ebbeda158ab17c2cf50aedfc0fed1832c3e'
FIX = '09c28cd59c948fa03fb49349d30e7236b6d067ed'
EVIDENCE = 'e0ecd1ef777447ab02e84255be6717fea303921f'
PIN = 'dbd9ddf1bddabb4c2b3d35099f9d0efd065ae2a3'
PREFIX = 'docs/audit/c-reports/urgentshop-23/'
SOURCES = ('src/borg/borg-store-buy.c', 'src/borg/borg-think-store.c')
MODES = ('poisoned', 'bleeding', 'healthy')
SUITE = 'native-c/urgentshop-23'


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
        ['git', 'diff', FIX + '^', FIX, '--'] + list(SOURCES), cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        for source in SOURCES:
            (d / source).parent.mkdir(parents=True, exist_ok=True)
            (d / source).write_bytes(read(BEFORE, source))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        for source in SOURCES:
            layered = (d / source).read_bytes()
            assert (ROOT / source).read_bytes() == layered, \
                'product module != before + source diff: ' + source
    # This fix is stacked after dimdoor-21 (patch 0086) in this PR;
    # BEFORE is this step's actual before commit, the dimdoor step tip
    # (borg-escape.c is already fixed there and is proven by that step's
    # own verifier). The fix commit itself touches only the two files
    # here, and so does the tree-level scope from BEFORE to HEAD.
    fix_scope = subprocess.check_output(
        ['git', 'diff', '--name-only', FIX + '^', FIX, '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert fix_scope == sorted(SOURCES), fix_scope
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', BEFORE, 'HEAD', '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert changed == sorted(SOURCES), changed
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
                env=dict(os.environ, **{'US23_MODE': mode,
                                        'US23_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
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
    assert not b['poisoned']['passed'] and b['poisoned']['outcome'] == {'buys_cure': 0}
    assert a['poisoned']['passed'] and a['poisoned']['outcome'] == {'buys_cure': 1}
    assert not b['bleeding']['passed'] and b['bleeding']['outcome'] == {'buys_cure': 0}
    assert a['bleeding']['passed'] and a['bleeding']['outcome'] == {'buys_cure': 1}
    assert b['healthy']['passed'] and a['healthy']['passed']
    assert b['healthy']['log_sha256'] == a['healthy']['log_sha256'], ('control changed', 'healthy')
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
