#!/usr/bin/env python3
"""Verify source248 with the unchanged native fixture on actual product cores.

The Dispel Life filter kept damage only for monsters flagged both nonliving
and undead — the inverse of the game's drain — so the spell was rated below
doing nothing against every enemy. borg-fight-attack.c already carries the
missile guard (0011), so provenance is proven by applying the source block
to the before module and comparing bytes.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
twelve-carry tree (normal and ASan), which lacks only this fix.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BEFORE = 'b287fa712da8f3355b432c25a0365b8fb2d8391e'
FIX = '6912b85cb7b902616ad786dfc20afe3b4cf28b10'
EVIDENCE = '6df50d2e'
PREFIX = 'docs/audit/c-reports/dispel-248/'
SOURCE = 'src/borg/borg-fight-attack.c'
MODES = ('living', 'undead', 'bolt')
ASAN_OPTIONS = 'detect_leaks=0:intercept_strcmp=0'

OLD_BLOCK = b'''    /*  Dispel life */
    case BORG_ATTACK_DRAIN_LIFE:
        if (!(rf_has(r_ptr->flags, RF_NONLIVING)))
            dam = 0;
        if (!(rf_has(r_ptr->flags, RF_UNDEAD)))
            dam = 0;
        break;
'''
NEW_BLOCK = b'''    /*  Dispel life: the game's drain only hurts living monsters
     * (nonliving is undead or nonliving). */
    case BORG_ATTACK_DRAIN_LIFE:
        if (rf_has(r_ptr->flags, RF_NONLIVING)
            || rf_has(r_ptr->flags, RF_UNDEAD))
            dam = 0;
        break;
'''


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
    (out / 'scenario.c').write_bytes((ROOT / 'tools/dispel-filter-scenario.c').read_bytes())
    (out / 'profile/borg.txt').write_bytes(read(EVIDENCE, PREFIX + 'borg.txt'))
    before, before_asan = args.before_build.resolve(), args.before_asan_build.resolve()
    build, asan = args.product_build.resolve(), args.asan_build.resolve()

    # Layered provenance: before module + the source filter block equals the
    # product module, and the inverted filter occurs exactly once.
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
    report = {'scenario_source': 'tools/dispel-filter-scenario.c',
              'scenario_sha256': sha(out / 'scenario.c'),
              'original_fixture_commit': EVIDENCE,
              'original_fixture_sha256': hashlib.sha256(read(EVIDENCE, PREFIX + 'scenario.c')).hexdigest(),
              'fixture_commit': EVIDENCE, 'fix': FIX,
              'layered_provenance': 'before module + source filter block == product module',
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
                                    env=dict(os.environ, D248_MODE=mode, D248_PROFILE=str(out / 'profile'),
                                             ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/dispel-248 finished: 1/1 passed' in text,
                   'asan': 'AddressSanitizer' in text,
                   'log_sha256': sha(log)}
            match = re.search(r'OUTCOME (.*)', text)
            if match:
                row['outcome'] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])}
            match = re.search(r'RATING (.*)', text)
            if match:
                row['rating'] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])}
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary),
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    cases = {phase: data['cases'] for phase, data in report['phases'].items()}
    a, b = cases['normal-before']['living'], cases['normal-after']['living']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome']['hp_lost'] == b['outcome']['hp_lost'] and b['outcome']['hp_lost'] > 0
    assert b['rating']['value'] > 0 and a['rating']['value'] <= 0
    for mode in ('undead', 'bolt'):
        a, b = cases['normal-before'][mode], cases['normal-after'][mode]
        assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed'], mode
        assert a['log_sha256'] == b['log_sha256'], mode
    u = cases['normal-after']['undead']
    assert u['outcome']['hp_lost'] == 0 and u['outcome']['undead'] == 1
    for phase in ('asan-before', 'asan-after'):
        a = cases[phase]['living']
        expected_pass = phase == 'asan-after'
        assert a['exit'] == 0 and a['passed'] == expected_pass and not a['asan'], phase
        for mode in ('undead', 'bolt'):
            row = cases[phase][mode]
            assert row['exit'] == 0 and row['passed'] and not row['asan'], (phase, mode)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
