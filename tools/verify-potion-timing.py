#!/usr/bin/env python3
"""Verify source77 on actual product cores, retaining the incomplete alternative.

Run under the shared native lock. The simple alternative compiles a disposable
module with the before build's CMake flags; no normal object/source is mutated.
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
EVIDENCE = 'cce1d5d92079e78e939126d3cf35e24121442734'
FIX = 'cedf25eb790f2ff7c7c161cd1612b18ed99fb35e'
BEFORE = '24ba2be9e445f5f08e322ae97f65e5bdd3b4878b'
SOURCE = 'src/borg/borg-item-use.c'
PREFIX = 'docs/audit/c-reports/CBUG-0061/'
OLD = 'if (borg_timer(when_last_quaff) > 4 && borg_timer(when_last_quaff) > 0'
NEW = 'if (when_last_quaff && borg_timer(when_last_quaff) <= 4\n        && borg_timer(when_last_quaff) > 0'
CONTROLS = ('same-turn', 'bypass-control', 'reserve-control', 'empty-control', 'first-turn')
MODES = ('long-gap', 'recent', 'boundary-four', 'same-turn', 'bypass-control',
         'reserve-control', 'empty-control', 'first-use', 'first-turn')


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
    for name in ('scenario.c', 'run-cases.py', 'borg.txt'):
        (out / ('profile/borg.txt' if name == 'borg.txt' else name)).write_bytes(read(EVIDENCE, PREFIX + name))
    pristine = read('e473720ed', SOURCE).decode()
    proposal = read(FIX, SOURCE).decode()
    assert pristine.count(OLD) == 1 and pristine.replace(OLD, NEW) == proposal
    original = read(BEFORE, SOURCE).decode()
    assert (ROOT / SOURCE).read_text() == original.replace(OLD, NEW)
    before, build = args.before_build.resolve(), args.product_build.resolve()
    assert (before.parents[1] / SOURCE).read_text() == original
    helpers = sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    assert helpers
    report = {'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'),
              'before_source': BEFORE, 'source_fix': FIX,
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': sha(build / 'game/angband'), 'phases': {}, 'verified': False}
    for phase in ('before', 'simple', 'after'):
        core = build if phase == 'after' else before
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        assert len(objects) >= 150
        compile_command = None
        if phase == 'simple':
            source, obj = out / 'simple.c', out / 'simple.o'
            source.write_text(original.replace('borg_timer(when_last_quaff) > 4', 'borg_timer(when_last_quaff) <= 4', 1))
            flags = (before / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
            tokens = []
            for variable in ('C_DEFINES', 'C_INCLUDES', 'C_FLAGS'):
                tokens += shlex.split(re.search(r'^' + variable + r' = (.*)$', flags, re.MULTILINE)[1])
            compile_command = ['cc', *tokens, '-I' + str(ROOT / 'src/borg'), '-c', str(source), '-o', str(obj)]
            with (out / 'simple-compile.log').open('w') as log:
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
                               env=dict(os.environ, CBUG0061_MODE=mode, CBUG0061_PROFILE=str(out / 'profile'), LC_ALL='C.UTF-8'),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            text = re.sub(r'\x1b\[[0-9;]*m', '', r.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            outcome = re.search(r'^OUTCOME (.*)$', text, re.MULTILINE)
            row = {'exit': r.returncode, 'passed': 'native-c/CBUG-0061 finished: 1/1 passed' in text,
                   'completed': bool(outcome), 'log_sha256': sha(log)}
            if outcome:
                row.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', outcome[1])})
            rows[mode] = row
        report['phases'][phase] = {'cases': rows, 'binary_sha256': sha(binary), 'command': command,
                                   'variant_compile_command': compile_command,
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(phase, sum(r['passed'] for r in rows.values()), '/', len(rows), flush=True)
    rows = {phase: data['cases'] for phase, data in report['phases'].items()}
    assert all(r['exit'] == 0 and r['completed'] for phase in rows.values() for r in phase.values())
    assert sum(r['passed'] for r in rows['before'].values()) == 5
    assert all(not rows['before'][m]['passed'] for m in ('long-gap', 'recent', 'boundary-four', 'first-use'))
    assert sum(r['passed'] for r in rows['simple'].values()) == 8 and not rows['simple']['first-turn']['passed']
    assert all(r['passed'] for r in rows['after'].values())
    for mode in ('long-gap', 'first-use'):
        a, b = rows['before'][mode], rows['after'][mode]
        assert not a['used'] and not a['healed'] and a['confused']
        assert b['used'] and b['healed'] == 60 and not b['confused'] and b['potions_spent'] == 1
    for mode in ('recent', 'boundary-four'):
        a, b = rows['before'][mode], rows['after'][mode]
        assert a['used'] and a['healed'] == 60 and not b['used'] and not b['healed'] and b['confused']
    for mode in CONTROLS:
        assert (out / f'before-{mode}.log').read_bytes() == (out / f'after-{mode}.log').read_bytes(), mode
    report['identical_controls'] = list(CONTROLS)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
