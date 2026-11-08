#!/usr/bin/env python3
"""Verify source199 (swapacid-199) with the unchanged native fixture.

The swap weapon's acid resistance was read from its electricity element, so a weapon resisting
electricity was counted as acid-resistant (and an acid-resistant one was not). The correction reads
the acid element. The unchanged fixture has four modes: `elec` and `acid` (before the swap weapon's
acid resistance and the level-30 preparedness follow the wrong element; after they follow the acid
element) and `fire` and `none` (controls, byte-identical before/after).

Provenance is proven byte-wise (before module + source diff == product module). Normal phases only;
no sanitizer phase.
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
BEFORE = 'a4084032485a7c7f29153d0b37ce63dede3e4d5a'
SOURCE_FIX = 'eddbf5b82293ea70a76fae960bc9f8debf1579c6'
EVIDENCE = 'fbc0de07ffa7729f618ea64364086d8b80dd1254'
PIN = '9eca003a5896403b9810806b4fc656446a34cf9a'
PREFIX = 'docs/audit/c-reports/swapacid-199/'
SOURCE = 'src/borg/borg-trait-swap.c'
MODES = ('elec', 'acid', 'fire', 'none')


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
                env=dict(os.environ, SA199_PROFILE=str(out / 'profile'), SA199_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/swapacid-199 finished: 1/1 passed' in text,
                   'log_sha256': sha(log)}
            for tag, key in (('STATE ', 'state'), ('OUTCOME ', 'outcome')):
                for m in re.findall(re.escape(tag) + r'.*', text):
                    row.setdefault(key, {}).update(
                        {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', m)})
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    b, a = report['phases']['before']['cases'], report['phases']['after']['cases']
    assert all(r['exit'] == 0 for r in (*b.values(), *a.values()))
    assert not b['elec']['passed'] and a['elec']['passed']
    assert b['elec']['state']['swap_acid'] == 1 and a['elec']['state']['swap_acid'] == 0
    assert b['elec']['outcome'] == {'prepared30': 1, 'acid_counted': 1}
    assert a['elec']['outcome'] == {'prepared30': 0, 'acid_counted': 0}
    assert not b['acid']['passed'] and a['acid']['passed']
    assert b['acid']['state']['swap_acid'] == 0 and a['acid']['state']['swap_acid'] == 1
    assert b['acid']['outcome'] == {'prepared30': 0, 'acid_counted': 0}
    assert a['acid']['outcome'] == {'prepared30': 1, 'acid_counted': 1}
    for mode in ('fire', 'none'):
        assert b[mode]['passed'] and a[mode]['passed'], mode
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], mode
        assert a[mode]['outcome'] == {'prepared30': 0, 'acid_counted': 0}, mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
