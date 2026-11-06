#!/usr/bin/env python3
"""Verify source118 with an adapted native fixture and actual product cores.

The evidence fixture's adjacent mage only passed phaseB while the pristine
borg_projectable_pure() zeroed its bolts at the caster's own tracked grid;
the carried caster-shot-origin fix (0008) counts those bolts, so a rune can
no longer improve that danger and the unchanged fixture stalls at phaseB.
The tracked adapted scenario replaces the threat with a glyph-viable
speed-110 S_KIN summoner at distance 2 (see its header); phases, controls,
assertions and thresholds are the evidence fixture's. The original failed
attempt and fixture stay in artifacts/glyph/scenarios and
docs/measurement/GLYPH-TRACKER.md.

Run under the shared native lock after normal and fully ASan-instrumented core
builds. Before-ASan replaces only the message object with the original source,
compiled using the ASan build's recorded flags. No normal object/source changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BEFORE = '19870e97d89afa4b302bdd9d27337ed617c97554'
FIX = 'ec172531ec38fdd3ac2783d21e3faf6dc1e2b3f3'
EVIDENCE = 'f1f53106526412cfe44fa01c73d00e7dbf4dbeed'
PREFIX = 'docs/audit/c-reports/CBUG-0102/'
ADAPTED = ROOT / 'tools/glyph-tracker-scenario.c'
SOURCE = 'src/borg/borg-messages.c'
MODES = ('stairs', 'clear-floor', 'pairing')
ASAN_OPTIONS = 'detect_leaks=0:intercept_strcmp=0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--asan-build', default=ROOT / 'build/asan', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()
    def read(ref, name):
        return subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)
    (out / 'scenario.c').write_bytes(ADAPTED.read_bytes())
    (out / 'profile/borg.txt').write_bytes(read(EVIDENCE, PREFIX + 'borg.txt'))
    before, build, asan = args.before_build.resolve(), args.product_build.resolve(), args.asan_build.resolve()
    assert (ROOT / SOURCE).read_bytes() == read(FIX, SOURCE)
    assert (before.parents[1] / SOURCE).read_bytes() == read(BEFORE, SOURCE)
    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    flags = (asan / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
    assert '-fsanitize=address' in flags
    tokens = []
    for variable in ('C_DEFINES', 'C_INCLUDES', 'C_FLAGS'):
        tokens += shlex.split(re.search(r'^' + variable + r' = (.*)$', flags, re.MULTILINE)[1])
    old_source, old_object = out / 'before-messages.c', out / 'before-messages-asan.o'
    old_source.write_bytes(read(BEFORE, SOURCE))
    compile_command = ['cc', *tokens, '-I' + str(ROOT / 'src/borg'), '-c', str(old_source), '-o', str(old_object)]
    with (out / 'before-asan-compile.log').open('w') as log:
        subprocess.run(compile_command, stdout=log, stderr=subprocess.STDOUT, check=True)
    report = {'scenario_source': 'tools/glyph-tracker-scenario.c',
              'scenario_sha256': sha(out / 'scenario.c'),
              'original_fixture_commit': EVIDENCE,
              'original_fixture_sha256': hashlib.sha256(read(EVIDENCE, PREFIX + 'scenario.c')).hexdigest(),
              'profile_commit': EVIDENCE, 'fix': FIX,
              'before_commit': BEFORE, 'before_native_gate': before_gate,
              'before_binary_sha256': sha(before / 'game/angband'),
              'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'product_binary_sha256': sha(build / 'game/angband'), 'asan_options': ASAN_OPTIONS,
              'before_asan_compile_command': compile_command, 'phases': {}, 'verified': False}
    for phase, core in (('normal-before', before), ('normal-after', build),
                        ('asan-before', asan), ('asan-after', asan)):
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        if phase == 'asan-before':
            replaced = [o for o in objects if o.as_posix().endswith(SOURCE + '.o')]
            assert len(replaced) == 1
            objects = [old_object if o == replaced[0] else o for o in objects]
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'src/tests')]
        if phase.startswith('asan'):
            command += ['-fsanitize=address', '-fno-omit-frame-pointer']
        command += [str(out / 'scenario.c'), *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run([str(binary), '-v'], cwd=build / 'game',
                                    env=dict(os.environ, CBUG0102_MODE=mode, CBUG0102_PROFILE=str(out / 'profile'),
                                             ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {'exit': result.returncode, 'passed': 'native-c/CBUG-0102 finished: 1/1 passed' in text,
                   'asan': 'AddressSanitizer' in text, 'log_sha256': sha(log),
                   'target_write_report': all(s in text for s in ('heap-buffer-overflow', 'WRITE of size 4', 'borg_defend_aux_glyph', 'borg_init_track'))}
            for tag, key in (('TRACK phaseA', 'phaseA'), ('TRACK phaseB_acted', 'phaseB'), ('OUTCOME', 'outcome')):
                match = re.search(re.escape(tag) + r' (.*)', text)
                if match:
                    row[key] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])}
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command, 'binary_sha256': sha(binary),
                                   'objects_sha256': {str(o): sha(o) for o in objects + helpers}}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    cases = {phase: data['cases'] for phase, data in report['phases'].items()}
    a, b = cases['normal-before']['stairs'], cases['normal-after']['stairs']
    assert a['exit'] == b['exit'] == 0 and not a['passed'] and b['passed']
    assert (a['phaseA']['num'], a['phaseB']['num'], a['outcome']['num_final']) == (-1, 0, 0)
    assert (b['phaseA']['num'], b['phaseB']['num'], b['outcome']['num_final']) == (0, 1, 1)
    assert a['outcome']['glyph_created'] == b['outcome']['glyph_created'] == 1
    def decisions(phase):
        return re.findall(r'DECISION .*', (out / f'{phase}-stairs.log').read_text())
    assert decisions('normal-before') == decisions('normal-after')
    for mode in ('clear-floor', 'pairing'):
        a, b = cases['normal-before'][mode], cases['normal-after'][mode]
        assert a['exit'] == b['exit'] == 0 and a['passed'] and b['passed']
        assert a['log_sha256'] == b['log_sha256'], mode
    a = cases['asan-before']['stairs']
    assert a['exit'] != 0 and not a['passed'] and a['target_write_report']
    for mode in ('clear-floor', 'pairing'):
        a = cases['asan-before'][mode]
        assert a['exit'] == 0 and a['passed'] and not a['asan'], mode
    for mode, row in cases['asan-after'].items():
        assert row['exit'] == 0 and row['passed'] and not row['asan'], mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
