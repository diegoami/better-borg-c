#!/usr/bin/env python3
"""Patch-retirement audit for the official angband master 574b618c3 import.

Official master 42cd156ac..574b618c3 contains upstream versions of three
local carries:

  0144 TPORTCHECK-593  95387b06f  borg-escape.c   landing check with either kind
  0092 HEALCHANCE-364  b5747369b  borg-caution.c  healing-chance signs
  0017 CBUG-0239       007bea95c  borg-trait.c    slays kept across slots

The unchanged tracker fixtures for the three carries run against three
builds, each with its own native gate result:

  before  the import head with only those three upstream commits reverted
          (a scratch commit; the defects present)
  carry   the pre-import product (the import merge's first parent), where
          the local carries supply the fixes
  after   the import head, where the upstream commits supply the fixes

Expected: every fixture's defect mode fails before and passes carry and
after with the outcome rows its carry verifier recorded; every control
passes in all three phases with a byte-identical log; and carry and after
logs are byte-identical for every mode, so the upstream form replaces each
carry on its fixture.  Normal (non-ASan) builds only.

Run under the shared native lock after the gate has run in each tree.
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
PREVIOUS = '42cd156ac9f95ddf4311e88dd7ad462292d6d1d6'
OFFICIAL = '574b618c3bfec595f3503a58f8e488b1c4ae3a46'
CARRY = 'b0bacee0697b5ca5ca2706d9335e24454bbdb4e9'
IMPORT_MERGE = 'ec5778b9201ac5ab97be8f6662df9e0bd1c1fb03'
SCOPE = ('src', 'lib', 'CMakeLists.txt', 'cmake')

FIXTURES = {
    'tportcheck-593': {
        'carry': '0144', 'upstream': '95387b06f384c63c75e05e9b7ce562fc73d2d3c4',
        'source': 'src/borg/borg-escape.c',
        'evidence': '382acb7b92bdcd004a144f7aca3403bf3e656dd7',
        'files': {'scenario.c': 'scenario.c', 'profile/borg.txt': 'profile/borg.txt'},
        'env': ('TC593_MODE', 'TC593_PROFILE'), 'suite': 'native-c/tportcheck-593',
        'modes': ('scrolls', 'control'), 'defect': 'scrolls', 'controls': ('control',),
        'extra_flags': (),
    },
    'healchance-364': {
        'carry': '0092', 'upstream': 'b5747369b3e61a711d8fba25f3678df51596a2df',
        'source': 'src/borg/borg-caution.c',
        'evidence': 'f88fee1e3ace2b5f34f6fc8a1b4fbc30d3f94da1',
        'pin': '3adc1b8128edfe31ca9a395d64f860b995396ec6',
        'files': {'scenario.c': 'scenario.c', 'borg.txt': 'profile/borg.txt'},
        'env': ('HC364_MODE', 'HC364_PROFILE'), 'suite': 'native-c/healchance-364',
        'modes': ('danger', 'unique', 'risky', 'control'),
        'defect': ('danger', 'unique', 'risky'), 'controls': ('control',),
        # As tools/verify-healchance.py: the kit calls tval_is_potion()
        # without including obj-tval.h; force the include rather than edit
        # the pinned fixture.
        'extra_flags': ('-include', 'obj-tval.h'),
    },
    'slay-239': {
        'carry': '0017', 'upstream': '007bea95ca6979eaaadb13758266b4dde0fa2e4d',
        'source': 'src/borg/borg-trait.c',
        'evidence': '25b0118631f108edc926856c8f4b3c35d3611bf9',
        'files': {'scenario.c': 'scenario.c', 'borg.txt': 'profile/borg.txt'},
        'env': ('S239_MODE', 'S239_PROFILE'), 'suite': 'native-c/slay-239',
        'modes': ('animal', 'nonanimal'), 'defect': 'animal', 'controls': ('nonanimal',),
        'extra_flags': (),
    },
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args, text=True):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=text)


def show(ref, name):
    return git('show', ref + ':' + name, text=False)


def check_outcomes(name, phase, rows):
    """The outcome rows each carry verifier recorded for its phases."""
    fixed = phase != 'before'
    if name == 'tportcheck-593':
        state = {'danger': 2000, 'curhp': 300, 'avoidance': 300, 'ateleport': 5}
        assert rows['scrolls']['state'] == dict(state, aescape=0), rows['scrolls']
        assert rows['control']['state'] == dict(state, aescape=6), rows['control']
        assert rows['scrolls']['outcome'] == (
            {'landing_ok': 1, 'uses_destruction': 0} if fixed
            else {'landing_ok': 0, 'uses_destruction': 1}), (phase, rows['scrolls'])
        assert rows['control']['outcome'] == {'landing_ok': 1, 'uses_destruction': 0}
    elif name == 'healchance-364':
        o = {m: rows[m]['outcome'] for m in rows}
        if fixed:
            assert o['danger']['heals'] == 100, (phase, o)
            assert o['danger']['witness_healed'] == 1 and o['danger']['drank_healing'] == 1
            assert o['unique']['heals'] == 32 and o['risky']['heals'] == 20, (phase, o)
        else:
            assert o['danger']['heals'] == 0, (phase, o)
            assert o['unique']['heals'] == 18 and o['risky']['heals'] == 27, (phase, o)
    elif name == 'slay-239':
        a, n = rows['animal']['outcome'], rows['nonanimal']['outcome']
        if fixed:
            assert a['auto'] == a['with'] > a['without'], (phase, a)
        else:
            assert a['auto'] == a['without'] < a['with'], (phase, a)
        assert n['auto'] == n['without'] == n['with'], (phase, n)


def run_fixture(name, spec, out, phases):
    work = out / name
    (work / 'profile').mkdir(parents=True)
    evidence = spec['evidence']
    for src, dst in spec['files'].items():
        (work / dst).write_bytes(show(evidence, 'docs/audit/c-reports/' + name + '/' + src))
    if 'pin' in spec:
        same = subprocess.run(
            ['git', 'diff', '--exit-code', spec['pin'], evidence, '--',
             *('docs/audit/c-reports/' + name + '/' + f for f in spec['files'])],
            cwd=ROOT, capture_output=True)
        assert same.returncode == 0, name + ': runtime fixtures changed since the run pin'
    var_mode, var_profile = spec['env']
    result = {'fixture_commit': evidence, 'fixture_sha256': sha(work / 'scenario.c'),
              'carry': spec['carry'], 'upstream_commit': spec['upstream'],
              'source': spec['source'], 'phases': {}}
    for phase, core in phases.items():
        cache = (core / 'CMakeCache.txt').read_text(errors='replace')
        home = Path(next(line.split('=', 1)[1].strip() for line in cache.splitlines()
                         if line.startswith('CMAKE_HOME_DIRECTORY')))
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers, (phase, core)
        binary = work / (phase + '-scenario')
        # Each phase compiles the scenario against its own tree's headers.
        command = ['cc', '-g', '-DALLOW_BORG', *spec['extra_flags'],
                   '-I' + str(home / 'src'), '-I' + str(home / 'src/tests'),
                   str(work / 'scenario.c'), *map(str, objects + helpers),
                   '-lm', '-o', str(binary)]
        with (work / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in spec['modes']:
            run = subprocess.run(
                [str(binary), '-v'], cwd=core / 'game',
                env=dict(os.environ, **{var_mode: mode, var_profile: str(work / 'profile')},
                         LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', run.stdout.decode(errors='replace'))
            log = work / f'{phase}-{mode}.log'
            log.write_text(text)
            parsed = {}
            for tag, key in (('STATE ', 'state'), ('OUTCOME ', 'outcome')):
                row = {}
                for match in re.findall(re.escape(tag) + r'(.*)', text):
                    row.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match)})
                parsed[key] = row
            rows[mode] = {'exit': run.returncode,
                          'passed': spec['suite'] + ' finished: 1/1 passed' in text,
                          'state': parsed['state'], 'outcome': parsed['outcome'],
                          'log_sha256': sha(log)}
            print(name, phase, mode, rows[mode], flush=True)
        result['phases'][phase] = {'cases': rows, 'command': command,
                                   'binary_sha256': sha(binary)}
    defects = spec['defect'] if isinstance(spec['defect'], tuple) else (spec['defect'],)
    cases = {phase: data['cases'] for phase, data in result['phases'].items()}
    for phase, rows in cases.items():
        for mode, row in rows.items():
            assert row['exit'] == 0, (name, phase, mode)
            expected = mode not in defects or phase != 'before'
            assert row['passed'] is expected, (name, phase, mode, row)
        check_outcomes(name, phase, rows)
    for mode in spec['controls']:
        hashes = {cases[p][mode]['log_sha256'] for p in cases}
        assert len(hashes) == 1, (name, mode, 'control changed')
    replaced = {mode: cases['carry'][mode]['log_sha256'] == cases['after'][mode]['log_sha256']
                for mode in spec['modes']}
    result['carry_after_logs_identical'] = replaced
    assert all(replaced.values()), (name, 'upstream form differs from the carry', replaced)
    result['verified'] = True
    return result


def provenance(before_commit, product_commit):
    """Before tree == product with exactly the three upstream commits reverted."""
    changed = git('diff', '--name-only', before_commit, product_commit, '--', *SCOPE).split()
    assert sorted(changed) == sorted(f['source'] for f in FIXTURES.values()), changed
    for name, spec in FIXTURES.items():
        upstream, source = spec['upstream'], spec['source']
        assert git('diff', '--name-only', upstream + '^', upstream).split() == [source], name
        subprocess.run(['git', 'merge-base', '--is-ancestor', upstream, OFFICIAL],
                       cwd=ROOT, check=True)
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / source).parent.mkdir(parents=True)
            (d / source).write_bytes(show(before_commit, source))
            subprocess.run(['patch', '-p1', '-s'], cwd=d, check=True,
                           input=git('diff', upstream + '^', upstream, '--', source, text=False))
            layered = (d / source).read_bytes()
        assert show(product_commit, source) == layered, name + ': product != before + upstream'


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--before-tree', required=True, type=Path,
                   help='checkout of the scratch before commit, gate already run')
    p.add_argument('--carry-tree', required=True, type=Path,
                   help='checkout of the pre-import product, gate already run')
    p.add_argument('--product-tree', default=ROOT, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)

    trees = {'before': args.before_tree.resolve(), 'carry': args.carry_tree.resolve(),
             'after': args.product_tree.resolve()}
    gates = {}
    for phase, tree in trees.items():
        gate = json.loads((tree / 'artifacts/native/result.json').read_text())
        assert gate['success'], phase
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tree, text=True).strip()
        subprocess.run(['git', 'diff', '--exit-code', gate['commit'], commit, '--', *SCOPE],
                       cwd=tree, check=True)
        gates[phase] = gate

    # The import merge joins the pre-import product and official master.  It is
    # pinned: a message search also matches later merges that quote its subject.
    merge = IMPORT_MERGE
    assert git('rev-parse', merge + '^1').strip() == CARRY
    assert git('rev-parse', merge + '^2').strip() == OFFICIAL
    subprocess.run(['git', 'merge-base', '--is-ancestor', PREVIOUS, CARRY], cwd=ROOT, check=True)
    assert gates['carry']['commit'] == CARRY
    # The after gate may sit on any descendant of the import whose game files
    # equal the import's (the merge itself, the release tag, a later main).
    after_commit = gates['after']['commit']
    subprocess.run(['git', 'merge-base', '--is-ancestor', merge, after_commit],
                   cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--quiet', merge, after_commit, '--', *SCOPE],
                   cwd=ROOT, check=True)
    # The before commit is a scratch commit whose parent has those same game
    # files; provenance() then checks it differs only by the reverted hunks.
    before_commit = gates['before']['commit']
    git('cat-file', '-e', before_commit + '^{commit}')
    subprocess.run(['git', 'diff', '--quiet', before_commit + '^', merge, '--', *SCOPE],
                   cwd=ROOT, check=True)
    provenance(before_commit, after_commit)

    report = {'official': OFFICIAL, 'previous_official': PREVIOUS, 'import_merge': merge,
              'gates': gates,
              'binaries_sha256': {p: sha(t / 'build/native/game/angband') for p, t in trees.items()},
              'provenance': 'before = product with the three upstream commits reverted; '
                            'product module == before module + upstream diff, per file',
              'fixtures': {}, 'verified': False}
    phases = {p: t / 'build/native' for p, t in trees.items()}
    for name, spec in FIXTURES.items():
        report['fixtures'][name] = run_fixture(name, spec, out, phases)
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('verified', out / 'result.json')


if __name__ == '__main__':
    main()
