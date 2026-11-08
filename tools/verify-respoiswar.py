#!/usr/bin/env python3
"""Verify source185 (respoiswar-185) with the unchanged native fixture.

The warrior's Resist Poison reward in borg_power_inventory() continued the Resist Cold
count (a stale counter), so cold-resistant warriors were under-rewarded. The correction
resets the counter before the poison loop. The unchanged fixture has two modes: `cold`
(four Resist Cold potions: before potion_reward 900, after 2400) and `plain` (control,
byte-identical before/after).

Stacked on patch for source184 in the same function: provenance is the source change merged
onto the before module. Normal phases only; no sanitizer phase.
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
BEFORE = '089acfae4735f1b76d2fa2723cdbc44786647c4f'
SOURCE_FIX = 'c056daabf55e6a1713e68381ef4a72ec6fd349b9'
EVIDENCE = '58a366e8b9bdc886c9c94292271ea0313e678906'
PIN = '6f130a4eea68e0c2855bcbb257cf9158752d369b'
PREFIX = 'docs/audit/c-reports/respoiswar-185/'
SOURCE = 'src/borg/borg-power.c'
MODES = ('cold', 'plain')


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

    # Stacked carry: prove provenance by merging the source change (source parent to
    # source fix) onto the before module (the plain source diff may not apply).
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / 'ours.c').write_bytes(read(BEFORE, SOURCE))
        (d / 'base.c').write_bytes(read(SOURCE_FIX + '^', SOURCE))
        (d / 'theirs.c').write_bytes(read(SOURCE_FIX, SOURCE))
        layered = subprocess.run(['git', 'merge-file', '-p', 'ours.c', 'base.c', 'theirs.c'],
                                 cwd=d, capture_output=True, check=True).stdout
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
        'provenance': 'source change merged onto the before module == product module',
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
                env=dict(os.environ, RW185_PROFILE=str(out / 'profile'), RW185_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/respoiswar-185 finished: 1/1 passed' in text,
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
    assert not b['cold']['passed'] and a['cold']['passed']
    assert b['cold']['state'] == {'arescold': 4, 'arespois': 3, 'potion_reward': 900}
    assert a['cold']['state'] == {'arescold': 4, 'arespois': 3, 'potion_reward': 2400}
    assert b['plain']['passed'] and a['plain']['passed']
    assert b['plain']['log_sha256'] == a['plain']['log_sha256']
    assert a['plain']['state'] == {'arescold': 0, 'arespois': 3, 'potion_reward': 2400}
    assert all(r['outcome'] == {'potions_kept': 1} for r in (*b.values(), *a.values()))
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
