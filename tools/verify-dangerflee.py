#!/usr/bin/env python3
"""Verify source156 (dangerflee-156) with the unchanged native fixture.

borg_caution()'s "Fleeing (excessive danger)" branch is documented as "do not
flee level if going after Morgoth or fighting a unique" but its test required
`ready_morgoth == 1`, so it fired only for a Borg that WAS going after Morgoth
and never for an ordinary one. The owner-decided correction is
`ready_morgoth != 1`. The unchanged fixture has three modes: `excessive` (a
low-level Borg, danger above twice its hit points, no unique, not Morgoth-ready:
before no flee, after flee plus desperate-stairs), `morgoth` (Morgoth-ready:
the guard now correctly holds, so the pristine firing disappears) and `hurt`
(danger within bounds: no flee, byte-identical before/after).

Provenance is proven byte-wise (before module + source diff == product
module). Normal phases only; no sanitizer phase (one-token condition).
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
BEFORE = '120ca9916d0b0813171112f9345375fd7745d76b'
SOURCE_FIX = '007d45483832b2792ddde1b2c368b67975365496'
EVIDENCE = '7d796742e9ad496695baa24f9b076f203a5d74c6'
PIN = '809e556b39e47c2dd13c6dd53aa42b7ac8329010'
PREFIX = 'docs/audit/c-reports/dangerflee-156/'
SOURCE = 'src/borg/borg-caution.c'
MODES = ('excessive', 'morgoth', 'hurt')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--fix', required=True, help='applied product commit')
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()

    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)

    (out / 'scenario.c').write_bytes(read(EVIDENCE, PREFIX + 'scenario.c'))
    (out / 'profile/borg.txt').write_bytes(read(EVIDENCE, PREFIX + 'profile/borg.txt'))
    same = subprocess.run(
        ['git', 'diff', '--exit-code', PIN, EVIDENCE, '--',
         PREFIX + 'scenario.c', PREFIX + 'borg.txt', PREFIX + 'profile'],
        cwd=ROOT, capture_output=True)
    assert same.returncode == 0, 'runtime fixtures changed since the run pin'
    before, build = args.before_build.resolve(), args.product_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', SOURCE_FIX + '^', SOURCE_FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / 'src/borg').mkdir(parents=True)
        (d / SOURCE).write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / SOURCE).read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered, 'product module != before + source diff'
    # The only src/lib difference between the before commit and the product is the fix.
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', BEFORE, 'HEAD', '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'],
        cwd=ROOT, text=True).split()
    assert changed == [SOURCE], changed
    subprocess.run(['git', 'merge-base', '--is-ancestor', args.fix, 'HEAD'], cwd=ROOT, check=True)

    report = {
        'fixture_commit': EVIDENCE, 'fixture_pin': PIN,
        'fixture_sha256': sha(out / 'scenario.c'),
        'source_fix': SOURCE_FIX, 'fix': args.fix,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
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
                env=dict(os.environ, DF156_PROFILE=str(out / 'profile'), DF156_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/dangerflee-156 finished: 1/1 passed' in text,
                   'log_sha256': sha(log)}
            for tag, key in (('STATE ', 'state'), ('OUTCOME ', 'outcome')):
                m = re.search(re.escape(tag) + r'.*', text)
                if m:
                    row[key] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', m[0])}
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    b, a = report['phases']['before']['cases'], report['phases']['after']['cases']
    assert all(r['exit'] == 0 for r in (*b.values(), *a.values()))
    # excessive: no flee before, flee plus desperate stairs after.
    assert not b['excessive']['passed'] and a['excessive']['passed']
    assert b['excessive']['outcome'] == {'excessive_flee': 0, 'desperate_stairs': 0}
    assert a['excessive']['outcome'] == {'excessive_flee': 1, 'desperate_stairs': 1}
    # morgoth: the pristine inverted condition fired here; the corrected guard holds.
    assert not b['morgoth']['passed'] and a['morgoth']['passed']
    assert b['morgoth']['outcome'] == {'excessive_flee': 1, 'desperate_stairs': 1}
    assert a['morgoth']['outcome'] == {'excessive_flee': 0, 'desperate_stairs': 0}
    # hurt: danger within bounds, identical before and after.
    assert b['hurt']['passed'] and a['hurt']['passed']
    assert b['hurt']['log_sha256'] == a['hurt']['log_sha256']
    assert a['hurt']['outcome'] == {'excessive_flee': 0, 'desperate_stairs': 0}
    for mode in MODES:
        assert b[mode]['state'] == a[mode]['state'], mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
