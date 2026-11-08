#!/usr/bin/env python3
"""Verify source144 (cfgmissing-144) with the unchanged native fixture.

borg_init_txt_file() allocated the configuration only after reopening borg.txt,
so a borg.txt that could not be read or written left the configuration (and the
file pointer) NULL and the Borg crashed. The correction allocates the defaults
first and returns with a warning when the reopen fails. The unchanged fixture has
two modes: `missing` (before the process crashes with a non-zero exit, after it
initialises with default settings) and `present` (normal, byte-identical).

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
BEFORE = '0ceeaadbb62a0fd2d4d09e38816023de21a4e630'
SOURCE_FIX = '8cbee69447cda2526b4810fd6ea74677921ff1d1'
EVIDENCE = 'f37cc9b515e361913a6c680451c4ceab62e3f51c'
PIN = '1ff9ca1e59d639b6693b9bcb40190c6d836c6fa9'
PREFIX = 'docs/audit/c-reports/cfgmissing-144/'
SOURCE = 'src/borg/borg-init.c'
MODES = ('missing', 'present')


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
                env=dict(os.environ, CM144_PROFILE=str(out / 'profile'), CM144_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/cfgmissing-144 finished: 1/1 passed' in text,
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
    assert b['missing']['exit'] != 0 and not b['missing']['passed']
    assert b['missing']['outcome'] == {'init_completed': 0, 'crashed': 1}
    assert a['missing']['exit'] == 0 and a['missing']['passed']
    assert a['missing']['outcome'] == {'init_completed': 1, 'crashed': 0}
    assert a['missing']['state'] == {'init_failure': 0, 'stop_dlevel': 128}
    assert b['present']['exit'] == a['present']['exit'] == 0 and b['present']['passed'] and a['present']['passed']
    assert b['present']['log_sha256'] == a['present']['log_sha256']
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
