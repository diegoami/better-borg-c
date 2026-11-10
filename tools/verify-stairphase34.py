#!/usr/bin/env python3
"""Verify the source34 stair-escape key queue (source fix 2176cf71) on product cores.

Five escape steps (danger levels 3.1, 4.1, 5.1, 6.1 and 8) tested the up
staircase inside the Phase Door condition:

    if ((borg_escape_stair() || borg_caution_phase(...)) && ...)

borg_escape_stair() queues the climb key '<' and returns true, but the rest
of the condition still ran: if a phase was possible its keys were queued
after the '<', and if not the '<' stayed queued and the routine could queue
a teleport.  The correction makes the staircase its own branch,
borg_escape_stair() || (borg_caution_phase(...) && ...), so a chosen stair
escape queues only '<'.

The kit is the source lane's unchanged native-c/stairphase-34 fixture
(fixture commit below).  Before the fix, upstair and antisummon queue the
phase or teleport after '<' and fail; after the fix both pass with a single
climb key.  downstair, floor and climb are controls: they pass in both
phases and their logs are byte-identical.

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
BEFORE = 'e06a84ce4a727df556de0a1e991b12198d458966'
FIX = '2176cf71cebb4b2922e67a3516e3c82c283ed426'
EVIDENCE = '1cb472f2e6fa72069346298a0e2baf27dfe863f2'
PREFIX = 'docs/audit/c-reports/stairphase-34/'
SOURCE = 'src/borg/borg-escape.c'
MODES = ('upstair', 'antisummon', 'downstair', 'floor', 'climb')
SUITE = 'native-c/stairphase-34'
# Per mode: (passes before, passes after).
EXPECT = {'upstair': (False, True), 'antisummon': (False, True),
          'downstair': (True, True), 'floor': (True, True), 'climb': (True, True)}
# The flipped rows, as the kit records them.
BEFORE_ROWS = {
    'upstair': {'depth_before': 10, 'depth_after': 9, 'climbed': 1,
                'phase_read': 1, 'teleport_read': 0,
                'scroll_read_on_new_level': 1, 'moved': 1, 'commands': 4},
    'antisummon': {'depth_before': 10, 'depth_after': 9, 'climbed': 1,
                   'phase_read': 0, 'teleport_read': 1,
                   'scroll_read_on_new_level': 1, 'moved': 1, 'commands': 4},
}
AFTER_ROWS = {
    'upstair': {'depth_before': 10, 'depth_after': 9, 'climbed': 1,
                'phase_read': 0, 'teleport_read': 0,
                'scroll_read_on_new_level': 0, 'moved': 1, 'commands': 1},
    'antisummon': {'depth_before': 10, 'depth_after': 9, 'climbed': 1,
                   'phase_read': 0, 'teleport_read': 0,
                   'scroll_read_on_new_level': 0, 'moved': 1, 'commands': 1},
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-gate', required=True, type=Path,
                   help='result.json of the gate run at the before commit')
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
    checked = ['scenario.c', 'profile/borg.txt']
    for name in checked:
        assert (ROOT / PREFIX / name).read_bytes() == (out / name).read_bytes(), \
            'working-tree fixture differs from its commit: ' + name

    before, build = args.before_build.resolve(), args.product_build.resolve()

    # Byte-wise provenance: the before module plus the source diff is the product module.
    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / SOURCE).parent.mkdir(parents=True)
        (d / SOURCE).write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / SOURCE).read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered, 'product module != before + source diff'
    fix_scope = subprocess.check_output(
        ['git', 'diff', '--name-only', FIX + '^', FIX, '--', 'src', 'lib',
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
                env=dict(os.environ, **{'SP34_MODE': mode,
                                        'SP34_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            omatch = re.search(r'OUTCOME (.*)', text)
            rows[mode] = {
                'exit': result.returncode,
                'passed': SUITE + ' finished: 1/1 passed' in text,
                'outcome': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch[1])} if omatch else {},
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
    for mode, rows in BEFORE_ROWS.items():
        assert b[mode]['outcome'] == rows, ('before rows', mode, b[mode]['outcome'])
    for mode, rows in AFTER_ROWS.items():
        assert a[mode]['outcome'] == rows, ('after rows', mode, a[mode]['outcome'])
    for mode in ('downstair', 'floor', 'climb'):
        assert b[mode]['outcome'] == a[mode]['outcome'], ('control rows', mode)
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], ('control changed', mode)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
