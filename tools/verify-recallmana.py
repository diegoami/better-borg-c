#!/usr/bin/env python3
"""Verify source157 (recallmana-157) with the unchanged native fixture.

borg_caution()'s recall-wait branch tested `BI_CURSP < BI_CURSP / 4`, never true
for positive mana, so a high-mana caster in danger while Recall is pending never
used a restore-mana item to buy time. The correction compares with
`BI_MAXSP / 4`. The unchanged fixture has two modes: `lowmana` (sp 19 of 193:
before no restore, after restore) and `halfmana` (sp 96 of 193: no restore,
byte-identical before/after).

Layered interaction: after patch 0053 (source156) an ordinary Borg in excessive
danger takes the flee and desperate-stairs branch before reaching this line, so
the UNCHANGED source fixture (ready_morgoth = 0, recorded on pristine code where
that branch was inverted) no longer reaches it and stays red on both builds.
That is asserted, not hidden. The adapted fixture changes exactly one line,
`borg.ready_morgoth = 0` to `1` (a Morgoth-ready caster skips the flee branch,
as the pristine run did), and carries the fail-before/pass-after proof.

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
BEFORE = '9cb711cd2fc7bb5ee45530c61bd25a063253492b'
SOURCE_FIX = '57d0df0633d12064602993f39fe6a5ee5f62524c'
EVIDENCE = '5a8572e08e24321cce00e65a4c2c7832c4a1315d'
PIN = 'b6bd252e1c9b60845cd3824f42d7dbc5100d2b63'
PREFIX = 'docs/audit/c-reports/recallmana-157/'
SOURCE = 'src/borg/borg-caution.c'
MODES = ('lowmana', 'halfmana')


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

    original = read(EVIDENCE, PREFIX + 'scenario.c')
    (out / 'scenario.c').write_bytes(original)
    line = b'borg.ready_morgoth = 0;'
    assert original.count(line) == 1
    (out / 'scenario-adapted.c').write_bytes(original.replace(line, b'borg.ready_morgoth = 1;'))
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
    for variant, source in (('source', 'scenario.c'), ('adapted', 'scenario-adapted.c')):
     for phase, core in (('before', before), ('after', build)):
         objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
         helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
         assert len(objects) >= 150 and helpers
         binary = out / (variant + '-' + phase + '-scenario')
         command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                    '-I' + str(ROOT / 'src/tests'), str(out / source),
                    *map(str, objects + helpers), '-lm', '-o', str(binary)]
         with (out / (variant + '-' + phase + '-link.log')).open('w') as log:
             subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
         rows = {}
         for mode in MODES:
             result = subprocess.run(
                 [str(binary), '-v'], cwd=build / 'game',
                 env=dict(os.environ, RM157_PROFILE=str(out / 'profile'), RM157_MODE=mode, LC_ALL='C.UTF-8'),
                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
             text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
             log = out / f'{variant}-{phase}-{mode}.log'
             log.write_text(text)
             row = {'exit': result.returncode,
                    'passed': 'native-c/recallmana-157 finished: 1/1 passed' in text,
                    'log_sha256': sha(log)}
             for tag, key in (('STATE ', 'state'), ('OUTCOME ', 'outcome')):
                 m = re.search(re.escape(tag) + r'.*', text)
                 if m:
                     row[key] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', m[0])}
             rows[mode] = row
             print(variant, phase, mode, row, flush=True)
         report['phases'][variant + '-' + phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary)}
         (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    ph = report['phases']
    for key in ph:
        assert all(r['exit'] == 0 for r in ph[key]['cases'].values()), key
    sb, sa = ph['source-before']['cases'], ph['source-after']['cases']
    # Unchanged source fixture: red on both builds because patch 0053 flees first.
    for c in (sb, sa):
        assert not c['lowmana']['passed'] and c['lowmana']['outcome'] == {'restore_mana': 0}
        assert c['halfmana']['passed'] and c['halfmana']['outcome'] == {'restore_mana': 0}
    assert sb['lowmana']['log_sha256'] == sa['lowmana']['log_sha256']
    b, a = ph['adapted-before']['cases'], ph['adapted-after']['cases']
    assert not b['lowmana']['passed'] and a['lowmana']['passed']
    assert b['lowmana']['outcome'] == {'restore_mana': 0} and a['lowmana']['outcome'] == {'restore_mana': 1}
    assert b['lowmana']['state']['sp'] == 19 and b['lowmana']['state']['maxsp'] == 193
    assert b['halfmana']['passed'] and a['halfmana']['passed']
    assert b['halfmana']['log_sha256'] == a['halfmana']['log_sha256']
    assert a['halfmana']['outcome'] == {'restore_mana': 0}
    for mode in MODES:
        assert b[mode]['state'] == a[mode]['state'], mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
