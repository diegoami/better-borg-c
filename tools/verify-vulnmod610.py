#!/usr/bin/env python3
"""Verify source610: model unresisted elemental vulnerability in borg_danger() (fix 16a8ac653, stacked on 82fd25a54).

After the vulnerability-cancels-resistance correction (#594), a
resistance cancelled by a vulnerability and a never-resisted element look
the same in BI_RFIRE, but the game treats them differently: an unresisted
elemental vulnerability takes 4/3 damage, and temporary resistance
cancels the vulnerability's multiplier.  The 17 element cases of
borg_danger() applied neither.

Add traits BI_VFIRE, BI_VELEC, BI_VCOLD and BI_VACID recording a
vulnerability that has no permanent resistance to cancel, and apply 4/3
in the element cases without temporary resistance and no reduction with
it.

The kit is the source lane's unchanged native-c/vulnmod-610 fixture,
whose before-tree already contains the #594 correction (the consumer's
0136 carry provides it).  Expected: vuln and temp fail before (the
multiplier is not applied; temporary resistance wrongly cancels the
vulnerability) and pass after; the control passes in both phases and is
byte-identical between the phases.

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
BEFORE = 'cb8c51fcb6ee67d683dc94cd5ab320f45b89b1b3'
FIX = '16a8ac653bc4f6e9564f7b914358a1ebe8a16e1f'
# The source fix is stacked on the #594 correction; the stacked delta is
# 82fd25a54..16a8ac653 (the consumer's 0136 provides the base content).
FIX_BASE = '82fd25a5477054a0727ab920701b7555898586b2'
EVIDENCE = 'cb8c51fcb6ee67d683dc94cd5ab320f45b89b1b3'
PREFIX = 'docs/audit/c-reports/vulnmod-610/'
SOURCES = ['src/borg/borg-danger.c', 'src/borg/borg-trait.c', 'src/borg/borg-trait.h']
SUITE = 'native-c/vulnmod-610'
MODES = ('vuln', 'temp', 'control')
EXPECT = {m: (True, True) for m in MODES}
EXPECT['vuln'] = (False, True)
EXPECT['temp'] = (False, True)


def state(lvl, ref, rfire, temp, vuln):
    return {'game_fire_res_level': lvl, 'reference_game_fire_res_level': ref,
            'borg_rfire': rfire, 'borg_temp_rfire': temp, 'borg_fire_vuln': vuln}


BEFORE_ROWS = {
    'vuln': {'state': state(-1, 0, 0, 0, 1), 'outcome': {'danger': 137, 'reference': 137}},
    'temp': {'state': state(0, 0, 0, 1, 1), 'outcome': {'danger': 73, 'reference': 137}},
    'control': {'state': state(0, 0, 0, 0, 1), 'outcome': {'danger': 137, 'reference': 137}},
}
ROWS = {
    'vuln': {'state': state(-1, 0, 0, 0, 1), 'outcome': {'danger': 169, 'reference': 137}},
    'temp': {'state': state(0, 0, 0, 1, 1), 'outcome': {'danger': 137, 'reference': 137}},
    'control': {'state': state(0, 0, 0, 0, 1), 'outcome': {'danger': 137, 'reference': 137}},
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
        'source_fix_base': FIX_BASE,
        'provenance': 'stacked source diff (82fd25a54..16a8ac653) applied to the before modules == product modules',
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
        # include roots; this fix adds four enum entries to borg-trait.h).
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
                env=dict(os.environ, **{'VM610_MODE': mode,
                                        'VM610_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
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
        assert b[mode]['state'] == BEFORE_ROWS[mode]['state'], ('before state', mode, b[mode]['state'])
        assert b[mode]['outcome'] == BEFORE_ROWS[mode]['outcome'], ('before rows', mode, b[mode]['outcome'])
        assert a[mode]['state'] == ROWS[mode]['state'], ('after state', mode, a[mode]['state'])
        assert a[mode]['outcome'] == ROWS[mode]['outcome'], ('after rows', mode, a[mode]['outcome'])
    assert b['control']['log_sha256'] == a['control']['log_sha256'], 'control changed'
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
