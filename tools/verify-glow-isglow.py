#!/usr/bin/env python3
"""Verify the source213 square_isglow correction (source PR411, c316a65b2) on product cores.

The carried glowtrace fix (patch 0050, source shape da9934216) read the
floor's glow state through square_islit(), which is the grid's current light
level and includes the Borg's own light source: every floor inside the torch
radius was marked BORG_GLOW and the flow toward light chose targets the Borg
was already lighting itself. The owner-decided correction marks a floor
glowing only when the game flags SQUARE_GLOW (square_isglow()), marks
torch-lit floors BORG_LIGHT instead, and keeps the dark test
(!isglow && !islit). Before phases (the 0050 state) hold the restored-branch
contract for genuinely glowing floors and fail the torch-lit case; after
phases pass every mode. The glowing-arena (main), door and unlit logs are
byte-identical across the correction; the torch-lit case flips
torchlit_marked_glow 1 to 0 with glow_n 9 to 0.

Fixture: revised kit 8934edd4e at head f2b402c92 (supersedes the 0050-era
fixtures 50d4911e/5edc188e). Normal phases only, like the most recent
carries; the correction touches no memory-safety behavior.

Run under the shared native lock after this tree's gate build (before phases
use the snapshotted pre-fix build and its recorded gate result).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BEFORE = '72dd1c8a366a924b3f2f90c3a966c8aa6d6d75fa'
FIX = 'c316a65b248c4372ff3b686eafaa0477c3117eeb'
EVIDENCE = 'f2b402c92ce57cc85d9fda777de901c2f157c720'
PIN = '8934edd4e26dfa0b73aec5d9f4ab89ecdc5aee36'
PREFIX = 'docs/audit/c-reports/glowtrace-213/'
SOURCE = 'src/borg/borg-update.c'
MODES = ('main', 'door', 'torchlit', 'unlit')


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

    # Provenance: the source correction applied to the before module equals
    # the product module; the fix commit is the only src/lib change.
    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with __import__('tempfile').TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / 'src/borg').mkdir(parents=True)
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
                env=dict(os.environ, GLOW213_PROFILE=str(out / 'profile'),
                         GLOW213_MODE=mode, LC_ALL='C.UTF-8'),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            smatch = re.search(r'STATE (.*)', text)
            omatch = re.search(r'OUTCOME (.*)', text)
            rows[mode] = {
                'exit': result.returncode,
                'passed': 'finished: 1/1 passed' in text,
                'state': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', smatch[1])} if smatch else {},
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
    # main (glowing arena): the 0050 contract holds before and after, logs
    # byte-identical; the flow-toward-light list is the kit's 484.
    assert b['main']['passed'] and a['main']['passed']
    assert b['main']['log_sha256'] == a['main']['log_sha256'], 'main log changed'
    for row in (b['main'], a['main']):
        assert row['state']['distant_glow'] == 1 and row['state']['near_glow'] == 1
        assert row['state']['wall_glow'] == 0 and row['outcome'] == {'glow_n': 484}
        assert row['state']['marked'] == 1 and row['state']['lit'] == 1 and row['state']['pcmem'] == 1
    # door control: identical before/after.
    assert b['door']['passed'] and a['door']['passed']
    assert b['door']['log_sha256'] == a['door']['log_sha256'], 'door log changed'
    assert a['door']['outcome'] == {'door_is_open': 1, 'wall_glow': 0}
    # unlit: the far floor is BORG_DARK in both, logs byte-identical.
    assert b['unlit']['passed'] and a['unlit']['passed']
    assert b['unlit']['log_sha256'] == a['unlit']['log_sha256'], 'unlit log changed'
    assert a['unlit']['outcome'] == {'far_dark': 1}
    # torchlit: the fail-before/pass-after case. Before, the torch-lit floor
    # is wrongly BORG_GLOW and the flow finds targets; after, it is
    # BORG_LIGHT and the flow list is empty (the kit's own contract).
    assert not b['torchlit']['passed'] and b['torchlit']['outcome']['torchlit_marked_glow'] == 1
    assert b['torchlit']['state']['near_glow'] == 1 and b['torchlit']['state']['near_light_flag'] == 0
    assert b['torchlit']['outcome']['glow_n'] > 0
    assert a['torchlit']['passed']
    assert a['torchlit']['outcome'] == {'torchlit_marked_glow': 0, 'glow_n': 0}
    assert a['torchlit']['state']['near_glow'] == 0 and a['torchlit']['state']['near_light_flag'] == 1
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
