#!/usr/bin/env python3
"""Verify source142 (cfgminus-142) with the unchanged native fixture.

borg_proc_setting() negated a setting after the character loop whether or not a
number followed the minus sign, so a bare minus (or an overflowing value) flipped
the sign of a stale or default value. The correction negates only when a number
was read. The unchanged fixture has three modes: `minus` (a bare minus: before
the setting is -127 and the Borg is not prepared at depth 20, after it keeps its
default 127 and is), `valid` (100) and `negative` (-5), both byte-identical.

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
BEFORE = '052129ae5b7e072513b80ac2626d82792e6a8463'
SOURCE_FIX = '6bc43e71a4b36189ba7246abe53f114d6259469c'
EVIDENCE = '0a21f5ce0cfdadfb1d3520480425a337bab5f752'
PIN = '18f79a3cc631b76b55524e9253a79f383fd6d9a3'
PREFIX = 'docs/audit/c-reports/cfgminus-142/'
SOURCE = 'src/borg/borg-init.c'
MODES = ('minus', 'valid', 'negative')


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

    # Stacked carries: the source diff is against pristine, so prove provenance by
    # merging the source change (source parent -> source fix) onto the before module.
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / 'ours.c').write_bytes(read(BEFORE, SOURCE))
        (d / 'base.c').write_bytes(read(SOURCE_FIX + '^', SOURCE))
        (d / 'theirs.c').write_bytes(read(SOURCE_FIX, SOURCE))
        merged = subprocess.run(['git', 'merge-file', '-p', 'ours.c', 'base.c', 'theirs.c'],
                                cwd=d, capture_output=True, check=True).stdout
        layered = merged
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
                env=dict(os.environ, CN142_PROFILE=str(out / 'profile'), CN142_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/cfgminus-142 finished: 1/1 passed' in text,
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
    assert not b['minus']['passed'] and a['minus']['passed']
    assert b['minus']['state'] == {'no_deeper': -127} and a['minus']['state'] == {'no_deeper': 127}
    assert b['minus']['outcome'] == {'prepared20': 0} and a['minus']['outcome'] == {'prepared20': 1}
    for mode, v in (('valid', 100), ('negative', -5)):
        assert b[mode]['passed'] and a[mode]['passed']
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], mode
        assert a[mode]['state'] == {'no_deeper': v}, mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
