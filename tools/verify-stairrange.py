#!/usr/bin/env python3
"""Verify source245 (stairrange-245) with the unchanged native fixture.

The munchkin stair-range adjustment `(clevel - 10) + (10 - depth)` is negative
below character level 10, so the "increase" shrank the range (8 to 3 for a
level-5 Borg at depth 10) and no visible staircase counted as close. The
owner-decided correction gates the adjustment on `clevel > 10`. The unchanged
fixture runs the production munchkin decision once: before, no climb
(`goal.less` 0, the requirement fails); after, power climb (`goal.less` 1).

borg-think-dungeon.c carries no earlier patch over the changed lines, but
provenance is still proven byte-wise: the source diff applied to the before
module equals the product module.

Normal phases only. There is no sanitizer phase: this is range arithmetic with
no memory error to observe.
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
BEFORE = 'eea2eee96412280d6406f772ac2f73d8975f7ba4'
SOURCE_FIX = 'c16b3e9d14470dd19ef884f37f9eca2f7cc7d37f'
EVIDENCE = '5da8217435bb693c3aabbff9d75520f96f355c61'
PIN = '3c9a75e2023386863db8a21be16db5b8c12a840a'
PREFIX = 'docs/audit/c-reports/stairrange-245/'
SOURCE = 'src/borg/borg-think-dungeon.c'


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
        result = subprocess.run(
            [str(binary), '-v'], cwd=build / 'game',
            env=dict(os.environ, SR245_PROFILE=str(out / 'profile'), LC_ALL='C.UTF-8'),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
        log = out / f'{phase}-main.log'
        log.write_text(text)
        row = {'exit': result.returncode,
               'passed': 'native-c/stairrange-245 finished: 1/1 passed' in text,
               'log_sha256': sha(log)}
        for tag, key in (('SETUP ', 'setup'), ('STATE ', 'state'), ('OUTCOME ', 'outcome')):
            m = re.search(re.escape(tag) + r'.*', text)
            if m:
                row[key] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', m[0])}
        print(phase, row, flush=True)
        report['phases'][phase] = {'case': row, 'command': command, 'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    b, a = report['phases']['before']['case'], report['phases']['after']['case']
    assert b['exit'] == a['exit'] == 0
    assert not b['passed'] and a['passed']
    assert b['outcome'] == {'climb_decision': 0} and a['outcome'] == {'climb_decision': 1}
    for row in (b, a):
        assert row['state']['clevel'] == 5 and row['state']['depth'] == 10
    assert b['state']['goal_less'] == 0 and a['state']['goal_less'] == 1
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
