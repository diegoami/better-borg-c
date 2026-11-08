#!/usr/bin/env python3
"""Verify source403 (staircycle-403) with the unchanged native fixture.

A poisoned or hallucinating munchkin Borg could stair-cycle without advancing the world clock: stair
travel does not age the clock (level entry grants minimum move energy and the world tick is skipped
during level generation), so the timed ailment never wears off and the run freezes. The correction
adds one bail in the munchkin branch's early-bail sequence: while poisoned or hallucinating, leave
munchkin mode and hand the turn to the ordinary recovery path. The unchanged fixture has two modes:
`main` (ailments applied through the real timed-effect API: before the Borg flows to the stair, after
it hands the turn to recovery) and `clean` (a healthy control, byte-identical before/after).

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
BEFORE = '91f075bdcc329ec754e10e24da3cce36c5279784'
SOURCE_FIX = 'd92e06c3f964e4bba19642288ded1b331a327109'
EVIDENCE = 'eb36b06b524992d112cef4fc9ec51f8ea701c015'
PIN = '43dee40ed05284848f3df25aa5abf19a7f776c7f'
PREFIX = 'docs/audit/c-reports/staircycle-403/'
SOURCE = 'src/borg/borg-think-dungeon.c'
MODES = ('main', 'clean')


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
                env=dict(os.environ, STAIR403_PROFILE=str(out / 'profile'), STAIR403_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': ('native-c/staircycle-403 finished: 2/2 passed' in text) if mode == 'main'
                   else ('finished: 1/1 passed' in text),
                   'ailing_failed_as_expected': 'native-c/staircycle-403 finished: 1/2 passed' in text
                   and 'stair_directed=1' in text,
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
    # `main` runs two tests in one process: the ailing test then the clean test. Before, only
    # the ailing test fails (1/2, stair_directed=1); after, both pass (2/2).
    assert not b['main']['passed'] and b['main']['ailing_failed_as_expected']
    assert a['main']['passed'] and not a['main']['ailing_failed_as_expected']
    assert b['main']['outcome'] == {'stair_directed': 1, 'munchkin_handled': 1}
    assert a['main']['outcome'] == {'stair_directed': 0, 'munchkin_handled': 1}
    assert b['clean']['passed'] and a['clean']['passed']
    assert b['clean']['log_sha256'] == a['clean']['log_sha256']
    assert a['clean']['outcome'] == {'munchkin_handled': 1}
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
