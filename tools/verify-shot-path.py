#!/usr/bin/env python3
"""Verify source279's unchanged native fixture on four actual product variants.

Run under the shared lock after the normal build. Diagnostic alternatives
replace only a disposable danger object compiled with recorded CMake flags;
ordinary product sources/objects are never changed to create alternatives.
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
BEFORE = '9929eb4eb16412ef2415a5711a3eecab92fa1288'
FIX = '1bce07d8080b520589c292c793cc0b95ef9df182'
PER_SPELL = 'b223c4f18622883549682f9f997b76fe1f06fc73'
EVIDENCE = 'cef0b118e02976a3384d4c348ba4cd0210c1f492'
PREFIX = 'docs/audit/c-reports/shot-path-279/'
MODES = ('clear-path', 'blocked', 'ball-control', 'direct-control',
         'boulder-control', 'boulder-blocked')
CONTROLS = ('blocked', 'ball-control', 'direct-control', 'boulder-blocked')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def per_spell(source):
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
    projection = 'src/borg/borg-projection.c'
    danger = 'src/borg/borg-danger.c'
    assert (ROOT / projection).read_bytes() == read(FIX, projection)
    assert (ROOT / danger).read_bytes() == read(BEFORE, danger)
    assert per_spell(read(BASE, danger).decode()) == read(PER_SPELL, danger).decode()
    before, build = args.before_build.resolve(), args.product_build.resolve()
    assert (before.parents[1] / projection).read_bytes() == read(BASE, projection)
    assert (before.parents[1] / danger).read_bytes() == read(BEFORE, danger)
    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    # Reuse the already-qualified seven-carry build; record its actual build
    # commit and prove the later documentation commits do not change inputs.
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    helpers = sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    assert helpers
    variant_source, variant_object = out / 'per-spell-danger.c', out / 'per-spell-danger.o'
    variant_source.write_text(per_spell(read(BEFORE, danger).decode()))
    flags = (before / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
    tokens = []
    for variable in ('C_DEFINES', 'C_INCLUDES', 'C_FLAGS'):
        tokens += shlex.split(re.search(r'^' + variable + r' = (.*)$', flags, re.MULTILINE)[1])
    compile_command = ['cc', *tokens, '-I' + str(ROOT / 'src/borg'), '-c', str(variant_source), '-o', str(variant_object)]
    with (out / 'alternative-compile.log').open('w') as log:
        subprocess.run(compile_command, stdout=log, stderr=subprocess.STDOUT, check=True)
    report = {'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'),
              'before_commit': BEFORE, 'before_native_gate': before_gate,
              'before_binary_sha256': sha(before / 'game/angband'),
              'fix': FIX, 'independent_alternative': PER_SPELL,
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': sha(build / 'game/angband'),
              'alternative_compile_command': compile_command, 'phases': {}, 'verified': False}
    for phase in ('before', 'per-spell-only', 'both', 'after'):
        core = build if phase in ('both', 'after') else before
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        assert len(objects) >= 150
        if phase in ('per-spell-only', 'both'):
            replaced = [o for o in objects if o.as_posix().endswith(danger + '.o')]
            assert len(replaced) == 1
            objects = [variant_object if o == replaced[0] else o for o in objects]
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'src/tests'),
                   str(out / 'scenario.c'), *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            r = subprocess.run([str(binary), '-v'], cwd=build / 'game',
                               env=dict(os.environ, SHOTPATH279_MODE=mode, SHOTPATH279_PROFILE=str(out / 'profile'), LC_ALL='C.UTF-8'),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            text = re.sub(r'\x1b\[[0-9;]*m', '', r.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            outcome = re.search(r'^OUTCOME (.*)$', text, re.MULTILINE)
            row = {'exit': r.returncode, 'passed': 'native-c/shot-path-279 finished: 1/1 passed' in text,
                   'completed': bool(outcome), 'log_sha256': sha(log)}
            if outcome:
                row.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', outcome[1])})
            # The native unit runner prefixes this record with the test name.
            geometry = re.search(r'GEOMETRY (.*)', text)
            if geometry:
                row['geometry'] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', geometry[1])}
            rows[mode] = row
        report['phases'][phase] = {'cases': rows, 'binary_sha256': sha(binary), 'command': command,
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(phase, sum(r['passed'] for r in rows.values()), '/', len(rows), flush=True)
    rows = {phase: data['cases'] for phase, data in report['phases'].items()}
    assert all(r['exit'] == 0 and r['completed'] for phase in rows.values() for r in phase.values())
    for phase in ('before', 'per-spell-only'):
        assert sum(r['passed'] for r in rows[phase].values()) == 2
    assert all(r['passed'] for phase in ('after', 'both') for r in rows[phase].values())
    for mode, row in rows['after'].items():
        g = row['geometry']
        assert g['caster_clear'] == g['player_clear'] == g['expected_clear']
        assert g['same_start'] and not g['wall'] and not g['through_wall']
        assert g['blocker_endpoint'] == (-1 if g['expected_clear'] else 1)
        assert all(rows['before'][mode]['geometry'][k] == g[k] for k in
                   ('player_clear', 'same_start', 'wall', 'through_wall', 'blocker_endpoint'))
    for mode in ('blocked', 'boulder-blocked'):
        assert rows['before'][mode]['log_sha256'] == rows['after'][mode]['log_sha256'], mode
    for mode in CONTROLS:
        def outcomes(phase):
            return [l for l in (out / f'{phase}-{mode}.log').read_text().splitlines()
                    if l.startswith(('FRAME ', 'DECISION ', 'OUTCOME '))]
        assert outcomes('before') == outcomes('after'), mode
    a, b = rows['before']['clear-path'], rows['after']['clear-path']
    assert a['hp_lost'] == 54 and b['hp_lost'] == 0 and b['scrolls_spent'] == 1
    a, b = rows['before']['boulder-control'], rows['after']['boulder-control']
    assert a['hp_lost'] == 18 and b['hp_lost'] == 29 and b['mana_spent'] == 2
    assert rows['after']['boulder-blocked']['hp_lost'] == 0
    report['identical_full_controls'] = ['blocked', 'boulder-blocked']
    report['identical_native_outcome_controls'] = list(CONTROLS)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
