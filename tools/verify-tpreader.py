#!/usr/bin/env python3
"""Verify source250 (tpreader-250) with the unchanged native fixture.

borg_danger_one_kill()'s Teleport Other exclusion loop ran to
`ii <= borg_tp_other_n`, one slot past the saved entries, so a stale index
left there by a longer earlier evaluation excluded an adjacent giant's whole
danger. The product already contains the identical one-token correction
through the source67 carry (commit 706fb49b0, which fixed the same line while
skipping only listed candidates), so no new patch is applied for source250.

This verifier proves that overlap on the unchanged source fixture: the
product (`--after-build`) is compared with a build of the same tree whose
only difference is that single line restored to the pristine `<=`
(`--before-build`). The two source trees are diffed here and must differ by
exactly that token. The fixture's three modes run on each: `stale-hit`
fails before and passes after; `in-list` and `empty` controls are
byte-identical logs.

No sanitizer phase: the stale slot lies inside the allocated array, so the
source evidence also records no sanitizer report; this is a logic defect.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FIX = 'e890819a6b5ac6e7f7135dcc2b234fcc520b9752'
EVIDENCE = '9ca89f4461e518f28c85962a51aaa6308e0b0158'
PIN = '6f6710ccc3a3dc1b035544338444048b2f7cbced'
PREFIX = 'docs/audit/c-reports/tpreader-250/'
SOURCE = 'src/borg/borg-danger.c'
MODES = ('stale-hit', 'in-list', 'empty')
OLD = '        for (ii = 0; ii <= borg_tp_other_n; ii++) {\n'
NEW = '        for (ii = 0; ii < borg_tp_other_n; ii++) {\n'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path,
                   help='core build dir of the tree with the pristine `<=` restored')
    p.add_argument('--before-tree', required=True, type=Path)
    p.add_argument('--after-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--after-tree', default=ROOT, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()

    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)

    for name in ('scenario.c', 'borg.txt'):
        target = out / ('profile/borg.txt' if name == 'borg.txt' else name)
        target.write_bytes(read(EVIDENCE, PREFIX + name))
    same = subprocess.run(
        ['git', 'diff', '--exit-code', PIN, EVIDENCE, '--',
         PREFIX + 'scenario.c', PREFIX + 'borg.txt'], cwd=ROOT, capture_output=True)
    assert same.returncode == 0, 'runtime fixtures changed since the run pin'

    before_src = (args.before_tree / SOURCE).read_text()
    after_src = (args.after_tree / SOURCE).read_text()
    assert before_src.count(OLD) == 1 and after_src.count(NEW) == 1
    assert before_src.replace(OLD, NEW) == after_src, 'trees differ by more than the loop bound'
    diff = list(difflib.unified_diff(before_src.splitlines(), after_src.splitlines(), lineterm='', n=0))
    changed = [d for d in diff if d[:1] in '+-' and d[:3] not in ('+++', '---')]
    assert len(changed) == 2, changed
    # The after tree is this product: its commit must contain the fix text.
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.after_tree, text=True).strip()
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', SOURCE], cwd=args.after_tree, check=True)
    # Source-fix diff equals the one-token change (provenance of the overlap).
    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT, text=True)
    src_changed = [l for l in source_diff.splitlines()
                   if l[:1] in '+-' and l[:3] not in ('+++', '---')]
    assert [l[1:] for l in src_changed] == [OLD.rstrip('\n'), NEW.rstrip('\n')] or \
        [l[1:].strip() for l in src_changed] == [OLD.strip(), NEW.strip()], src_changed
    overlap = subprocess.check_output(
        ['git', 'log', '--format=%H', '-S', 'ii < borg_tp_other_n', '--', SOURCE],
        cwd=args.after_tree, text=True).split()

    report = {
        'fixture_commit': EVIDENCE, 'fixture_pin': PIN,
        'fixture_sha256': sha(out / 'scenario.c'),
        'source_fix': FIX,
        'product_commit': head,
        'line_introduced_in_product_by': overlap,
        'tree_diff': changed,
        'source_before_sha256': hashlib.sha256(before_src.encode()).hexdigest(),
        'source_after_sha256': hashlib.sha256(after_src.encode()).hexdigest(),
        'phases': {}, 'verified': False,
    }
    for phase, core in (('before', args.before_build.resolve()), ('after', args.after_build.resolve())):
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
                [str(binary), '-v'], cwd=args.after_build.resolve() / 'game',
                env=dict(os.environ, TP250_PROFILE=str(out / 'profile'),
                         TP250_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode,
                   'passed': 'native-c/tpreader-250 finished: 1/1 passed' in text,
                   'log_sha256': sha(log)}
            for tag, key in (('SETUP n=', 'setup'), ('DANGER ', 'danger')):
                m = re.search(re.escape(tag) + r'.*', text)
                if m:
                    row[key] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', m[0])}
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    b, a = report['phases']['before']['cases'], report['phases']['after']['cases']
    assert all(r['exit'] == 0 for r in (*b.values(), *a.values()))
    assert not b['stale-hit']['passed'] and b['stale-hit']['danger']['danger'] == 0
    assert a['stale-hit']['passed'] and a['stale-hit']['danger']['danger'] == 179
    assert a['stale-hit']['setup']['n'] == 1
    for mode, danger in (('in-list', 0), ('empty', 179)):
        assert b[mode]['passed'] and a[mode]['passed']
        assert b[mode]['danger']['danger'] == a[mode]['danger']['danger'] == danger
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
