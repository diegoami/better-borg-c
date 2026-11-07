#!/usr/bin/env python3
"""Verify source314 with the unchanged native fixture on actual product cores.

The production town stair-scum bail cleared lunal_mode but left fleeing_lunal
set, producing the split state the caution phase misreads. The correction
clears both flags; the full-pack bail must leave both set with identical logs.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
thirty-one-carry tree, which lacks only this fix.
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
BEFORE = 'b0cf47b1354918825d0c2c464b2460e85296e672'
FIX = 'a26da54d61be83236c2c5859141b801521d6c6d5'
EVIDENCE = 'd50baba7'
PREFIX = 'docs/audit/c-reports/lunal-314/'
SOURCE = 'src/borg/borg-think-dungeon-util.c'
MODES = ('town', 'pack')
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
        (d / 'src/borg/borg-think-dungeon-util.c').write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / 'src/borg/borg-think-dungeon-util.c').read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered

    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    for core in (asan, before_asan):
        flags = (core / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
        assert '-fsanitize=address' in flags
    report = {
        'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'),
        'fix': FIX,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE, 'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'product_binary_sha256': sha(build / 'game/angband'),
        'asan_options': ASAN_OPTIONS, 'phases': {}, 'verified': False,
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
                env=dict(os.environ, T314_MODE=mode, T314_PROFILE=str(out / 'profile'),
                         ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            match = re.search(r'OUTCOME (.*)', text)
            row = {
                'exit': result.returncode,
                'passed': 'native-c/lunal-314 finished: 1/1 passed' in text,
                'asan': 'AddressSanitizer' in text,
                'outcome': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])} if match else {},
                'log_sha256': sha(log),
            }
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {
            'cases': rows, 'command': command, 'binary_sha256': sha(binary),
            'objects_sha256': {str(o): sha(o) for o in objects + helpers},
        }
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    cases = {phase: data['cases'] for phase, data in report['phases'].items()}
    a, b = cases['normal-before']['town'], cases['normal-after']['town']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome'] == {'lunal_mode': 0, 'fleeing_lunal': 1}
    assert b['outcome'] == {'lunal_mode': 0, 'fleeing_lunal': 0}
    a, b = cases['normal-before']['pack'], cases['normal-after']['pack']
    assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
    assert a['outcome'] == b['outcome'] == {'lunal_mode': 1, 'fleeing_lunal': 1}
    assert a['log_sha256'] == b['log_sha256'], 'full-pack control changed'
    for phase in ('asan-before', 'asan-after'):
        a = cases[phase]['town']
        expected_pass = phase == 'asan-after'
        assert a['exit'] == 0 and a['passed'] == expected_pass and not a['asan'], phase
        row = cases[phase]['pack']
        assert row['exit'] == 0 and row['passed'] and not row['asan'], phase
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
