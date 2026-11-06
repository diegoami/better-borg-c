#!/usr/bin/env python3
"""Run immutable source82 scenarios against existing native product core objects.

No copied decision implementation. Only the fixture's absolute output directory
is relocated; keep the fixture, inputs and assertions otherwise unchanged.
Run under flock /tmp/angband-validation.lock.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = '1b67370d0dc56d9b7ef34e5356e63d21a7095545'
PREFIX = 'docs/audit/c-reports/CBUG-0066/'
MODES = ('armour-better', 'weapon-better', 'armour-only', 'weapon-only', 'tie',
         'no-benefit', 'fire-armour', 'electric-weapon', 'both-helpful')
CONTROLS = ('armour-only', 'weapon-only', 'tie', 'no-benefit')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-build', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for directory in ('profile', 'profile/save', 'profile/scores', 'profile/panic', 'profile/archive'):
        (out / directory).mkdir(exist_ok=True)
    def read(name):
        return subprocess.check_output(['git', 'show', EVIDENCE + ':' + PREFIX + name], cwd=ROOT)
    original = read('expanded/scenario.c')
    fixture = original.decode().replace('/tmp/native-c-66-expanded', str(out))
    (out / 'scenario.c').write_text(fixture)
    (out / 'profile/borg.txt').write_bytes(read('borg.txt'))
    helpers = sorted((args.product_build.resolve() / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    if not helpers:
        raise RuntimeError('Native gate must build unit test helpers first')
    result = {'evidence_ref': EVIDENCE, 'original_fixture_sha256': hashlib.sha256(original).hexdigest(),
              'fixture_sha256': digest(out / 'scenario.c'), 'relocation': str(out),
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': digest(args.product_build / 'game/angband'), 'phases': {}}
    for phase, build in (('before', args.baseline_build.resolve()), ('after', args.product_build.resolve())):
        objects = sorted((build / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        if len(objects) < 150:
            raise RuntimeError('Incomplete native core')
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'src/tests'),
                   str(out / 'scenario.c'), *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            r = subprocess.run([str(binary), '-v'], cwd=args.product_build.resolve() / 'game',
                               env=dict(os.environ, CBUG0066_MODE=mode, LC_ALL='C.UTF-8'),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            log = out / f'{phase}-{mode}.log'
            log.write_bytes(r.stdout)
            text = r.stdout.decode()
            hp = re.search(r'OUTCOME hp_before=(\d+) hp_after=(-?\d+) hp_lost=(\d+)', text)
            rows[mode] = {'exit': r.returncode, 'passed': 'finished: 1/1 passed' in text,
                          'completed': 'finished:' in text, 'log_sha256': digest(log)}
            if hp:
                rows[mode].update(zip(('hp_before', 'hp_after', 'hp_lost'), map(int, hp.groups())))
            print(phase, mode, rows[mode], flush=True)
        result['phases'][phase] = {'cases': rows, 'binary_sha256': digest(binary),
                                  'command': command, 'objects_sha256': {str(o): digest(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    before = result['phases']['before']['cases']
    after = result['phases']['after']['cases']
    for mode in MODES:
        assert before[mode]['completed'] and before[mode]['exit'] == 0, mode
        assert after[mode]['completed'] and after[mode]['exit'] == 0 and after[mode]['passed'], mode
        if mode in CONTROLS:
            assert before[mode]['passed'], mode
            assert before[mode]['log_sha256'] == after[mode]['log_sha256'], mode
        else:
            assert not before[mode]['passed'], mode
            assert before[mode]['hp_lost'] > after[mode]['hp_lost'], mode
    result['verified'] = True
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
