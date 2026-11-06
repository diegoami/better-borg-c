#!/usr/bin/env python3
"""Verify source254 with the unchanged native fixture on actual product cores.

The launch probe's dead `b_n < 0` guard (b_n initializes to zero) let a
targetless borg_attack_aux_launch() read borg_items[-1].desc and queue a
fire key plus a quiver character from index -1. The one-guard import keeps
the real target and simulated controls byte-identical.

Run under the shared native lock after the normal gate build and a fully
ASan-instrumented core build (CMAKE_C_FLAGS='-fsanitize=address
-fno-omit-frame-pointer -g'). Before-ASan replaces only the attack object
with the pre-fix source, compiled with the ASan build's recorded flags.
No normal object/source changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BEFORE = 'b72ad8eae676ba7c2b9d90026eb0e2d4a2468540'
FIX = '405e4fd4880e7bef27d6a6328765a904638c8257'
EVIDENCE = '8b30eb584'
PREFIX = 'docs/audit/c-reports/missile-254/'
SOURCE = 'src/borg/borg-fight-attack.c'
MODES = ('no-target', 'live-shot', 'simulated')
ASAN_OPTIONS = 'detect_leaks=0:intercept_strcmp=0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
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
    before, build, asan = args.before_build.resolve(), args.product_build.resolve(), args.asan_build.resolve()
    assert (ROOT / SOURCE).read_bytes() == read(FIX, SOURCE)
    assert (before.parents[1] / SOURCE).read_bytes() == read(BEFORE, SOURCE)
    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    flags = (asan / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
    assert '-fsanitize=address' in flags
    tokens = []
    for variable in ('C_DEFINES', 'C_INCLUDES', 'C_FLAGS'):
        tokens += shlex.split(re.search(r'^' + variable + r' = (.*)$', flags, re.MULTILINE)[1])
    old_source, old_object = out / 'before-attack.c', out / 'before-attack-asan.o'
    old_source.write_bytes(read(BEFORE, SOURCE))
    compile_command = ['cc', *tokens, '-I' + str(ROOT / 'src/borg'), '-c', str(old_source), '-o', str(old_object)]
    with (out / 'before-asan-compile.log').open('w') as log:
        subprocess.run(compile_command, stdout=log, stderr=subprocess.STDOUT, check=True)
    report = {'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'), 'fix': FIX,
              'before_commit': BEFORE, 'before_native_gate': before_gate,
              'before_binary_sha256': sha(before / 'game/angband'),
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': sha(build / 'game/angband'), 'asan_options': ASAN_OPTIONS,
              'before_asan_compile_command': compile_command, 'phases': {}, 'verified': False}
    for phase, core in (('normal-before', before), ('normal-after', build),
                        ('asan-before', asan), ('asan-after', asan)):
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        if phase == 'asan-before':
            replaced = [o for o in objects if o.as_posix().endswith(SOURCE + '.o')]
            assert len(replaced) == 1
            objects = [old_object if o == replaced[0] else o for o in objects]
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
                                    env=dict(os.environ, M254_MODE=mode, M254_PROFILE=str(out / 'profile'),
                                             ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/missile-254 finished: 1/1 passed' in text,
                   'asan': 'AddressSanitizer' in text,
                   'log_sha256': sha(log),
                   'target_read_report': all(s in text for s in ('heap-buffer-overflow', 'READ of size',
                                                                 'borg_attack_aux_launch'))}
            for tag, key in (('DECISION', 'decision'), ('OUTCOME', 'outcome')):
                match = re.search(re.escape(tag) + r' (.*)', text)
                if match:
                    row[key] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])}
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary),
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    cases = {phase: data['cases'] for phase, data in report['phases'].items()}
    a, b = cases['normal-before']['no-target'], cases['normal-after']['no-target']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert (a['outcome']['return'], a['outcome']['keys']) == (0, 3)
    assert (b['outcome']['return'], b['outcome']['keys']) == (0, 0)
    for mode in ('live-shot', 'simulated'):
        a, b = cases['normal-before'][mode], cases['normal-after'][mode]
        assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
        assert a['log_sha256'] == b['log_sha256'], mode
    a = cases['asan-before']['no-target']
    assert a['exit'] != 0 and not a['passed'] and a['target_read_report']
    for mode in ('live-shot', 'simulated'):
        a = cases['asan-before'][mode]
        assert a['exit'] == 0 and a['passed'] and not a['asan'], mode
    for mode, row in cases['asan-after'].items():
        assert row['exit'] == 0 and row['passed'] and not row['asan'], mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
