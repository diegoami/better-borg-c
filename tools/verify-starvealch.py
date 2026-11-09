#!/usr/bin/env python3
"""Verify the source18 Remove Hunger at the Alchemist (source fix 0fd9bc4b) on product cores.

When the Borg carries no food, borg_think_shop_buy_useful() only
weighed the General Store and the Home, and a malformed starving check
(tval != scroll && sval != Remove Hunger) let any scroll through; the
scrolls also were never counted as food, so buying one never raised the
Borg's power.  Remove Hunger is sold by the Alchemist (store 4).  The
correction admits store 4 in the no-food store filter, writes the check
as "food, or a Scroll of Remove Hunger", and counts those scrolls as
food only when no other food is carried.
Note: this product already carries urgentshop-23 (the poisoned/cut
store filter at index 4), which the source base predates -- the
cherry-pick's first hunk is resolved by hand preserving both.
The starving mode fails before (nothing bought) and passes after (the
Remove Hunger scroll is bought); the general_food and fed controls pass
in both phases with byte-identical logs.
Fixture: kit 97bcf2a980749472b5ce1dba44ac7cb054ca274d at head bbc5de859c7b27d02d88c1bb84ec46d796de8716. Normal phases only. Before phases
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
BEFORE = '0a75c0736f45b08b3df7fc73d716196d9eca9f02'
FIX = '0fd9bc4bd6f069e0cbab664e7541e3202764a9a4'
EVIDENCE = '99db3c5ca26afceb280b0f49fb48f2756176488e'
PIN = '98aa8ad02781766425e8ff1b28550f860f034417'
PREFIX = 'docs/audit/c-reports/starvealch-18/'
SOURCES = ('src/borg/borg-store-buy.c', 'src/borg/borg-trait.c')
MODES = ('starving', 'general_food', 'fed')
SUITE = 'native-c/starvealch-18'


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
    # Single-step PR: the fix commit itself touches only the two files
    # here, and so does the tree-level scope from BEFORE to HEAD.  (The
    # applied commit carries the hand-resolved urgentshop-23 context --
    # our carried store-4 filter -- which the source base predates; the
    # layered-module check proves the source diff still reproduces the
    # product modules.)
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
                env=dict(os.environ, **{'SA18_MODE': mode,
                                        'SA18_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
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
    assert not b['starving']['passed'] and b['starving']['outcome'] == {'buys_food': 0, 'buys_remove_hunger': 0}
    assert a['starving']['passed'] and a['starving']['outcome'] == {'buys_food': 0, 'buys_remove_hunger': 1}
    assert b['general_food']['passed'] and a['general_food']['passed']
    assert b['fed']['passed'] and a['fed']['passed']
    assert b['general_food']['log_sha256'] == a['general_food']['log_sha256'], ('control changed', 'general_food')
    assert b['fed']['log_sha256'] == a['fed']['log_sha256'], ('control changed', 'fed')
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
