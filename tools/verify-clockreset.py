#!/usr/bin/env python3
"""Verify source246 (clockreset-246) with the unchanged native fixture.

borg_think_dungeon() aborted the Borg ("clock overflow") at
BORG_TIME_MAX - 3000, about 2900 turns before the graceful reset in
borg_think() could run, so the reset was unreachable. The owner-decided
correction resets the clock in place at that threshold and keeps playing
(borg_think()'s own check stays as a failsafe). The unchanged fixture sets the
clock to the exact threshold and runs one production think pass: before the
clock stays frozen at 2147480647 and the Borg is inactive; after it is 1 and
the Borg is still active.

Provenance is proven byte-wise (before module + source diff == product
module). Normal phases only; no sanitizer phase (no memory error).
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
BEFORE = '068d34022a77949ec5157fdb62bb3b1e3e7242cb'
SOURCE_FIX = '7cc0ebbd2016afeaaf57c5e976251b67f7c0e147'
EVIDENCE = '6d4859904037aa987577a8bcab522d5ebd4ae17a'
PIN = '85ff225404d99acfdf22568b4bc5ec64afd4218b'
PREFIX = 'docs/audit/c-reports/clockreset-246/'
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
            env=dict(os.environ, CR246_PROFILE=str(out / 'profile'), LC_ALL='C.UTF-8'),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
        log = out / f'{phase}-main.log'
        log.write_text(text)
        row = {'exit': result.returncode,
               'passed': 'native-c/clockreset-246 finished: 1/1 passed' in text,
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
    assert b['state'] == {'time_after': 2147480647, 'active': 0}, b['state']
    assert a['state'] == {'time_after': 1, 'active': 1}, a['state']
    assert b['outcome'] == {'kept_playing': 0, 'time_reset': 0}
    assert a['outcome'] == {'kept_playing': 1, 'time_reset': 1}
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
