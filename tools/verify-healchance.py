#!/usr/bin/env python3
"""Verify the source364 healing-chance signs (source fix b366550f) on product cores.

borg_heal() draws a chance roll and skips healing below the threshold;
three adjustments had the sign opposite to their comments: fighting a
unique subtracted 10 (healed less next to a unique), the
danger-at-current-hp case subtracted 75 (a borg in real danger skipped
healing whenever it had lost less than 75% of its hp), and the risky
adjustment added 5.  The correction flips the three signs; the class
adjustment and thresholds are unchanged.
The danger, unique and risky modes flip as recorded; the control passes
in both phases with a byte-identical log.
Fixture: kit 97bcf2a980749472b5ce1dba44ac7cb054ca274d at head bbc5de859c7b27d02d88c1bb84ec46d796de8716. Normal phases only. Before phases
(the pre-fix build) fail the flip mode; after phases pass every mode;
control logs are byte-identical across the correction.

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
BEFORE = 'e4cbcf27bc54c28d69d3cfa327e37b635f6a8b5b'
FIX = 'b366550f776d4d7a6ac52031529f3254a5914d38'
EVIDENCE = 'f88fee1e3ace2b5f34f6fc8a1b4fbc30d3f94da1'
PIN = '3adc1b8128edfe31ca9a395d64f860b995396ec6'
PREFIX = 'docs/audit/c-reports/healchance-364/'
SOURCE = 'src/borg/borg-caution.c'
MODES = ('danger', 'unique', 'risky', 'control')
SUITE = 'native-c/healchance-364'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-gate', required=True, type=Path,
                   help='result.json of the gate run at the before commit')
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--product-gate', default=ROOT / 'artifacts/native/result.json', type=Path)
    p.add_argument('--fix', required=True, help='applied product commit')
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()

    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)

    (out / 'scenario.c').write_bytes(read(EVIDENCE, PREFIX + 'scenario.c'))
    (out / 'profile/borg.txt').write_bytes(read(EVIDENCE, PREFIX + 'borg.txt'))
    same = subprocess.run(
        ['git', 'diff', '--exit-code', PIN, EVIDENCE, '--',
         PREFIX + 'scenario.c', PREFIX + 'borg.txt', PREFIX + 'profile'],
        cwd=ROOT, capture_output=True)
    assert same.returncode == 0, 'runtime fixtures changed since the run pin'
    before, build = args.before_build.resolve(), args.product_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / SOURCE).parent.mkdir(parents=True)
        (d / SOURCE).write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / SOURCE).read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered, 'product module != before + source diff'
    # Single-step PR: the fix commit itself touches only SOURCE, and the
    # tree-level scope from BEFORE to HEAD is SOURCE alone.
    fix_scope = subprocess.check_output(
        ['git', 'diff', '--name-only', FIX + '^', FIX, '--', 'src', 'lib',
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
        'fixture_commit': EVIDENCE, 'fixture_pin': PIN,
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
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        binary = out / (phase + '-scenario')
        # The kit's scenario.c calls tval_is_potion() without including
        # obj-tval.h (implicit declarations are errors on this compiler);
        # force the include rather than edit the pinned fixture.
        command = ['cc', '-g', '-DALLOW_BORG', '-include', 'obj-tval.h',
                   '-I' + str(ROOT / 'src'),
                   '-I' + str(ROOT / 'src/tests'), str(out / 'scenario.c'),
                   *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, **{'HC364_MODE': mode,
                                        'HC364_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            omatch = re.search(r'OUTCOME (.*)', text)
            rows[mode] = {
                'exit': result.returncode,
                'passed': SUITE + ' finished: 1/1 passed' in text,
                'outcome': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch[1])} if omatch else {},
                'log_sha256': sha(log),
            }
            print(phase, mode, rows[mode], flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command,
                                   'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    b, a = report['phases']['before']['cases'], report['phases']['after']['cases']
    for mode in MODES:
        assert b[mode]['exit'] == 0 and a[mode]['exit'] == 0, mode
    assert not b['danger']['passed'] and b['danger']['outcome']['heals'] == 0
    assert a['danger']['passed'] and a['danger']['outcome']['heals'] == 100
    assert a['danger']['outcome']['witness_healed'] == 1 and a['danger']['outcome']['drank_healing'] == 1
    assert not b['unique']['passed'] and b['unique']['outcome']['heals'] == 18
    assert a['unique']['passed'] and a['unique']['outcome']['heals'] == 32
    assert not b['risky']['passed'] and b['risky']['outcome']['heals'] == 27
    assert a['risky']['passed'] and a['risky']['outcome']['heals'] == 20
    assert b['control']['passed'] and a['control']['passed']
    assert b['control']['outcome'] == a['control']['outcome']
    assert b['control']['log_sha256'] == a['control']['log_sha256'], ('control changed', 'control')
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
