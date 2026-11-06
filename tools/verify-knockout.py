#!/usr/bin/env python3
"""Verify source14's unchanged native fixture using actual consumer core objects.

Run under flock /tmp/angband-validation.lock after the normal native build.
Only the fixture's absolute profile paths are relocated. No decision code is
copied and no assertion, seed, timed state or combat input is changed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = '3de1e3123915587483395dd40c4d2e75704e65f4'
PREFIX = 'docs/audit/c-reports/CBUG-0002/'
MODES = ('knockout', 'heavy-stun', 'paralysis', 'none')


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
    for d in ('profile', 'profile/save', 'profile/panic', 'profile/scores', 'profile/archive'):
        (out / d).mkdir(exist_ok=True)
    def read(name):
        return subprocess.check_output(['git', 'show', EVIDENCE + ':' + PREFIX + name], cwd=ROOT)
    original = read('scenario.c')
    (out / 'scenario.c').write_text(original.decode().replace('/tmp/native-c-14-evidence', str(out)))
    (out / 'profile/borg.txt').write_bytes(read('borg.txt'))
    build = args.product_build.resolve()
    helpers = sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    if not helpers:
        raise RuntimeError('Normal native build must supply test helpers')
    report = {'fixture_commit': EVIDENCE, 'original_fixture_sha256': hashlib.sha256(original).hexdigest(),
              'fixture_sha256': sha(out / 'scenario.c'), 'relocation': str(out),
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': sha(build / 'game/angband'), 'phases': {}, 'verified': False}
    for phase, core in (('before', args.before_build.resolve()), ('after', build)):
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        if len(objects) < 150:
            raise RuntimeError('Incomplete native core')
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'src/tests'),
                   str(out / 'scenario.c'), *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            r = subprocess.run([str(binary), '-v'], cwd=build / 'game',
                               env=dict(os.environ, CBUG0002_MODE=mode, LC_ALL='C.UTF-8'),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            log = out / f'{phase}-{mode}.log'
            log.write_bytes(r.stdout)
            text = r.stdout.decode()
            kill = re.search(r'^KILL_REACTION delta=(\d+)$', text, re.MULTILINE)
            recovered = re.search(r'^RECOVERED turn=(\d+) hp=(\d+) global_suppression=(\d+) knockout_messages=(\d+)$', text, re.MULTILINE)
            outcome = re.search(r'^OUTCOME deaths=(\d+) reactions_before=(\d+) reactions_after=(\d+) delta=(\d+)$', text, re.MULTILINE)
            row = {'exit': r.returncode, 'passed': 'finished: 1/1 passed' in text,
                   'completed': 'finished:' in text, 'log_sha256': sha(log),
                   'kill_reactions': int(kill[1]) if kill else None,
                   'monster_kills': int(outcome[1]) if outcome else None,
                   'recovered_turn': int(recovered[1]) if recovered else None,
                   'suppression': int(recovered[3]) if recovered else None}
            rows[mode] = row
            print(phase, mode, row, flush=True)
        gate = core.parents[1] / 'artifacts/native/result.json'
        report['phases'][phase] = {'cases': rows, 'binary_sha256': sha(binary), 'command': command,
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers},
                                   'native_gate': json.loads(gate.read_text()) if gate.exists() else None}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    before = report['phases']['before']['cases']
    after = report['phases']['after']['cases']
    for mode in MODES:
        assert before[mode]['exit'] == after[mode]['exit'] == 0, mode
        assert before[mode]['completed'] and after[mode]['passed'], mode
        assert before[mode]['monster_kills'] == after[mode]['monster_kills'] == 1, mode
        if mode == 'knockout':
            assert not before[mode]['passed'], mode
            assert (before[mode]['kill_reactions'], after[mode]['kill_reactions']) == (0, 1)
            assert (before[mode]['suppression'], after[mode]['suppression']) == (1, 0)
        else:
            assert before[mode]['passed'] and before[mode]['log_sha256'] == after[mode]['log_sha256'], mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
