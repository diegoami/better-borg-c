#!/usr/bin/env python3
"""Verify source324 with the unchanged native fixture and LeakSanitizer.

Precedence adjustment freed operator-block structs without their backing
pointer arrays. Functional formula logs are identical before and after; the
proof is the stack-attributed 160-byte/two-allocation leak disappearing.
borg-formulas-calc.c carries 0026, so provenance is proven by applying the
source diff to the before module.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
thirty-two-carry tree, which lacks only this fix.
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
BEFORE = '56f9d49595f1cd5504e6f1d92edb144f543c88ff'
FIX = '02be7739db306897f2441562ee8d27dddc15d36c'
EVIDENCE = '6cbb0347'
PREFIX = 'docs/audit/c-reports/opblock-324/'
SOURCE = 'src/borg/borg-formulas-calc.c'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome(text):
    match = re.search(r'OUTCOME (.*)', text)
    return {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])} if match else {}


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
        'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'),
        'fix': FIX,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE, 'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'product_binary_sha256': sha(build / 'game/angband'),
        'phases': {}, 'verified': False,
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
        modes = ('operators',) if phase.startswith('asan') else ('operators', 'control')
        for mode in modes:
            env = dict(os.environ, T324_MODE=mode, LC_ALL='C.UTF-8')
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
                'passed': 'native-c/opblock-324 finished: 1/1 passed' in text,
                'outcome': outcome(text),
                'log_sha256': sha(log),
            }
            if phase.startswith('asan'):
                blocks = text.split('Direct leak of ')[1:]
                summary = re.search(r'SUMMARY: AddressSanitizer: (.*)', text)
                row['leaks'] = {
                    'summary': summary[1] if summary else 'no leaks reported',
                    'operator_block_leaks': sum(
                        'in adjust_order_ops_depth_block' in block for block in blocks),
                }
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {
            'cases': rows, 'command': command, 'binary_sha256': sha(binary),
            'objects_sha256': {str(o): sha(o) for o in objects + helpers},
        }
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    cases = {phase: data['cases'] for phase, data in report['phases'].items()}
    for mode, expected in (('operators', {'formula_value': 7, 'calc_count': 1}),
                           ('control', {'control_value': 42, 'control_count': 1})):
        a, b = cases['normal-before'][mode], cases['normal-after'][mode]
        assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
        assert a['outcome'] == b['outcome'] == expected
        assert a['log_sha256'] == b['log_sha256'], mode + ' functional log changed'
    a = cases['asan-before']['operators']
    b = cases['asan-after']['operators']
    assert a['passed'] and b['passed']
    assert a['outcome'] == b['outcome'] == {'formula_value': 7, 'calc_count': 1}
    assert a['leaks']['summary'] == '160 byte(s) leaked in 2 allocation(s).'
    # LSan groups the two allocations into one Direct-leak report block.
    assert a['leaks']['operator_block_leaks'] == 1
    assert b['leaks']['summary'] == 'no leaks reported'
    assert b['leaks']['operator_block_leaks'] == 0 and b['exit'] == 0
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
