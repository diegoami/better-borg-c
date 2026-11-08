#!/usr/bin/env python3
"""Verify the source85 best-equipment skip count (source fix 5d73e0c21) on product cores.

borg_one_step_wearing_best() carries out, one step at a time, the
equipment changes planned at home by borg_best_stuff().  When the next
change cannot be made because the pack or the home is full, it calls
itself with skip + 1 to try the following change instead.  The skip
counter was declared inside the search loop, so it was reset to skip on
every pass and never reached zero: with skip > 0 every remaining planned
change was skipped, not just the first skip of them.  The step then did
nothing, and when the list ended on empty entries the plan was
discarded.  A change that could still be made (for example wearing a
cloak into an empty slot, which also frees the pack slot the blocked
change needs) was never tried.  The correction declares the counter
once, before the loop.

The tight mode fails before (2 actions, no scale mail and no cloak worn;
the plan is dropped) and passes after (5 actions, both worn); the roomy
and nocloak controls pass in both phases with byte-identical logs.

Fixture: kit 620235082 at head 3735a7e7. Normal phases only. Run under
the shared native lock after this tree's gate build, with the before
snapshot built at the before commit (its gate result recorded under
--before-gate).
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
BEFORE = '3e50961cd9e0327f5b52855ae43d905b23ae2789'
FIX = '5d73e0c2120b450428f2417db325041c1b6d3da9'
EVIDENCE = '3735a7e72849aa4fa95ddade1458fb27a95be866'
PIN = '620235082d9faf6644d496f52fbc177a970fe266'
PREFIX = 'docs/audit/c-reports/wearskip-85/'
SOURCE = 'src/borg/borg-item-wear.c'
MODES = ('tight', 'roomy', 'nocloak')
FLIP = ['tight']
SUITE = 'native-c/wearskip-85'


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
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                   '-I' + str(ROOT / 'src/tests'), str(out / 'scenario.c'),
                   *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, **{'WS85_MODE': mode,
                                        'WS85_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
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
    # tight: the plan is dropped before (2 actions, nothing worn) and
    # carried out after (5 actions, scale mail and cloak worn).
    assert not b['tight']['passed'] and b['tight']['outcome'] == {
        'actions': 2, 'wears_scale_mail': 0, 'wears_cloak': 0}
    assert a['tight']['passed'] and a['tight']['outcome'] == {
        'actions': 5, 'wears_scale_mail': 1, 'wears_cloak': 1}
    for mode in ('roomy', 'nocloak'):
        assert b[mode]['passed'] and a[mode]['passed'], mode
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], ('control changed', mode)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
