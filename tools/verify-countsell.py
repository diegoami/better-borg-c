#!/usr/bin/env python3
"""Verify source134 (countsell-134) with the unchanged native fixture.

borg_count_sell() returned 0 at once when it met an unidentified item that is not
part of a pile, discarding everything already counted, so a full pack with one
such item looked like nothing to sell and the Borg dived instead of selling first.
The correction skips that item. The unchanged fixture has three modes: `full-unid`
(a full pack with one unidentified single item: before sellable 0 and the Borg goes
down, after sellable 15 and it stays up), `full` (no unidentified item, byte-identical)
and `light` (a nearly empty pack: sellable 0 to 2, still dives).

Provenance is proven byte-wise (before module + source diff == product module).
Normal phases only; no sanitizer phase.
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
BEFORE = 'd4f9bb5c92179fcc4107d357af3882738d482aff'
SOURCE_FIX = '026a42d3fcdfcbedaaef12c6f39200e38ecbd2ed'
EVIDENCE = '6aedfa6f16479584a9c59c6bd6dbdc8408f624a8'
PIN = '68b23b2a1b2eeb94d70a86e98375aaddaadf0951'
PREFIX = 'docs/audit/c-reports/countsell-134/'
SOURCE = 'src/borg/borg-store-sell.c'
MODES = ('full-unid', 'full', 'light')


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
                env=dict(os.environ, CS134_PROFILE=str(out / 'profile'), CS134_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/countsell-134 finished: 1/1 passed' in text,
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
    assert not b['full-unid']['passed'] and a['full-unid']['passed']
    assert b['full-unid']['state'] == {'sellable': 0, 'unidentified': 1, 'prepared_next': 1}
    assert a['full-unid']['state'] == {'sellable': 15, 'unidentified': 1, 'prepared_next': 1}
    assert b['full-unid']['outcome'] == {'went_down': 1} and a['full-unid']['outcome'] == {'went_down': 0}
    assert b['full']['passed'] and a['full']['passed']
    assert b['full']['log_sha256'] == a['full']['log_sha256']
    assert a['full']['state'] == {'sellable': 15, 'unidentified': 0, 'prepared_next': 1}
    assert b['light']['passed'] and a['light']['passed']
    assert b['light']['state'] == {'sellable': 0, 'unidentified': 1, 'prepared_next': 1}
    assert a['light']['state'] == {'sellable': 2, 'unidentified': 1, 'prepared_next': 1}
    assert b['light']['outcome'] == a['light']['outcome'] == {'went_down': 1}
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
