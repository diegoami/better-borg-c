#!/usr/bin/env python3
"""Verify source253 with the unchanged native fixture on actual product cores.

The arc angle test reoriented the spell target instead of the scanned grid,
so every grid received the same angle difference and an arc spell was
valued as hitting everything in range and LOS. borg-fight-attack.c already
carries 0011 (missile) and 0013 (dispel), so provenance is proven by
applying the source two-token diff to the before module and comparing
bytes. The fixture contract is relational (reference measured with the
bystander's kill hidden), robust to carried danger corrections.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
thirteen-carry tree (normal and ASan), which lacks only this fix.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BEFORE = '9e31b9aa0d3f0ae37aab96377a4416b78c2187ef'
FIX = '7f33e9fbf83059a0a1ed5e530f463124ce1e4be0'
EVIDENCE = '6f1f66446'
PREFIX = 'docs/audit/c-reports/arc-253/'
SOURCE = 'src/borg/borg-fight-attack.c'
MODES = ('arc-bystander', 'arc-both')
ASAN_OPTIONS = 'detect_leaks=0:intercept_strcmp=0'

OLD_BLOCK = b'''            n2y = y - y1 + 20;
            n2x = x - x1 + 20;'''
NEW_BLOCK = b'''            n2y = ry - y1 + 20;
            n2x = rx - x1 + 20;'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-asan-build', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--asan-build', default=ROOT / 'build/asan', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()
    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)
    for name in ('scenario.c', 'borg.txt'):
        target = out / ('profile/borg.txt' if name == 'borg.txt' else name)
        target.write_bytes(read(EVIDENCE, PREFIX + name))
    before, before_asan = args.before_build.resolve(), args.before_asan_build.resolve()
    build, asan = args.product_build.resolve(), args.asan_build.resolve()

    # Layered provenance: before module + the source two-token diff equals
    # the product module, and the misoriented lines occur exactly once.
    before_module = read(BEFORE, SOURCE)
    assert before_module.count(OLD_BLOCK) == 1
    layered = before_module.replace(OLD_BLOCK, NEW_BLOCK)
    assert (ROOT / SOURCE).read_bytes() == layered

    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    for core in (asan, before_asan):
        flags = (core / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
        assert '-fsanitize=address' in flags
    report = {'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'), 'fix': FIX,
              'layered_provenance': 'before module + source two-token diff == product module',
              'before_commit': BEFORE, 'before_native_gate': before_gate,
              'before_binary_sha256': sha(before / 'game/angband'),
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': sha(build / 'game/angband'), 'asan_options': ASAN_OPTIONS,
              'phases': {}, 'verified': False}
    for phase, core in (('normal-before', before), ('normal-after', build),
                        ('asan-before', before_asan), ('asan-after', asan)):
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'src/tests')]
        if phase.startswith('asan'):
            command += ['-fsanitize=address', '-fno-omit-frame-pointer']
        command += [str(out / 'scenario.c'), *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run([str(binary), '-v'], cwd=build / 'game',
                                    env=dict(os.environ, A253_MODE=mode, A253_PROFILE=str(out / 'profile'),
                                             ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/arc-253 finished: 1/1 passed' in text,
                   'asan': 'AddressSanitizer' in text,
                   'log_sha256': sha(log)}
            match = re.search(r'OUTCOME (.*)', text)
            if match:
                row['outcome'] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])}
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary),
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    cases = {phase: data['cases'] for phase, data in report['phases'].items()}
    a, b = cases['normal-before']['arc-bystander'], cases['normal-after']['arc-bystander']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome']['value'] > a['outcome']['reference']
    assert b['outcome']['value'] == b['outcome']['reference']
    assert b['outcome']['reference'] > 0
    a, b = cases['normal-before']['arc-both'], cases['normal-after']['arc-both']
    assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
    assert a['log_sha256'] == b['log_sha256'], 'arc-both control changed'
    assert b['outcome']['value'] > b['outcome']['reference']
    for phase in ('asan-before', 'asan-after'):
        a = cases[phase]['arc-bystander']
        expected_pass = phase == 'asan-after'
        assert a['exit'] == 0 and a['passed'] == expected_pass and not a['asan'], phase
        row = cases[phase]['arc-both']
        assert row['exit'] == 0 and row['passed'] and not row['asan'], phase
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
