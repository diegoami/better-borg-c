#!/usr/bin/env python3
"""Verify source213 with the unchanged native fixture on actual product cores.

borg_update_map()'s Floors branch is dead: the 2023 reorg mistranslated
the original borg's FEAT_FLOOR case as FEAT_NONE, so the branch's
dark/glow marking never executes. The correction restores the
FEAT_FLOOR condition and reads the glow state via square_islit() — the
grid's permanent-glow flag matching the original CAVE_GLOW test (the
transcribed g.lighting == LIGHTING_LIT would have been wrong even if
reached). The unchanged fixture drives the production update pass once
in a permanently glowing arena: before, distant and adjacent glowing
floors are unflagged (the require(near) fails); after, both are flagged
BORG_GLOW, the perm wall stays unflagged, and the flow-toward-light
consumer sees 484 targets. borg-update.c already carries 0039/0046, so
provenance is proven by applying the source diff to the before module
and comparing bytes.

Before builds are this tree's own pre-fix cores (source origin/main
2f4d62e4f, copied aside before the fix was applied), so they are
input-identical to current main including the interleaved flowcache
carry. The sanitized phases report the pre-existing init-time
borg_sort_comp_hook overflow (source finding #399, separately filed) in
every phase — expected, and asserted as such rather than suppressed.
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
BEFORE = '2f4d62e4fd3450196ed14c4f20c1d15486dea851'
FIX = '6c00db351c3edaabd708294bd9b702b07f66cb4c'
EVIDENCE = '5e6f2ddb5296922905ad47207ed6dcc166ff3233'
PIN = '5edc188e4e37c4ccf351dd5657b83bc5f1167244'
PREFIX = 'docs/audit/c-reports/glowtrace-213/'
SOURCE = 'src/borg/borg-update.c'
MODES = ('main',)
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
    fixture_identity = subprocess.run(
        ['git', 'diff', '--exit-code', PIN, EVIDENCE, '--',
         PREFIX + 'scenario.c', PREFIX + 'borg.txt', PREFIX + 'profile'],
        cwd=ROOT, capture_output=True)
    assert fixture_identity.returncode == 0, 'runtime fixtures changed since the run pin'
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
                env=dict(os.environ, GLOW213_PROFILE=str(out / 'profile'),
                         ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            smatch = re.search(r'STATE (.*)', text)
            omatch = re.search(r'OUTCOME (.*)', text)
            row = {
                'exit': result.returncode,
                'passed': 'native-c/glowtrace-213 finished: 1/1 passed' in text,
                'asan': 'AddressSanitizer' in text,
                'state': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', smatch[1])} if smatch else {},
                'outcome': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch[1])} if omatch else {},
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
    a, b = cases['normal-before']['main'], cases['normal-after']['main']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['state']['distant_glow'] == 0 and a['state']['near_glow'] == 0 \
        and a['state']['wall_glow'] == 0
    assert b['state']['distant_glow'] == 1 and b['state']['near_glow'] == 1 \
        and b['state']['wall_glow'] == 0
    for row in (a, b):
        assert row['state']['marked'] == 1 and row['state']['lit'] == 1 \
            and row['state']['pcmem'] == 1
    assert a['outcome'] == {} and b['outcome'] == {'glow_n': 484}
    for phase in ('asan-before', 'asan-after'):
        expected = {'main': phase == 'asan-after'}
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
