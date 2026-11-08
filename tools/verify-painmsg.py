#!/usr/bin/env python3
"""Verify the source197 pain-message allocation (source PR458, 8a0c13f7) on product cores.

borg_get_parsed_pain() allocated strlen + 1 bytes for a ' ' + text + NUL
entry, so several monster status endings parsed short and queued no Borg
reaction: 'The kobold can move again.', 'falls under your spell!', 'is no
longer under your control.' and 'shimmers for a moment.' were ignored by
the original and are recognised and matched to the monster by the
corrected Borg. The stun and hurt controls are byte-identical; the puff
line stays unrecognised in both (no monster name; outside this fix).
The correction allocates strlen + 2.
Fixture: kit 'ba2167d51fcdd99a957b9ed53f65c676ed4b4bff' at head 'ffb74e54ad2ccf6a88e38c174322d04814bb3748'. Normal phases only. Before phases
(the pre-fix build) fail the flip modes; after phases pass every mode;
control logs are byte-identical across the correction.

Run under the shared native lock after this tree's gate build, with the
before snapshot built at the before commit (its gate result recorded under
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
BEFORE = '53c17b06c863a7bb3e81675398f33eb2a346e933'
FIX = '8a0c13f7127642da8222c84380b4e6b8f9f96eff'
EVIDENCE = 'ffb74e54ad2ccf6a88e38c174322d04814bb3748'
PIN = 'ba2167d51fcdd99a957b9ed53f65c676ed4b4bff'
PREFIX = 'docs/audit/c-reports/painmsg-197/'
SOURCE = 'src/borg/borg-messages.c'
MODES = ('held', 'command', 'uncommand', 'shapefail', 'stun', 'hurt', 'puff')
FLIP = ['held', 'command', 'uncommand', 'shapefail']
ENV_PREFIX = 'PM197'
SUITE = 'native-c/painmsg-197'


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
                env=dict(os.environ, **{'PM197_MODE': mode,
                                         'PM197_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
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
        assert not b['held']['passed'] and b['held']['outcome'] == {'recognised': 0, 'matched_to_kobold': 0}
    assert a['held']['passed'] and a['held']['outcome'] == {'recognised': 1, 'matched_to_kobold': 1}
    assert not b['command']['passed'] and b['command']['outcome'] == {'recognised': 0, 'matched_to_kobold': 0}
    assert a['command']['passed'] and a['command']['outcome'] == {'recognised': 1, 'matched_to_kobold': 1}
    assert not b['uncommand']['passed'] and b['uncommand']['outcome'] == {'recognised': 0, 'matched_to_kobold': 0}
    assert a['uncommand']['passed'] and a['uncommand']['outcome'] == {'recognised': 1, 'matched_to_kobold': 1}
    assert not b['shapefail']['passed'] and b['shapefail']['outcome'] == {'recognised': 0, 'matched_to_kobold': 0}
    assert a['shapefail']['passed'] and a['shapefail']['outcome'] == {'recognised': 1, 'matched_to_kobold': 1}
    assert b['stun']['passed'] and a['stun']['passed']
    assert b['stun']['log_sha256'] == a['stun']['log_sha256'], ('control changed', 'stun')
    assert b['hurt']['passed'] and a['hurt']['passed']
    assert b['hurt']['log_sha256'] == a['hurt']['log_sha256'], ('control changed', 'hurt')
    # puff stays unrecognised in both (no monster name; outside this fix).
    assert not b['puff']['passed'] and not a['puff']['passed']
    assert b['puff']['outcome'] == a['puff']['outcome'] == {'recognised': 0, 'matched_to_kobold': 0}
    assert b['puff']['log_sha256'] == a['puff']['log_sha256']
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
