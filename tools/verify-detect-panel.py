#!/usr/bin/env python3
"""Verify source290 with the unchanged native fixture on actual product cores.

A queued detection self-reaction keeps pre-level-change panel offsets; on a
one-panel-high cave its mark indexes past the resized arrays — the original
crashes (SIGSEGV / ASan read at borg_handle_self). borg-update.c is
pristine in this product, so the imported module is byte-identical to the
reviewed source commit. Before-ASan replaces only the update object with
the pre-fix source, compiled with the ASan build's recorded flags.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
seventeen-carry tree (normal and ASan), which lacks only this fix.
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
BEFORE = '5667d085dcdef669a587c8e8153aa6cca8c20ecd'
FIX = '02fb00af6abdb165fc1b445c42dc85d2263a3cdd'
EVIDENCE = 'd9d4c7186'
PREFIX = 'docs/audit/c-reports/detect-290/'
SOURCE = 'src/borg/borg-update.c'
MODES = ('stale', 'fresh')
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

    # Module-identity provenance: the file is otherwise pristine.
    assert (ROOT / SOURCE).read_bytes() == read(FIX, SOURCE)
    assert read(BEFORE, SOURCE) == read(FIX + '^', SOURCE)

    # Pre-fix update object for the before-ASan phase.
    flags = (asan / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
    assert '-fsanitize=address' in flags
    tokens = []
    for variable in ('C_DEFINES', 'C_INCLUDES', 'C_FLAGS'):
        tokens += shlex.split(re.search(r'^' + variable + r' = (.*)$', flags, re.MULTILINE)[1])
    old_source, old_object = out / 'before-update.c', out / 'before-update-asan.o'
    old_source.write_bytes(read(BEFORE, SOURCE))
    compile_command = ['cc', *tokens, '-I' + str(ROOT / 'src/borg'), '-c', str(old_source), '-o', str(old_object)]
    with (out / 'before-asan-compile.log').open('w') as log:
        subprocess.run(compile_command, stdout=log, stderr=subprocess.STDOUT, check=True)

    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    flags2 = (before_asan / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
    assert '-fsanitize=address' in flags2
    report = {'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'), 'fix': FIX,
              'provenance': 'module byte-identical to the reviewed source commit (file otherwise pristine)',
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
                                    env=dict(os.environ, D290_MODE=mode, D290_PROFILE=str(out / 'profile'),
                                             ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/detect-290 finished: 1/1 passed' in text,
                   'asan': 'AddressSanitizer' in text,
                   'log_sha256': sha(log),
                   'target_read_report': all(s in text for s in ('heap-buffer-overflow', 'READ',
                                                                 'borg_handle_self'))}
            match = re.search(r'OUTCOME (.*)', text)
            if match:
                row['outcome'] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])}
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary),
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    cases = {phase: data['cases'] for phase, data in report['phases'].items()}
    a, b = cases['normal-before']['stale'], cases['normal-after']['stale']
    assert b['exit'] == 0 and b['passed'] and b['outcome']['last_row_mark'] == 0
    assert a['exit'] != 0 and not a['passed'], 'normal-before stale must crash or fail'
    a = cases['asan-before']['stale']
    assert a['exit'] != 0 and not a['passed'] and a['target_read_report']
    for phase in ('normal-before', 'normal-after', 'asan-before', 'asan-after'):
        row = cases[phase]['fresh']
        assert row['exit'] == 0 and row['passed'] and not row['asan'], (phase, 'fresh')
        assert row['outcome']['last_row_mark'] == 1, (phase, 'fresh')
    a, b = cases['normal-before']['fresh'], cases['normal-after']['fresh']
    assert a['log_sha256'] == b['log_sha256'], 'fresh control changed'
    row = cases['asan-after']['stale']
    assert row['exit'] == 0 and row['passed'] and not row['asan']
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
