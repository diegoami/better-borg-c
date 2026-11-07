#!/usr/bin/env python3
"""Verify source323 with the unchanged native fixture and LeakSanitizer.

calculations_free() released calculation structs without their token-list
backing arrays. Functional logs are identical before and after; the proof is
the stack-attributed token-array leak disappearing. The layered before build
already carries opblock-324, so its expected baseline is 80 bytes/1 token
allocation (not the pristine source baseline of 160/2), and the operator leak
count must remain zero. borg-formulas-calc.c carries 0026/0033; provenance is
proven by applying the source diff to the before module.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
thirty-three-carry tree, which lacks only this fix.
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
BEFORE = '4ea7f7614d60bb2d47c53c608f7c552cf41fda05'
FIX = '2b98c831ba7b3f53b05ddcf620b8b2c54f5ed6a3'
EVIDENCE = '0799d463'
PREFIX = 'docs/audit/c-reports/calfree-323/'
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
        'cross_carry_interaction': 'opblock-324 already carried: 80 bytes/1 token allocation -> no leaks',
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
        modes = ('free',) if phase.startswith('asan') else ('free', 'control')
        for mode in modes:
            env = dict(os.environ, T323_MODE=mode, LC_ALL='C.UTF-8')
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
                'passed': 'native-c/calfree-323 finished: 1/1 passed' in text,
                'outcome': outcome(text),
                'log_sha256': sha(log),
            }
            if phase.startswith('asan'):
                blocks = text.split('Direct leak of ')[1:]
                summary = re.search(r'SUMMARY: AddressSanitizer: (.*)', text)
                row['leaks'] = {
                    'summary': summary[1] if summary else 'no leaks reported',
                    'token_array_leaks': sum('in tokenize_math' in block for block in blocks),
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
    for mode, expected in (('free', {'freed_value': 3, 'freed_count': 0}),
                           ('control', {'control_value': 42, 'control_count': 1})):
        a, b = cases['normal-before'][mode], cases['normal-after'][mode]
        assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
        assert a['outcome'] == b['outcome'] == expected
        assert a['log_sha256'] == b['log_sha256'], mode + ' functional log changed'
    a = cases['asan-before']['free']
    b = cases['asan-after']['free']
    assert a['passed'] and b['passed']
    assert a['outcome'] == b['outcome'] == {'freed_value': 3, 'freed_count': 0}
    assert a['leaks']['summary'] == '80 byte(s) leaked in 1 allocation(s).'
    assert a['leaks']['token_array_leaks'] == 1
    assert a['leaks']['operator_block_leaks'] == 0, 'carried opblock fix regressed'
    assert b['leaks']['summary'] == 'no leaks reported'
    assert b['leaks']['token_array_leaks'] == 0
    assert b['leaks']['operator_block_leaks'] == 0 and b['exit'] == 0
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
