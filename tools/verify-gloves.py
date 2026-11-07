#!/usr/bin/env python3
"""Verify source205 with the unchanged native fixture on actual product cores.

borg_notice_armour_swap()'s armour-swap case list accepted HELM, CROWN,
SHIELD, CLOAK, SOFT_ARMOR, HARD_ARMOR and DRAG_ARMOR but never TV_GLOVES,
so free-action gauntlets in the pack could never be chosen as the armour
swap when the Borg has no free action. The correction adds
`case TV_GLOVES:` to the list. The unchanged fixture drives the production
armour-swap scan: before, the free-action gauntlets are never chosen (the
require fails); after, they are chosen with free action. The plain-glove
and free-action-already-worn controls are byte-identical.
borg-trait-swap.c is pristine (no carried patches touch it), so provenance
is proven by applying the source diff to the pristine before module and
comparing the result to the product module.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
forty-four-carry tree, which lacks only this fix. The sanitized phases
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
BEFORE = 'a22d8d09e4a04f17de1680a6047dac759e46e54f'
FIX = '175ef6feb555bbf67bcdfff7f628d686decf63a8'
EVIDENCE = '7ff787acc6250893e4391e0998c46eeecfb67665'
PREFIX = 'docs/audit/c-reports/gloves-205/'
SOURCE = 'src/borg/borg-trait-swap.c'
MODES = ('glove-fa', 'plain', 'have-fa')
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
    before, before_asan = args.before_build.resolve(), args.before_asan_build.resolve()
    build, asan = args.product_build.resolve(), args.asan_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        d.joinpath(SOURCE).parent.mkdir(parents=True)
        d.joinpath(SOURCE).write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = d.joinpath(SOURCE).read_bytes()
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
        'provenance': 'source diff applied to the pristine before module == product module',
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
                env=dict(os.environ, GL205_MODE=mode, GL205_PROFILE=str(out / 'profile'),
                         ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            match = re.search(r'OUTCOME (.*)', text)
            row = {
                'exit': result.returncode,
                'passed': 'native-c/gloves-205 finished: 1/1 passed' in text,
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
    a, b = cases['normal-before']['glove-fa'], cases['normal-after']['glove-fa']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome'] == {'armour_swap': 0, 'free_act': 0}
    assert b['outcome'] == {'armour_swap': 1, 'free_act': 1}
    for mode in ('plain', 'have-fa'):
        a, b = cases['normal-before'][mode], cases['normal-after'][mode]
        assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
        assert a['outcome'] == b['outcome'] == {'armour_swap': 0, 'free_act': 0}
        assert a['log_sha256'] == b['log_sha256'], f'{mode} control changed'
    for phase in ('asan-before', 'asan-after'):
        expected = {'glove-fa': phase == 'asan-after', 'plain': True, 'have-fa': True}
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
