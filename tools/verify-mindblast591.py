#!/usr/bin/env python3
"""Verify source591: model Mind Blast as 8d8 damage plus confusion (fix 9a9fb3ce8).

The Mind Blast spell case of borg_danger() scored the damage as
spell_power/2+1, a 3.x-era figure.  In 4.2 Mind Blast is an 8d8 attack
with a confusion side effect, so the borg underrated casters that carry
it: at the measured position the whole Mind Blast term was 9 of a danger
40 dominated by the Wound spell, where the game's 64 plus the confusion
term gives 74.  Score the damage as the 8d8 maximum and add the
confusion term.

The kit is the source lane's unchanged native-c/mindblast-591 fixture.
Expected: the nar mode (Nár, the Dwarf, four grids away) fails before
(danger 40) and passes after (danger 74); the illusionist control passes
in both phases and is byte-identical between the phases.

Run under the shared native lock after this tree's gate build, with the
before snapshot built at the before commit (its gate result recorded
under --before-gate).
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
BEFORE = '623148199e1f1eed3e583275fb6c21dd4141a7f5'
FIX = '9a9fb3ce8fbfe2b01725e92a9ec04e5facb64af1'
FIX_BASE = '42cd156ac9f95ddf4311e88dd7ad462292d6d1d6'
EVIDENCE = '623148199e1f1eed3e583275fb6c21dd4141a7f5'
PREFIX = 'docs/audit/c-reports/mindblast-591/'
SOURCE = 'src/borg/borg-danger.c'
SUITE = 'native-c/mindblast-591'
MODES = ('nar', 'control')
EXPECT = {m: (True, True) for m in MODES}
EXPECT['nar'] = (False, True)
BEFORE_ROWS = {
    'nar': {'outcome': {'danger': 40}},
    'control': {'outcome': {'danger': 600}},
}
ROWS = {
    'nar': {'outcome': {'danger': 74}},
    'control': {'outcome': {'danger': 600}},
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-gate', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--product-gate', default=ROOT / 'artifacts/native/result.json', type=Path)
    p.add_argument('--fix', required=True, help='applied product commit')
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()

    evidence = subprocess.check_output(
        ['git', 'rev-parse', EVIDENCE], cwd=ROOT, text=True).strip()

    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)

    (out / 'scenario.c').write_bytes(read(evidence, PREFIX + 'scenario.c'))
    (out / 'profile/borg.txt').write_bytes(read(evidence, PREFIX + 'profile/borg.txt'))
    for name in ('scenario.c', 'profile/borg.txt'):
        assert (ROOT / PREFIX / name).read_bytes() == (out / name).read_bytes(), \
            'working-tree fixture differs from its commit: ' + name

    before, build = args.before_build.resolve(), args.product_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX_BASE, FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / SOURCE).parent.mkdir(parents=True)
        (d / SOURCE).write_bytes(read(BEFORE, SOURCE))
        applied = subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d)
        assert applied.returncode == 0, 'source diff does not apply to the before module'
        layered = (d / SOURCE).read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered, 'product module != before + source diff'
    fix_scope = subprocess.check_output(
        ['git', 'diff', '--name-only', FIX_BASE, FIX, '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert fix_scope == [SOURCE], fix_scope
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', BEFORE, 'HEAD', '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert changed == [SOURCE], changed
    subprocess.run(['git', 'merge-base', '--is-ancestor', args.fix, 'HEAD'], cwd=ROOT, check=True)

    before_gate = json.loads(args.before_gate.resolve().read_text())
    assert before_gate['success'] and before_gate['commit'] == BEFORE
    product_gate = json.loads(args.product_gate.resolve().read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert product_gate['success']
    subprocess.run(['git', 'merge-base', '--is-ancestor', product_gate['commit'], 'HEAD'],
                   cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--exit-code', product_gate['commit'], 'HEAD', '--',
                    'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)

    report = {
        'fixture_commit': evidence,
        'fixture_sha256': sha(out / 'scenario.c'),
        'source_fix': FIX, 'fix': args.fix,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE,
        'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': head,
        'product_native_gate': product_gate,
        'product_binary_sha256': sha(build / 'game/angband'),
        'phases': {}, 'verified': False,
    }
    for phase, core in (('before', before), ('after', build)):
        # Compile the scenario against THIS build's own headers (per-phase
        # include roots; the pattern from the source589 verifier).
        cache = (core / 'CMakeCache.txt').read_text(errors='replace')
        home = next(line.split('=', 1)[1].strip() for line in cache.splitlines()
                    if line.startswith('CMAKE_HOME_DIRECTORY'))
        home = Path(home)
        assert (home / 'src/borg/borg-trait.c').exists(), home
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(home / 'src'),
                   '-I' + str(home / 'src/tests'), str(out / 'scenario.c'),
                   *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, **{'MB591_MODE': mode,
                                        'MB591_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            outcome = {}
            for omatch in re.findall(r'OUTCOME (.*)', text):
                outcome.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch)})
            rows[mode] = {
                'exit': result.returncode,
                'passed': SUITE + ' finished: 1/1 passed' in text,
                'outcome': outcome,
                'log_sha256': sha(log),
                'capture_byte_identical': log.read_bytes() == (ROOT / PREFIX / f'{phase}-{mode}.log').read_bytes(),
            }
            print(phase, mode, rows[mode], flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command,
                                   'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    b, a = report['phases']['before']['cases'], report['phases']['after']['cases']
    for mode in MODES:
        assert b[mode]['exit'] == 0 and a[mode]['exit'] == 0, mode
        assert b[mode]['passed'] is EXPECT[mode][0], ('before pass', mode)
        assert a[mode]['passed'] is EXPECT[mode][1], ('after pass', mode)
        assert b[mode]['outcome'] == BEFORE_ROWS[mode]['outcome'], ('before rows', mode, b[mode]['outcome'])
        assert a[mode]['outcome'] == ROWS[mode]['outcome'], ('after rows', mode, a[mode]['outcome'])
    assert b['control']['log_sha256'] == a['control']['log_sha256'], 'control changed'
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
