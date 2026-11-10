#!/usr/bin/env python3
"""Verify that the Lunal take skip is gated on the runtime mode (correction to 0101).

The source fix skips every item borg_flow_take_lunal() marks bad.  That
routine serves two modes: Lunal scumming and munchkin collection.  Gating on
borg_cfg[BORG_MUNCHKIN_START] was wrong - it is a class/config flag that is
true for Warrior, Druid and Ranger for the whole game - so the skip was
disabled everywhere for those classes and the Lunal path the defect was
reported for never got the fix.  The product gates on borg.munchkin_mode
instead.

The kit runs the same visible Dagger in both runtime modes: with munchkin
mode off the borg skips the marked-bad item (rc=0); with it on, munchkin mode
collects what it can sell and the item is taken (rc=1).  The gold control is
taken in both.  Before the correction (commit ebedce47d) the munchkin-mode
mode fails: the config gate skips the item even though the runtime mode is
munchkin.  After the correction all three pass.

Run under the shared native lock after this tree's gate build, with the before
snapshot built at the before commit (its gate result recorded under
--before-gate).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BEFORE = 'ebedce47da29e730907c7e99217e28801ae5896e'
FIX = '45423c1c8d99bc7846dc8503fa0a2be0e5c7e149'
EVIDENCE = '7084c916e'
PREFIX = 'docs/audit/c-reports/lunaltake-73/'
SOURCE = 'src/borg/borg-flow-take.c'
MODES = ('dagger', 'dagger-munchkin', 'gold')
SUITE = 'native-c/lunaltake-73'
# Passes before, passes after.  The munchkin mode is the one the config gate
# got wrong.
EXPECT = {'dagger': (True, True), 'dagger-munchkin': (False, True), 'gold': (True, True)}
ROWS = {'dagger': {'walks_to_item': 0},
        'dagger-munchkin': {'walks_to_item': 1},
        'gold': {'walks_to_item': 1}}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-gate', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--product-gate', default=ROOT / 'artifacts/native/result.json', type=Path)
    p.add_argument('--fix', required=True, help='applied product commit')
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()

    evidence = subprocess.check_output(
        ['git', 'rev-parse', EVIDENCE], cwd=ROOT, text=True).strip()

    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)

    (out / 'scenario.c').write_bytes(read(evidence, PREFIX + 'scenario.c'))
    (out / 'profile/borg.txt').write_bytes(read(evidence, PREFIX + 'profile/borg.txt'))
    for name in ('scenario.c', 'profile/borg.txt'):
        assert (ROOT / PREFIX / name).read_bytes() == (out / name).read_bytes(), \
            'working-tree fixture differs from its commit: ' + name

    before, build = args.before_build.resolve(), args.product_build.resolve()

    # Provenance: the before module carries the config gate; the product must be
    # that module with exactly the runtime-mode gate substituted.
    cfg_gate = b'        if (item_bad && !borg_cfg[BORG_MUNCHKIN_START])\n            continue;'
    mode_gate = b'        if (item_bad && !borg.munchkin_mode)\n            continue;'
    before_module = read(BEFORE, SOURCE)
    assert before_module.count(cfg_gate) == 1, 'config gate not found in the before module'
    assert (ROOT / SOURCE).read_bytes() == before_module.replace(cfg_gate, mode_gate), \
        'product module != before + runtime-mode gate'
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
        'fixture_commit': evidence,
        'fixture_sha256': sha(out / 'scenario.c'),
        'source_fix': FIX, 'fix': args.fix,
        'provenance': 'before module (config gate) + runtime-mode gate == product module',
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
                env=dict(os.environ, **{'LT73_MODE': mode,
                                        'LT73_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
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
        assert b[mode]['passed'] is EXPECT[mode][0], ('before pass', mode)
        assert a[mode]['passed'] is EXPECT[mode][1], ('after pass', mode)
        assert a[mode]['outcome'] == ROWS[mode], ('after rows', mode, a[mode]['outcome'])
    # The Lunal behaviour is unchanged by the correction.
    assert b['dagger']['outcome'] == a['dagger']['outcome'] == ROWS['dagger']
    assert b['dagger-munchkin']['outcome'] == {'walks_to_item': 0}  # config gate skipped it too
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
