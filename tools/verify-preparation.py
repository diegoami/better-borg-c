#!/usr/bin/env python3
"""Run source110's unchanged native preparation fixture on actual product cores.

Run under the shared validation lock after the normal native build. The source
fixture is byte-identical: its existing environment parameter isolates profiles.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = 'a19c8733c0dfa8139b04eecd8117429ec5f55cd6'
PREFIX = 'docs/audit/c-reports/CBUG-0094/'
MODES = ('regen-only', 'speed-wins', 'speed-only', 'already-active', 'unlearned',
         'blind', 'confused', 'town', 'low-mana')


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
    for name in ('scenario.c', 'borg.txt'):
        (out / ('profile/borg.txt' if name == 'borg.txt' else name)).write_bytes(read(name))
    build = args.product_build.resolve()
    helpers = sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    if not helpers:
        raise RuntimeError('Normal native build must supply test helpers')
    report = {'fixture_commit': EVIDENCE, 'fixture_sha256': sha(out / 'scenario.c'),
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
                               env=dict(os.environ, CBUG0094_MODE=mode, CBUG0094_PROFILE=str(out / 'profile'), LC_ALL='C.UTF-8'),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            text = re.sub(r'\x1b\[[0-9;]*m', '', r.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            outcome = re.search(r'^OUTCOME (.*)$', text, re.MULTILINE)
            row = {'exit': r.returncode, 'passed': 'native-c/CBUG-0094 finished: 1/1 passed' in text,
                   'completed': bool(outcome), 'log_sha256': sha(log)}
            if outcome:
                row.update({k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', outcome[1])})
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
        assert before[mode]['completed'] and after[mode]['completed'], mode
        assert before[mode]['exit'] == after[mode]['exit'] == 0 and after[mode]['passed'], mode
        if mode in ('regen-only', 'speed-wins'):
            assert not before[mode]['passed'], mode
            assert before[mode]['commands'] == 2 and after[mode]['commands'] == 1, mode
            assert before[mode]['mana_spent'] - after[mode]['mana_spent'] == 20, mode
            assert (before[mode]['action_energy'], after[mode]['action_energy']) == (200, 100), mode
        else:
            assert before[mode]['passed'] and before[mode]['log_sha256'] == after[mode]['log_sha256'], mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
