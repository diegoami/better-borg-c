#!/usr/bin/env python3
"""Verify source64 incrementally with the already-carried caster-path correction.

Run under the shared native lock. Four variants use actual product objects;
only a disposable original projection object removes the independent helper
for diagnostics. Normal source/build objects are never changed for variants.
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
BASE = 'e473720ed88a0f0c7ca66815cef3000eb4a38bc3'
BEFORE = '8aff765683493311ca61d66ca1e4f02d241d7a37'
FIX = 'b223c4f18622883549682f9f997b76fe1f06fc73'
HELPER = '1bce07d8080b520589c292c793cc0b95ef9df182'
EVIDENCE = '0507c24cccd2131710e4e6cd566f901bad94e081'
PREFIX = 'docs/audit/c-reports/CBUG-0048/'
MODES = ('clear-path', 'blocked', 'ball-control', 'direct-control', 'boulder-control')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def correction(source):
    old = '    bool bolt       = false;\n'
    loop = 'for (q = 0; q < kill->ranged_attack; q++) {'
    assert source.count(old) == source.count(loop) == 1
    return source.replace(old, '', 1).replace(loop, loop + '\n        bool bolt = false;', 1)


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
    for name in ('scenario.c', 'borg.txt'):
        (out / ('profile/borg.txt' if name == 'borg.txt' else name)).write_bytes(read(EVIDENCE, PREFIX + name))
    danger, projection = 'src/borg/borg-danger.c', 'src/borg/borg-projection.c'
    assert correction(read(BASE, danger).decode()) == read(FIX, danger).decode()
    assert (ROOT / danger).read_text() == correction(read(BEFORE, danger).decode())
    assert (ROOT / projection).read_bytes() == read(HELPER, projection)
    before, build = args.before_build.resolve(), args.product_build.resolve()
    assert (before.parents[1] / danger).read_bytes() == read(BEFORE, danger)
    assert (before.parents[1] / projection).read_bytes() == read(HELPER, projection)
    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    helpers = sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    assert helpers
    source, obj = out / 'without-helper-projection.c', out / 'without-helper-projection.o'
    source.write_bytes(read(BASE, projection))
    flags = (before / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
    tokens = []
    for variable in ('C_DEFINES', 'C_INCLUDES', 'C_FLAGS'):
        tokens += shlex.split(re.search(r'^' + variable + r' = (.*)$', flags, re.MULTILINE)[1])
    compile_command = ['cc', *tokens, '-I' + str(ROOT / 'src/borg'), '-c', str(source), '-o', str(obj)]
    with (out / 'alternative-compile.log').open('w') as log:
        subprocess.run(compile_command, stdout=log, stderr=subprocess.STDOUT, check=True)
    report = {'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'),
              'fix': FIX, 'helper': HELPER, 'before_commit': BEFORE, 'before_native_gate': before_gate,
              'before_binary_sha256': sha(before / 'game/angband'),
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': sha(build / 'game/angband'),
              'alternative_compile_command': compile_command, 'phases': {}, 'verified': False}
    for phase in ('neither', 'path-only-before', 'per-spell-only', 'both-after'):
        core = build if phase in ('per-spell-only', 'both-after') else before
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        assert len(objects) >= 150
        if phase in ('neither', 'per-spell-only'):
            replaced = [o for o in objects if o.as_posix().endswith(projection + '.o')]
            assert len(replaced) == 1
            objects = [obj if o == replaced[0] else o for o in objects]
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'src/tests'),
                   str(out / 'scenario.c'), *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run([str(binary), '-v'], cwd=build / 'game',
                                    env=dict(os.environ, CBUG0048_MODE=mode, CBUG0048_PROFILE=str(out / 'profile'), LC_ALL='C.UTF-8'),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            outcome = re.search(r'OUTCOME (.*)', text)
            row = {'exit': result.returncode, 'completed': bool(outcome),
                   'passed': 'native-c/CBUG-0048 finished: 1/1 passed' in text, 'log_sha256': sha(log)}
            if outcome:
                row.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', outcome[1])})
            rows[mode] = row
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary),
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(phase, sum(r['passed'] for r in rows.values()), '/', len(rows), flush=True)
    cases = {p: d['cases'] for p, d in report['phases'].items()}
    assert all(r['exit'] == 0 and r['completed'] for rows in cases.values() for r in rows.values())
    for phase, count in (('neither', 3), ('path-only-before', 4), ('per-spell-only', 5), ('both-after', 5)):
        assert sum(r['passed'] for r in cases[phase].values()) == count
    before, after = cases['path-only-before'], cases['both-after']
    assert not before['blocked']['passed'] and all(r['passed'] for r in after.values())
    a, b = before['blocked'], after['blocked']
    assert not a['escape'] and a['hp_lost'] == 59
    assert b['escape'] and b['hp_lost'] == 54 and b['scrolls_spent'] == 1
    for mode in ('clear-path', 'ball-control', 'direct-control', 'boulder-control'):
        assert before[mode]['log_sha256'] == after[mode]['log_sha256'], mode
    # Retain original standalone proof, without attributing its open-shot
    # benefit anew to the incremental correction on the helper-fixed product.
    a, b = cases['neither']['clear-path'], cases['per-spell-only']['clear-path']
    assert not a['escape'] and a['hp_lost'] == 54
    assert b['escape'] and b['hp_lost'] == 0 and b['scrolls_spent'] == 1
    report['identical_incremental_controls'] = ['clear-path', 'ball-control', 'direct-control', 'boulder-control']
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
