#!/usr/bin/env python3
"""Verify source141 (cfghang-141) with the unchanged native fixture.

borg_proc_setting() looped forever on an integer setting whose value starts with
an unexpected character (a word, or a number with a suffix the scanner does not
consume): the character loop never advanced. The correction stops reading the
value at the first unexpected character and keeps the default. The unchanged
fixture has three modes: `word` and `suffix` (before the Borg initialisation
hangs and the scenario's watchdog exits non-zero; after it completes with the
default) and `valid` (a normal value, byte-identical before/after).

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
BEFORE = '20d7d4e6203d976a6fd294818d6e74c73eb94ad7'
SOURCE_FIX = '45dfc9b1f4930b28841d0c38b73cc4cd3171aab0'
EVIDENCE = '096ee66813dad5a32f9468d5fff2c48d2a46077c'
PIN = 'a3164a61b830bf1c67e10017f9a2be7dec9a1763'
PREFIX = 'docs/audit/c-reports/cfghang-141/'
SOURCE = 'src/borg/borg-init.c'
MODES = ('word', 'suffix', 'valid')


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
                env=dict(os.environ, CH141_PROFILE=str(out / 'profile'), CH141_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/cfghang-141 finished: 1/1 passed' in text,
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
    for mode in ('word', 'suffix'):
        assert b[mode]['exit'] != 0 and not b[mode]['passed'], mode
        assert b[mode]['outcome'] == {'init_completed': 0, 'hung': 1}, mode
        assert a[mode]['exit'] == 0 and a[mode]['passed'], mode
        assert a[mode]['outcome'] == {'init_completed': 1, 'hung': 0}, mode
        assert a[mode]['state'] == {'init_failure': 0, 'stop_dlevel': 128}, mode
    assert b['valid']['exit'] == a['valid']['exit'] == 0 and b['valid']['passed'] and a['valid']['passed']
    assert b['valid']['log_sha256'] == a['valid']['log_sha256']
    assert a['valid']['state'] == {'init_failure': 0, 'stop_dlevel': 7}
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
