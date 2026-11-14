#!/usr/bin/env python3
"""Verify source122: remove the unreachable visible-trap case from dark-flow exploration (fix b53fa471a).

borg_flow_dark_interesting() returns early for every grid below
FEAT_SECRET except closed doors.  Its "Explore visible traps" case tests
feat_is_trap_holding(ag->feat), and in the stock terrain data only the
open floor carries the TRAP flag.  The floor is below FEAT_SECRET, so the
test is never reached with a grid it could accept, and the borg keeps
known traps in ag->trap rather than in the feature anyway.

Delete the case and the "visible trap" wording in the function comment.
No behaviour change: traps lying on a chosen route are still checked by
the flow spread and disarmed by the step code.

The kit is the source lane's unchanged native-c/trapdead-122 fixture.  Every mode passes in both phases with the
recorded outcome rows; known, unknown, door are byte-identical before and after.

Run under the shared native lock after this tree's gate build, with the
before snapshot built at the before commit (its gate result recorded under
--before-gate).
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
BEFORE = 'a5582047f3b38dd06b46291184ce7e00754443d4'
FIX = 'b53fa471a59305abf4061ca5b3dc8ea3f812cc7a'
FIX_BASE = 'e473720ed88a0f0c7ca66815cef3000eb4a38bc3'
EVIDENCE = 'a5582047f3b38dd06b46291184ce7e00754443d4'
PREFIX = 'docs/audit/c-reports/trapdead-122/'
SOURCE = 'src/borg/borg-flow-dark.c'
MODES = ('known', 'unknown', 'door')
SUITE = 'native-c/trapdead-122'
EXPECT = {m: (True, True) for m in MODES}
ROWS = {"known": {"flowed": 0, "key": 0, "step_x": -1, "step_y": -1, "step_is_trap": 0}, "unknown": {"flowed": 1, "key": 68, "step_x": 11, "step_y": 12, "step_is_trap": 1}, "door": {"flowed": 1, "key": 52, "step_x": 9, "step_y": 12, "step_is_trap": 0}}
BEFORE_ROWS = ROWS


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

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX_BASE, FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / SOURCE).parent.mkdir(parents=True)
        (d / SOURCE).write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / SOURCE).read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered, 'product module != before + source diff'
    fix_scope = subprocess.check_output(
        ['git', 'diff', '--name-only', FIX_BASE, FIX, '--', 'src', 'lib',
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
        'fixture_commit': evidence,
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
                env=dict(os.environ, **{'TD122_MODE': mode,
                                        'TD122_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            outcome = {}
            for omatch in re.findall(r'OUTCOME (.*)', text):
                outcome.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch)})
            rows[mode] = {
                'exit': result.returncode,
                'passed': SUITE + ' finished: 1/1 passed' in text,
                'outcome': outcome,
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
        assert b[mode]['outcome'] == BEFORE_ROWS[mode], ('before rows', mode, b[mode]['outcome'])
        assert a[mode]['outcome'] == ROWS[mode], ('after rows', mode, a[mode]['outcome'])
    for mode in ('known', 'unknown', 'door'):
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], ('control changed', mode)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
