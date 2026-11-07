#!/usr/bin/env python3
"""Verify source212 with the unchanged native fixture on actual product cores.

In borg_update_map() the old_wall capture ran AFTER the grid's feature had
already been overwritten with what the game shows now, so the wall-change
comparison compared the new feature against itself and never detected a
change: stale flow data, stone-to-mud knowledge, icky detection flags and
their timestamps survived a grid changing under the Borg. The correction
moves the capture before the overwrite. The unchanged fixture plants the
tracked state (flow=50, know/icky, both stamps), changes the watched
grid's feature between two production map passes, and reads the state
back: before, door-close and door-open keep everything stale (the
invalidation requires fail); after, door-close invalidates fully
(flow=255) and door-open clears knowledge/icky and the stamps while
keeping the flow value. The no-change control is byte-identical.
borg-update.c already carries 0018, so provenance is proven by applying
the source diff to the before module and comparing bytes.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
thirty-eight-carry tree, which lacks only this fix.
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
BEFORE = '21fbfba5c4d3a2cc77707fea885590479cec18c3'
FIX = '641234dbd3e5d661e911e810e55df991a3a3a9b3'
EVIDENCE = '9fe10e42709c480e7b09c8472f9205b9281d6a1c'
PREFIX = 'docs/audit/c-reports/mapwall-212/'
SOURCE = 'src/borg/borg-update.c'
MODES = ('door-close', 'door-open', 'no-change')
ASAN_OPTIONS = 'detect_leaks=0:intercept_strcmp=0'


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

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / 'src/borg').mkdir(parents=True)
        (d / 'src/borg/borg-update.c').write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / 'src/borg/borg-update.c').read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered

    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    for core in (asan, before_asan):
        flags = (core / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
        assert '-fsanitize=address' in flags
        assert (core / 'CMakeFiles/OurUnitTestLib.dir/src/tests/unit-test.c.o').exists()
    report = {
        'fixture_commit': EVIDENCE,
        'fixture_sha256': sha(out / 'scenario.c'),
        'fix': FIX,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE,
        'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'product_binary_sha256': sha(build / 'game/angband'),
        'asan_options': ASAN_OPTIONS,
        'phases': {},
        'verified': False,
    }
    for phase, core in (('normal-before', before), ('normal-after', build),
                        ('asan-before', before_asan), ('asan-after', asan)):
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                   '-I' + str(ROOT / 'src/tests')]
        if phase.startswith('asan'):
            command += ['-fsanitize=address', '-fno-omit-frame-pointer']
        command += [str(out / 'scenario.c'), *map(str, objects + helpers),
                    '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, MW212_MODE=mode, MW212_PROFILE=str(out / 'profile'),
                         ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            match = re.search(r'OUTCOME (.*)', text)
            row = {
                'exit': result.returncode,
                'passed': 'native-c/mapwall-212 finished: 1/1 passed' in text,
                'asan': 'AddressSanitizer' in text,
                'outcome': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])} if match else {},
                'log_sha256': sha(log),
            }
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {
            'cases': rows,
            'command': command,
            'binary_sha256': sha(binary),
            'objects_sha256': {str(o): sha(o) for o in objects + helpers},
        }
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    cases = {phase: data['cases'] for phase, data in report['phases'].items()}
    a, b = cases['normal-before']['door-close'], cases['normal-after']['door-close']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome'] == {'invalidated': 0, 'flow255': 0}
    assert b['outcome'] == {'invalidated': 1, 'flow255': 1}
    a, b = cases['normal-before']['door-open'], cases['normal-after']['door-open']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome'] == {'invalidated': 0, 'flow255': 0}
    assert b['outcome'] == {'invalidated': 1, 'flow255': 0}
    a, b = cases['normal-before']['no-change'], cases['normal-after']['no-change']
    assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
    assert a['outcome'] == b['outcome'] == {'invalidated': 0, 'flow255': 0}
    assert a['log_sha256'] == b['log_sha256'], 'no-change control changed'
    for phase in ('asan-before', 'asan-after'):
        for mode in ('door-close', 'door-open'):
            row = cases[phase][mode]
            expected_pass = (phase == 'asan-after')
            assert row['exit'] == 0 and row['passed'] == expected_pass and not row['asan'], (phase, mode)
        row = cases[phase]['no-change']
        assert row['exit'] == 0 and row['passed'] and not row['asan'], phase
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
