#!/usr/bin/env python3
"""Verify source52: type the birth menu's own letters when respawning (fix 85e7ce6c6).

borg_reincarnate_start() picks the new race and class by typing the menu letter
for each choice.  It used all_letters, but the birth menus label their entries with
all_letters_nohjkl, which skips h, j, k and l.  From the eighth entry on the typed
letter was wrong: Half-Troll (h), High-Elf (j) and Kobold (k) typed a letter the
menu does not have, so the highlighted race was kept; Dunadan (i) selected
Half-Troll; for classes Ranger (h) kept the highlighted class and Blackguard (i)
selected Ranger.  The correction types the same letters the menus use.

The kit is the source lane's unchanged native-c/rebirthkey-52 fixture.  The race8,
class8 and race7 modes fail before (right_character=0) and pass after
(right_character=1); dwarfpriest and humanwarrior (indices below 7, where both
tables agree) are the controls, with byte-identical logs.

Run under the shared native lock after this tree's gate build, with the
before snapshot built at the before commit (its gate result recorded under
--before-gate).
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
BEFORE = '374cea77bf134ee73020a3e4ddda2c2b3631cfb9'
FIX = '85e7ce6c689e05bc209feda6d30a3bba51c533c6'
FIX_BASE = 'e473720ed88a0f0c7ca66815cef3000eb4a38bc3'
EVIDENCE = '374cea77bf134ee73020a3e4ddda2c2b3631cfb9'
PREFIX = 'docs/audit/c-reports/rebirthkey-52/'
SOURCE = 'src/borg/borg-reincarnate.c'
MODES = ('race8', 'class8', 'race7', 'dwarfpriest', 'humanwarrior')
SUITE = 'native-c/rebirthkey-52'
EXPECT = {'race8': (False, True), 'class8': (False, True), 'race7': (False, True),
          'dwarfpriest': (True, True), 'humanwarrior': (True, True)}
ROWS = {'race8': {'starved': 0,
           'respawn_started': 1,
           'race': 8,
           'class': 0,
           'want_race': 8,
           'want_class': 0,
           'queue_left': 0,
           'keys': 23,
           'right_character': 1},
 'class8': {'starved': 0,
            'respawn_started': 1,
            'race': 0,
            'class': 8,
            'want_race': 0,
            'want_class': 8,
            'queue_left': 0,
            'keys': 23,
            'right_character': 1},
 'race7': {'starved': 0,
           'respawn_started': 1,
           'race': 7,
           'class': 0,
           'want_race': 7,
           'want_class': 0,
           'queue_left': 0,
           'keys': 18,
           'right_character': 1},
 'dwarfpriest': {'starved': 0,
                 'respawn_started': 1,
                 'race': 5,
                 'class': 3,
                 'want_race': 5,
                 'want_class': 3,
                 'queue_left': 0,
                 'keys': 18,
                 'right_character': 1},
 'humanwarrior': {'starved': 0,
                  'respawn_started': 1,
                  'race': 0,
                  'class': 0,
                  'want_race': 0,
                  'want_class': 0,
                  'queue_left': 0,
                  'keys': 21,
                  'right_character': 1}}
BEFORE_ROWS = {'race8': {'starved': 0,
           'respawn_started': 1,
           'race': 7,
           'class': 0,
           'want_race': 8,
           'want_class': 0,
           'queue_left': 0,
           'keys': 23,
           'right_character': 0},
 'class8': {'starved': 0,
            'respawn_started': 1,
            'race': 0,
            'class': 7,
            'want_race': 0,
            'want_class': 8,
            'queue_left': 0,
            'keys': 23,
            'right_character': 0},
 'race7': {'starved': 0,
           'respawn_started': 1,
           'race': 0,
           'class': 0,
           'want_race': 7,
           'want_class': 0,
           'queue_left': 0,
           'keys': 18,
           'right_character': 0},
 'dwarfpriest': {'starved': 0,
                 'respawn_started': 1,
                 'race': 5,
                 'class': 3,
                 'want_race': 5,
                 'want_class': 3,
                 'queue_left': 0,
                 'keys': 18,
                 'right_character': 1},
 'humanwarrior': {'starved': 0,
                  'respawn_started': 1,
                  'race': 0,
                  'class': 0,
                  'want_race': 0,
                  'want_class': 0,
                  'queue_left': 0,
                  'keys': 21,
                  'right_character': 1}}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-gate', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--product-gate', default=ROOT / 'artifacts/native/result.json', type=Path)
    p.add_argument('--fix', required=True, help='applied product commit')
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()

    evidence = subprocess.check_output(
        ['git', 'rev-parse', EVIDENCE], cwd=ROOT, text=True).strip()

    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)

    (out / 'scenario.c').write_bytes(read(evidence, PREFIX + 'scenario.c'))
    (out / 'profile/borg.txt').write_bytes(read(evidence, PREFIX + 'profile/borg.txt'))
    for name in ('scenario.c', 'profile/borg.txt'):
        assert (ROOT / PREFIX / name).read_bytes() == (out / name).read_bytes(), \
            'working-tree fixture differs from its commit: ' + name

    before, build = args.before_build.resolve(), args.product_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX_BASE, FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / SOURCE).parent.mkdir(parents=True)
        (d / SOURCE).write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / SOURCE).read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered, 'product module != before + source diff'
    fix_scope = subprocess.check_output(
        ['git', 'diff', '--name-only', FIX_BASE, FIX, '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert fix_scope == [SOURCE], fix_scope
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', BEFORE, 'HEAD', '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert changed == [SOURCE], changed
    subprocess.run(['git', 'merge-base', '--is-ancestor', args.fix, 'HEAD'], cwd=ROOT, check=True)

    before_gate = json.loads(args.before_gate.resolve().read_text())
    assert before_gate['success'] and before_gate['commit'] == BEFORE
    product_gate = json.loads(args.product_gate.resolve().read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert product_gate['success']
    subprocess.run(['git', 'merge-base', '--is-ancestor', product_gate['commit'], 'HEAD'],
                   cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--exit-code', product_gate['commit'], 'HEAD', '--',
                    'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)

    report = {
        'fixture_commit': evidence,
        'fixture_sha256': sha(out / 'scenario.c'),
        'source_fix': FIX, 'fix': args.fix,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE,
        'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': head,
        'product_native_gate': product_gate,
        'product_binary_sha256': sha(build / 'game/angband'),
        'phases': {}, 'verified': False,
    }
    for phase, core in (('before', before), ('after', build)):
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                   '-I' + str(ROOT / 'src/tests'), str(out / 'scenario.c'),
                   *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, **{'RK52_MODE': mode,
                                        'RK52_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            outcome = {}
            for omatch in re.findall(r'OUTCOME (.*)', text):
                outcome.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch)})
            rows[mode] = {
                'exit': result.returncode,
                'passed': SUITE + ' finished: 1/1 passed' in text,
                'outcome': outcome,
                'log_sha256': sha(log),
            }
            print(phase, mode, rows[mode], flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command,
                                   'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    b, a = report['phases']['before']['cases'], report['phases']['after']['cases']
    for mode in MODES:
        assert b[mode]['exit'] == 0 and a[mode]['exit'] == 0, mode
        assert b[mode]['passed'] is EXPECT[mode][0], ('before pass', mode)
        assert a[mode]['passed'] is EXPECT[mode][1], ('after pass', mode)
        assert b[mode]['outcome'] == BEFORE_ROWS[mode], ('before rows', mode, b[mode]['outcome'])
        assert a[mode]['outcome'] == ROWS[mode], ('after rows', mode, a[mode]['outcome'])
    for mode in ('dwarfpriest', 'humanwarrior'):
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], ('control changed', mode)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
