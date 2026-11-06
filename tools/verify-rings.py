#!/usr/bin/env python3
"""Verify source78 on actual cores and both one-loop partial corrections.

Run under the shared lock after the normal native build. Partial variants compile
only a disposable replacement for the actual ring module, with its recorded
CMake flags; the task checkout and ordinary product objects are never modified.
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
EVIDENCE = 'bfe3fc402e8ae6cdec74d8b35fa8f50e612f2a8e'
FIX = '46c14b2828ed751ff8be7ac67df93b28cdc15f87'
SOURCE = 'src/borg/borg-item-use.c'
PREFIX = 'docs/audit/c-reports/CBUG-0062/'
MODES = ('left-ready', 'right-charging-left-ready', 'right-control', 'both-ready',
         'left-charging', 'no-ring', 'blind-control')
AFFECTED = MODES[:2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()
    def read(ref, path):
        return subprocess.check_output(['git', 'show', ref + ':' + path], cwd=ROOT)
    (out / 'scenario.c').write_bytes(read(EVIDENCE, PREFIX + 'scenario.c'))
    (out / 'profile/borg.txt').write_bytes(read(EVIDENCE, PREFIX + 'borg.txt'))
    original = read('e473720ed', SOURCE).decode()
    fixed = read(FIX, SOURCE).decode()
    old = 'for (i = INVEN_RIGHT; i < INVEN_LEFT; i++)'
    new = 'for (i = INVEN_RIGHT; i <= INVEN_LEFT; i++)'
    assert original.count(old) == 2 and original.replace(old, new) == fixed
    assert (ROOT / SOURCE).read_text() == fixed
    before, build = args.before_build.resolve(), args.product_build.resolve()
    assert (before.parents[1] / SOURCE).read_text() == original
    helpers = sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    assert helpers
    report = {'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'),
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': sha(build / 'game/angband'), 'phases': {}, 'verified': False}
    first, last = original.rsplit(old, 1)
    variants = {'detection-only': original.replace(old, new, 1), 'activation-only': first + new + last}
    for phase in ('before', 'detection-only', 'activation-only', 'after'):
        core = build if phase == 'after' else before
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        assert len(objects) >= 150
        compile_command = None
        if phase in variants:
            source = out / (phase + '.c')
            source.write_text(variants[phase])
            obj = out / (phase + '.o')
            flags = (before / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
            tokens = []
            for variable in ('C_DEFINES', 'C_INCLUDES', 'C_FLAGS'):
                tokens += shlex.split(re.search(r'^' + variable + r' = (.*)$', flags, re.MULTILINE)[1])
            compile_command = ['cc', *tokens, '-I' + str(ROOT / 'src/borg'), '-c', str(source), '-o', str(obj)]
            with (out / (phase + '-compile.log')).open('w') as log:
                subprocess.run(compile_command, stdout=log, stderr=subprocess.STDOUT, check=True)
            replaced = [o for o in objects if o.as_posix().endswith(SOURCE + '.o')]
            assert len(replaced) == 1
            objects = [obj if o == replaced[0] else o for o in objects]
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'src/tests'),
                   str(out / 'scenario.c'), *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            r = subprocess.run([str(binary), '-v'], cwd=build / 'game',
                               env=dict(os.environ, CBUG0062_MODE=mode, CBUG0062_PROFILE=str(out / 'profile'), LC_ALL='C.UTF-8'),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            text = re.sub(r'\x1b\[[0-9;]*m', '', r.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            outcome = re.search(r'^OUTCOME (.*)$', text, re.MULTILINE)
            row = {'exit': r.returncode, 'passed': 'native-c/CBUG-0062 finished: 1/1 passed' in text,
                   'completed': bool(outcome), 'log_sha256': sha(log)}
            if outcome:
                row.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', outcome[1])})
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'binary_sha256': sha(binary), 'command': command,
                                   'variant_compile_command': compile_command,
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    for phase, data in report['phases'].items():
        for mode, row in data['cases'].items():
            assert row['exit'] == 0 and row['completed'], (phase, mode)
            if mode in AFFECTED:
                if phase == 'after':
                    assert row['passed'] and row['activated'] and row['killed'] and row['enemy_after'] == 0
                else:
                    assert not row['passed'] and not row['activated'] and row['damage'] == 0
            else:
                baseline = report['phases']['before']['cases'][mode]
                assert row['passed'] and row['log_sha256'] == baseline['log_sha256'], (phase, mode)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
