#!/usr/bin/env python3
"""Verify source589: model protection from stun separately from sound resistance (fix 3088b91d9).

Several attacks can stun: gravity, plasma and force breath, water balls
and bolts, storms, plasma bolts and ice bolts.  In the game, only
protection from stun stops their stun; sound resistance stops only
sound's stun.  borg_danger() adds a large penalty (+500) when an already
stunned Borg faces a stunning attack, but for all of these attacks it
asked for sound resistance (BI_RSND) instead of stun protection, so the
penalty was skipped for a sound-resistant Borg (danger 156 instead of
656, under-rating a possibly lethal position) and applied anyway for a
stun-protected one without sound resistance (656 instead of 156).

Add a protection-from-stun trait (BI_PSTUN, set from player flags and
worn items), use it for the eight non-sound stun guards, and make the
sound breath check BI_RSND || BI_PSTUN.

The kit is the source lane's unchanged native-c/stunprot-589 fixture.
Expected: rsound and pstun fail before with the penalty applied to the
wrong Borg and pass after with the corrected danger; both and the
unstunned control pass in both phases, the control byte-identical.

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
BEFORE = '29af41256d135e6968936ad7ab216bdc01b369d7'
FIX = '3088b91d965ca483917377e4e1553329b7e292e8'
FIX_BASE = '42cd156ac9f95ddf4311e88dd7ad462292d6d1d6'
EVIDENCE = '29af41256d135e6968936ad7ab216bdc01b369d7'
PREFIX = 'docs/audit/c-reports/stunprot-589/'
SOURCES = ['src/borg/borg-danger.c', 'src/borg/borg-trait.c', 'src/borg/borg-trait.h']
SUITE = 'native-c/stunprot-589'
MODES = ('rsound', 'pstun', 'both', 'rsound-unstunned')
EXPECT = {m: (True, True) for m in MODES}
EXPECT['rsound'] = (False, True)
EXPECT['pstun'] = (False, True)
CALM = {'danger': 156, 'calm': 156, 'stun_penalty': 0}
HOT = {'danger': 656, 'calm': 156, 'stun_penalty': 500}
STATES = {
    'rsound': {'rsound': 1, 'isstun': 1, 'avoidance': 402},
    'pstun': {'rsound': 0, 'isstun': 1, 'avoidance': 402},
    'both': {'rsound': 1, 'isstun': 1, 'avoidance': 402},
    'rsound-unstunned': {'rsound': 1, 'isstun': 0, 'avoidance': 402},
}
BEFORE_ROWS = {
    'rsound': {'outcome': dict(CALM)},          # penalty wrongly skipped
    'pstun': {'outcome': dict(HOT)},            # penalty applied anyway
    'both': {'outcome': dict(CALM)},
    'rsound-unstunned': {'outcome': dict(CALM)},
}
ROWS = {
    'rsound': {'outcome': dict(HOT)},
    'pstun': {'outcome': dict(CALM)},
    'both': {'outcome': dict(CALM)},
    'rsound-unstunned': {'outcome': dict(CALM)},
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

    source_diff = subprocess.check_output(['git', 'diff', FIX_BASE, FIX], cwd=ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        for source in SOURCES:
            (d / source).parent.mkdir(parents=True, exist_ok=True)
            (d / source).write_bytes(read(BEFORE, source))
        applied = subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d)
        assert applied.returncode == 0, 'source diff does not apply to the before modules'
        for source in SOURCES:
            assert (ROOT / source).read_bytes() == (d / source).read_bytes(), \
                'product module != before + source diff: ' + source
    fix_scope = subprocess.check_output(
        ['git', 'diff', '--name-only', FIX_BASE, FIX, '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert fix_scope == sorted(SOURCES), fix_scope
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', BEFORE, 'HEAD', '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert changed == sorted(SOURCES), changed
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
        'provenance': 'source diff applied to the before modules == product modules',
        'before_commit': BEFORE,
        'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': head,
        'product_native_gate': product_gate,
        'product_binary_sha256': sha(build / 'game/angband'),
        'phases': {}, 'verified': False,
    }
    for phase, core in (('before', before), ('after', build)):
        # Compile the scenario against THIS build's own headers, not the
        # working tree's: the fix touches borg-trait.h, and a header from
        # the wrong phase shifts every trait enum index after the insert.
        cache = (core / 'CMakeCache.txt').read_text(errors='replace')
        home = next(line.split('=', 1)[1].strip() for line in cache.splitlines()
                    if line.startswith('CMAKE_HOME_DIRECTORY'))
        home = Path(home)
        assert (home / 'src/borg/borg-trait.h').exists(), home
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
                env=dict(os.environ, **{'SP589_MODE': mode,
                                        'SP589_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            parsed = {}
            for tag, key in (('STATE ', 'state'), ('OUTCOME ', 'outcome')):
                row = {}
                for match in re.findall(re.escape(tag) + r'(.*)', text):
                    row.update({k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match)})
                parsed[key] = row
            rows[mode] = {
                'exit': result.returncode,
                'passed': SUITE + ' finished: 1/1 passed' in text,
                'state': parsed.get('state', {}),
                'outcome': parsed.get('outcome', {}),
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
        assert b[mode]['state'] == STATES[mode], ('before state', mode, b[mode]['state'])
        assert a[mode]['state'] == STATES[mode], ('after state', mode, a[mode]['state'])
        assert b[mode]['outcome'] == BEFORE_ROWS[mode]['outcome'], ('before rows', mode, b[mode]['outcome'])
        assert a[mode]['outcome'] == ROWS[mode]['outcome'], ('after rows', mode, a[mode]['outcome'])
    assert b['rsound-unstunned']['log_sha256'] == a['rsound-unstunned']['log_sha256'], 'control changed'
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
