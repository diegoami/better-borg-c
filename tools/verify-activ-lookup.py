#!/usr/bin/env python3
"""Verify source260 with the unchanged native fixture on actual product cores.

The ACID_BOLT3 and DISP_ALL maneuvers looked up the wrong activation ids, so
the greater-bolt and all-monsters-dispel items were never considered.
borg-fight-attack.c already carries 0011/0013/0014/0016, so provenance is
proven by applying the source two-token diff to the before module and
comparing bytes.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
eighteen-carry tree (normal and ASan), which lacks only this fix.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BEFORE = 'd29f373e5540a54c49fec10c10d48329a4bf26dc'
FIX = '891d0cb9cc9057a2004dfeba7b21b19913f5a2b6'
EVIDENCE = 'f0e856241'
PREFIX = 'docs/audit/c-reports/activ-260/'
SOURCE = 'src/borg/borg-fight-attack.c'
MODES = ('miswired', 'control')
ASAN_OPTIONS = 'detect_leaks=0:intercept_strcmp=0'

REPLACEMENTS_UNIQUE = [
    (b'            act_dispel_undead, rad, dam, BORG_ATTACK_DISP_ALL, false, -1));',
     b'            act_dispel_all, rad, dam, BORG_ATTACK_DISP_ALL, false, -1));'),
]
# The acid line appears twice (correctly in BF_ACT_ACID_BOLT2 and miswired in
# BF_ACT_ACID_BOLT3); only the second occurrence changes.
ACID_OLD = b'            act_acid_bolt2, rad, dam, BORG_ATTACK_ACID, true, -1));'
ACID_NEW = b'            act_acid_bolt3, rad, dam, BORG_ATTACK_ACID, true, -1));'


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
    # the product module; the dispel id is unique, the acid id's second
    # occurrence (inside BF_ACT_ACID_BOLT3) is the miswired one.
    before_module = read(BEFORE, SOURCE)
    layered = before_module
    for old, new in REPLACEMENTS_UNIQUE:
        assert before_module.count(old) == 1
        layered = layered.replace(old, new)
    assert before_module.count(ACID_OLD) == 2
    first = before_module.find(ACID_OLD)
    second = before_module.find(ACID_OLD, first + 1)
    layered = layered[:second] + ACID_NEW + layered[second + len(ACID_OLD):]
    assert layered.count(ACID_NEW) == 1
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
                                    env=dict(os.environ, A260_MODE=mode, A260_PROFILE=str(out / 'profile'),
                                             ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/activ-260 finished: 1/1 passed' in text,
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
    a, b = cases['normal-before']['miswired'], cases['normal-after']['miswired']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome']['bolt3'] == 0 and a['outcome']['bolt2'] == 0
    assert b['outcome']['bolt3'] > 0 and b['outcome']['bolt2'] == 0
    a, b = cases['normal-before']['control'], cases['normal-after']['control']
    assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
    assert a['log_sha256'] == b['log_sha256'], 'control changed'
    assert b['outcome']['bolt2'] > 0
    for phase in ('asan-before', 'asan-after'):
        a = cases[phase]['miswired']
        expected_pass = phase == 'asan-after'
        assert a['exit'] == 0 and a['passed'] == expected_pass and not a['asan'], phase
        row = cases[phase]['control']
        assert row['exit'] == 0 and row['passed'] and not row['asan'], phase
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
