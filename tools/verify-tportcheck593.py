#!/usr/bin/env python3
"""Verify source593: check teleport landing zones with either kind of teleport (fix edc4dcb3f).

The teleport landing-zone check required both a teleport source
(BI_ATELEPORT) and an escape staff (BI_AESCAPE) before it would examine
landing zones, while its callers in the Destruction and Teleport Level
defences ask whether the borg has either kind.  With teleportation
scrolls but no escape staff the check refused, and the borg read the
Scrolls of Destruction next to the danger instead of checking for a safe
landing.  Examine landing zones with either kind.

The kit is the source lane's unchanged native-c/tportcheck-593 fixture.
Expected: the scrolls mode (teleportation scrolls, no escape staff,
danger 2000) fails before (landing check refused, Destruction read) and
passes after (landing zone checked, no Destruction read); the has-both
control passes in both phases and is byte-identical between the phases.

Run under the shared native lock after this tree's gate build, with the
before snapshot built at the before commit (its gate result recorded
under --before-gate).
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
BEFORE = '382acb7b92bdcd004a144f7aca3403bf3e656dd7'
FIX = 'edc4dcb3ff4c869b1fd366dd87330751a0de4d9c'
FIX_BASE = '42cd156ac9f95ddf4311e88dd7ad462292d6d1d6'
EVIDENCE = '382acb7b92bdcd004a144f7aca3403bf3e656dd7'
PREFIX = 'docs/audit/c-reports/tportcheck-593/'
SOURCE = 'src/borg/borg-escape.c'
SUITE = 'native-c/tportcheck-593'
MODES = ('scrolls', 'control')
EXPECT = {m: (True, True) for m in MODES}
EXPECT['scrolls'] = (False, True)
SCROLLS_STATE = {'danger': 2000, 'curhp': 300, 'avoidance': 300, 'ateleport': 5, 'aescape': 0}
CONTROL_STATE = {'danger': 2000, 'curhp': 300, 'avoidance': 300, 'ateleport': 5, 'aescape': 6}
BEFORE_ROWS = {
    'scrolls': {'state': dict(SCROLLS_STATE),
                'outcome': {'landing_ok': 0, 'uses_destruction': 1}},
    'control': {'state': dict(CONTROL_STATE),
                'outcome': {'landing_ok': 1, 'uses_destruction': 0}},
}
ROWS = {
    'scrolls': {'state': dict(SCROLLS_STATE),
                'outcome': {'landing_ok': 1, 'uses_destruction': 0}},
    'control': BEFORE_ROWS['control'],
}


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
        applied = subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d)
        assert applied.returncode == 0, 'source diff does not apply to the before module'
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
        # Compile the scenario against THIS build's own headers (per-phase
        # include roots; the pattern from the source589 verifier).
        cache = (core / 'CMakeCache.txt').read_text(errors='replace')
        home = next(line.split('=', 1)[1].strip() for line in cache.splitlines()
                    if line.startswith('CMAKE_HOME_DIRECTORY'))
        home = Path(home)
        assert (home / 'src/borg/borg-trait.c').exists(), home
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(home / 'src'),
                   '-I' + str(home / 'src/tests'), str(out / 'scenario.c'),
                   *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, **{'TC593_MODE': mode,
                                        'TC593_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            parsed = {}
            for tag, key in (('STATE ', 'state'), ('OUTCOME ', 'outcome')):
                row = {}
                for match in re.findall(re.escape(tag) + r'(.*)', text):
                    row.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match)})
                parsed[key] = row
            rows[mode] = {
                'exit': result.returncode,
                'passed': SUITE + ' finished: 1/1 passed' in text,
                'state': parsed.get('state', {}),
                'outcome': parsed.get('outcome', {}),
                'log_sha256': sha(log),
                'capture_byte_identical': log.read_bytes() == (ROOT / PREFIX / f'{phase}-{mode}.log').read_bytes(),
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
        assert b[mode]['state'] == BEFORE_ROWS[mode]['state'], ('before state', mode, b[mode]['state'])
        assert b[mode]['outcome'] == BEFORE_ROWS[mode]['outcome'], ('before rows', mode, b[mode]['outcome'])
        assert a[mode]['state'] == ROWS[mode]['state'], ('after state', mode, a[mode]['state'])
        assert a[mode]['outcome'] == ROWS[mode]['outcome'], ('after rows', mode, a[mode]['outcome'])
    assert b['control']['log_sha256'] == a['control']['log_sha256'], 'control changed'
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
