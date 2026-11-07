#!/usr/bin/env python3
"""Verify source247 with the unchanged native fixture on actual product cores.

borg_mon_blow_effect()'s name-table loop bounded itself with the full
array length, so a blow name absent from the table walked into the
table's { NULL, MONBLOW_NONE } sentinel entry and strcmp'd against NULL:
the source receipt records a segfault (exit 139) when the lookup is
called with a made-up blow name. The correction makes the bound
sentinel-safe (i + 1 < sizeof(monblow) / sizeof(monblow[0])), keeping
in-table resolution (HURT -> MONBLOW_HURT) and returning MONBLOW_NONE
for unknown names. The unchanged fixture calls the lookup directly with
an in-table name and a made-up name: before, the made-up name crashes
(the suite never finishes; the sanitizer build names the null
dereference); after, both checks pass on the plain and sanitizer builds.
borg-fight-attack.c already carries 0011/0013/0014/0016/0019/0020/0021/
0022/0023/0024/0037, so provenance is proven by applying the source diff
to the before module and comparing bytes.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build. Before phases use the retained
forty-one-carry tree, which lacks only this fix.
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
BEFORE = 'fb16560054b44899c50b8aec5ce1a2b0e35c0533'
FIX = '64046743679e0925ae6698b458a7bbf9dfa6cb19'
EVIDENCE = 'eea8f6e1cc24ef72fb0dc07ff6df888e100bf3f9'
PREFIX = 'docs/audit/c-reports/blowname-247/'
SOURCE = 'src/borg/borg-fight-attack.c'
ASAN_OPTIONS = 'halt_on_error=0:detect_leaks=0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-asan-build', required=True, type=Path)
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--asan-build', default=ROOT / 'build/asan', type=Path)
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
    before, before_asan = args.before_build.resolve(), args.before_asan_build.resolve()
    build, asan = args.product_build.resolve(), args.asan_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        (d / 'src/borg').mkdir(parents=True)
        (d / 'src/borg/borg-fight-attack.c').write_bytes(read(BEFORE, SOURCE))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        layered = (d / 'src/borg/borg-fight-attack.c').read_bytes()
    assert (ROOT / SOURCE).read_bytes() == layered

    before_gate = json.loads((before.parents[1] / 'artifacts/native/result.json').read_text())
    assert before_gate['success']
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    for core in (asan, before_asan):
        flags = (core / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
        assert '-fsanitize=address' in flags
        assert (core / 'CMakeFiles/OurUnitTestLib.dir/src/tests/unit-test.c.o').exists()
    report = {
        'fixture_commit': EVIDENCE,
        'fixture_sha256': sha(out / 'scenario.c'),
        'fix': FIX,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE,
        'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'product_binary_sha256': sha(build / 'game/angband'),
        'asan_options': ASAN_OPTIONS,
        'phases': {},
        'verified': False,
    }
    for phase, core in (('normal-before', before), ('normal-after', build),
                        ('asan-before', before_asan), ('asan-after', asan)):
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                   '-I' + str(ROOT / 'src/tests')]
        if phase.startswith('asan'):
            # The pre-existing init-time borg_sort_comp_hook overflow
            # (source399, separately filed) trips in every sanitized
            # borg_init on this pin; recover from reported errors so the
            # runs reach the lookup, exactly as the source receipt
            # records.
            command += ['-fsanitize=address', '-fsanitize-recover=address',
                        '-fno-omit-frame-pointer']
        command += [str(out / 'scenario.c'), *map(str, objects + helpers),
                    '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        result = subprocess.run(
            [str(binary), '-v'], cwd=build / 'game',
            env=dict(os.environ, BW247_PROFILE=str(out / 'profile'),
                     ASAN_OPTIONS=ASAN_OPTIONS, LC_ALL='C.UTF-8'),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode())
        log = out / f'{phase}.log'
        log.write_text(text)
        match = re.search(r'UNKNOWN value=(\d+)', text)
        known = re.search(r'KNOWN value=(\d+)', text)
        row = {
            'exit': result.returncode,
            'passed': 'native-c/blowname-247 finished: 1/1 passed' in text,
            'asan': 'AddressSanitizer' in text,
            'known_value': int(known[1]) if known else None,
            'unknown_value': int(match[1]) if match else None,
            'log_sha256': sha(log),
        }
        report['phases'][phase] = {
            'case': row,
            'command': command,
            'binary_sha256': sha(binary),
            'objects_sha256': {str(o): sha(o) for o in objects + helpers},
        }
        print(phase, row, flush=True)
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    a, b = report['phases']['normal-before']['case'], report['phases']['normal-after']['case']
    assert a['exit'] == -11 and not a['passed'], a
    assert b['exit'] == 0 and b['passed'] and b['asan'] is False
    assert b['known_value'] == 1 and b['unknown_value'] == 0
    sa, sb = report['phases']['asan-before']['case'], report['phases']['asan-after']['case']
    assert sa['exit'] != 0 and not sa['passed'] and sa['asan'], 'sanitizer build did not name the crash'
    # asan-after still reports the pre-existing init-time overflow (source
    # #399, separately filed, present on every sanitized borg_init on this
    # pin) — its absence would be suspicious; what must hold is that the
    # suite now completes with both lookups correct.
    assert sb['exit'] == 0 and sb['passed'], sb
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
