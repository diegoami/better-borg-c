#!/usr/bin/env python3
"""Verify source325 with the unchanged native fixture and LeakSanitizer.

calculations_free() zeroed the count but retained the backing pointer array;
the next parse at count zero overwrote that pointer with a fresh allocation.
The unchanged fixture checks the retained pointer and reload result, while
LeakSanitizer identifies the overwritten calculation-array allocation by its
adjacent borg_array_add/parse_calculation_line stack. Sibling operator/token
leaks must remain visible and are owned by source324/source323.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
twenty-five-carry tree, which lacks only this fix.
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
BEFORE = '7f4c9e7ae92aeed5add7ab672f6c2717dc925189'
FIX = '253ab11468bd91f47f2a458ecc3f333a00eaa677'
EVIDENCE = '8764d94b8'
PREFIX = 'docs/audit/c-reports/calcreload-325/'
SOURCE = 'src/borg/borg-formulas-calc.c'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome(text):
    match = re.search(r'OUTCOME (.*)', text)
    return {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])} if match else {}


def leak_rows(text):
    blocks = text.split('Direct leak of ')[1:]

    def stack_has(block, *names):
        return all(name in block for name in names)

    def adjacent(block):
        return re.search(
            r'in borg_array_add [^\n]*\n\s+#\d+ 0x[0-9a-f]+ in parse_calculation_line',
            block) is not None

    summary = re.search(r'SUMMARY: AddressSanitizer: (.*)', text)
    return {
        'summary': summary[1] if summary else 'no leaks reported',
        'calc_array_leak': any(adjacent(block) for block in blocks),
        'operator_block_leaks': sum(
            'in adjust_order_ops_depth_block' in block for block in blocks),
        'token_array_leaks': sum('in tokenize_math' in block for block in blocks),
    }


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
        (d / 'src/borg/borg-formulas-calc.c').write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / 'src/borg/borg-formulas-calc.c').read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered

    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    for core in (asan, before_asan):
        flags = (core / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
        assert '-fsanitize=address' in flags
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
        modes = ('reload',) if phase.startswith('asan') else ('reload', 'control')
        for mode in modes:
            env = dict(os.environ, T325_MODE=mode, LC_ALL='C.UTF-8')
            if phase.startswith('asan'):
                env['ASAN_OPTIONS'] = 'detect_leaks=1'
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game', env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {
                'exit': result.returncode,
                'passed': 'native-c/calcreload-325 finished: 1/1 passed' in text,
                'outcome': outcome(text),
                'log_sha256': sha(log),
            }
            if phase.startswith('asan'):
                row['leaks'] = leak_rows(text)
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
    a, b = cases['normal-before']['reload'], cases['normal-after']['reload']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert a['outcome'] == {'retained': 1, 'reload_value': 7, 'reload_count': 1}
    assert b['outcome'] == {'retained': 0, 'reload_value': 7, 'reload_count': 1}
    a, b = cases['normal-before']['control'], cases['normal-after']['control']
    assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
    assert a['outcome'] == b['outcome'] == {'control_value': 3, 'control_count': 1}
    assert a['log_sha256'] == b['log_sha256'], 'single-parse control changed'

    a = cases['asan-before']['reload']
    b = cases['asan-after']['reload']
    assert not a['passed'] and b['passed']
    assert a['outcome']['retained'] == 1 and b['outcome']['retained'] == 0
    assert a['leaks']['calc_array_leak'], 'original calculation-array leak not identified'
    assert not b['leaks']['calc_array_leak'], 'corrected calculation-array leak remains'
    for sibling in ('operator_block_leaks', 'token_array_leaks'):
        assert a['leaks'][sibling] > 0 and b['leaks'][sibling] > 0, sibling
        assert a['leaks'][sibling] == b['leaks'][sibling], sibling
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
