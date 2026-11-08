#!/usr/bin/env python3
"""Verify source310 with the unchanged native fixture on actual product cores.

borg_recall()'s endgame branch — BI_MAXDEPTH == 99 with fewer than five
live uniques, cleaning up the last uniques to hit Morgoth — answered the
recall-depth reset prompt with 'n' ("# Not Resetting recall depth.")
while its own comment says "Do reset Depth"; the generic branch answers
'y'. The correction answers 'y' ("# Resetting recall depth."), matching
the comment and the generic path. The unchanged fixture drives the
production decision (curdepth 65 = hunted-out maxdepth, 2 live uniques):
before, the endgame keys end in 'n' (the clear require !keep_n fails
while the controls pass); after, they end in 'y'. The generic
(curdepth = maxdepth) and mismatch (curdepth != hunted) controls are
byte-identical. borg-escape.c carries no earlier corrections, so
provenance is proven by applying the source diff to the before module
and comparing bytes.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
forty-seven-carry tree, which lacks only this fix. The sanitized phases
report the pre-existing init-time borg_sort_comp_hook overflow (source
finding #399, separately filed) in every phase — expected, and asserted
as such rather than suppressed.
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
BEFORE = 'c61e90c9cdfb466336d3f564a1a3709f3daecc65'
FIX = 'b00f2a1901091b8a3222dc5576638684b36d95ea'
EVIDENCE = '1f0425e12e9af9e31b15a0973aa8e805fe44c240'
PREFIX = 'docs/audit/c-reports/recalldepth-310/'
SOURCE = 'src/borg/borg-escape.c'
MODES = ('endgame', 'generic', 'mismatch')
ASAN_OPTIONS = 'halt_on_error=0:detect_leaks=0'


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
    receipt = json.loads(read(EVIDENCE, PREFIX + 'receipt.json'))
    for name in ('scenario.c', 'borg.txt'):
        assert sha(out / ('profile/borg.txt' if name == 'borg.txt' else name)) \
            == receipt['sha256'][name], name
    before, before_asan = args.before_build.resolve(), args.before_asan_build.resolve()
    build, asan = args.product_build.resolve(), args.asan_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / 'src/borg').mkdir(parents=True)
        (d / 'src/borg/borg-escape.c').write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / 'src/borg/borg-escape.c').read_bytes()
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
            command += ['-fsanitize=address', '-fsanitize-recover=address',
                        '-fno-omit-frame-pointer']
        command += [str(out / 'scenario.c'), *map(str, objects + helpers),
                    '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, RD310_MODE=mode, RD310_PROFILE=str(out / 'profile'),
                         ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            match = re.search(r'OUTCOME (.*)', text)
            row = {
                'exit': result.returncode,
                'passed': 'native-c/recalldepth-310 finished: 1/1 passed' in text,
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
    a, b = cases['normal-before']['endgame'], cases['normal-after']['endgame']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome'] == {'acted': 1, 'keys': 6, 'reset_y': 0, 'keep_n': 1}
    assert b['outcome'] == {'acted': 1, 'keys': 6, 'reset_y': 1, 'keep_n': 0}
    for mode, outcome in (('generic', {'acted': 1, 'keys': 6, 'reset_y': 1, 'keep_n': 0}),
                          ('mismatch', {'acted': 1, 'keys': 6, 'reset_y': 0, 'keep_n': 1})):
        a, b = cases['normal-before'][mode], cases['normal-after'][mode]
        assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
        assert a['outcome'] == b['outcome'] == outcome
        assert a['log_sha256'] == b['log_sha256'], (mode, 'control changed')
    for phase in ('asan-before', 'asan-after'):
        expected = {'endgame': phase == 'asan-after', 'generic': True, 'mismatch': True}
        for mode in MODES:
            row = cases[phase][mode]
            # Sanitized runs report the pre-existing init-time
            # borg_sort_comp_hook overflow (source #399, separately filed)
            # in every phase — asan=True is expected there; the pass/fail
            # contract and clean exit are what must hold.
            assert row['exit'] == 0 and row['passed'] == expected[mode], (phase, mode)
        assert all(cases[phase][md]['asan'] for md in MODES), 'expected #399 report missing'
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
