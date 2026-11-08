#!/usr/bin/env python3
"""Verify the source287 buffer-size correction (source PR335, e7f670fa4) on product cores.

The carried termination fix (patch 0025, source interim shape 3e7fe8a83)
bounded the UTF-8 conversion by ABS(n) * MB_CUR_MAX: a limit derived from the
character count, not from the destination. On a wide terminal showing
multibyte text the conversion writes past the caller's 1024-byte buffer
(revised source evidence kit f9706564e, 301-column wide case:
guard_overwritten=177; AddressSanitizer stack-buffer-overflow, WRITE of size
1201 in wcstombs from borg_what_text). The correction passes the destination
size, converts at most size - 1 bytes and always terminates the result
(empty on a conversion error).

Before phases use the retained before build and its ASan twin (the patch 0025
state; borg-io.c is byte-identical to the source interim shape): multibyte
and control still hold the 0025 contract; the wide case leaves 177 guard
bytes overwritten and, under AddressSanitizer, aborts with the 1201-byte
stack-buffer-overflow WRITE. After phases use this tree's gate build and its
ASan twin: every mode passes, the guard is untouched, no sanitizer report.
The control log is byte-identical across the correction, and the multibyte
log is unchanged too (the sized bound terminates the same 81 bytes).

Fixture: revised kit f9706564e (supersedes 8d844e379). The scenario's
t287-variant.h selects the API shape per phase (before cores unsized, after
cores sized); before-phase headers are exported from the before ref so the
unsized declaration matches the before core.

Run under the shared native lock after this tree's normal gate build and a
fully ASan-instrumented core build, with the before snapshots built at the
before commit (its gate result recorded under --before-gate).
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
BEFORE = '5cd2258dd78d9fed83c11f5df6a3afe88889337a'
INTERIM = '3e7fe8a8399352c4fe67f5de2d8d48b5e0bd04c1'
FIX = 'e7f670fa4d4f0672dc346637fc7be20c814a4b62'
EVIDENCE = 'f9706564e0a667670fb024e9e1f87da137f21c9c'
PREFIX = 'docs/audit/c-reports/text-287/'
SOURCES = ('src/borg/borg-io.c', 'src/borg/borg-io.h',
           'src/borg/borg-messages.c', 'src/borg/borg-think.c')
SIZED = {'normal-before': 0, 'normal-after': 1, 'asan-before': 0, 'asan-after': 1}
MODES = ('multibyte', 'control', 'wide')
ASAN_OPTIONS = 'detect_leaks=0:intercept_strcmp=0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-asan-build', required=True, type=Path)
    p.add_argument('--before-gate', required=True, type=Path,
                   help='result.json of the gate run at the before commit')
    p.add_argument('--product-build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--asan-build', default=ROOT / 'build/asan', type=Path)
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
    before, before_asan = args.before_build.resolve(), args.before_asan_build.resolve()
    build, asan = args.product_build.resolve(), args.asan_build.resolve()

    # Provenance: the source correction, file by file, applied to the before
    # module equals the product module; the before borg-io.c is exactly the
    # carried interim shape; the fix commit is the only src/lib change.
    for source in SOURCES:
        source_diff = subprocess.check_output(
            ['git', 'diff', FIX + '^', FIX, '--', source], cwd=ROOT)
        with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
            d = Path(tmp)
            (d / source).parent.mkdir(parents=True)
            (d / source).write_bytes(read(BEFORE, source))
            subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
            layered = (d / source).read_bytes()
        assert (ROOT / source).read_bytes() == layered, 'product module != before + source diff: ' + source
    changed = subprocess.check_output(
        ['git', 'diff', '--name-only', BEFORE, 'HEAD', '--', 'src', 'lib',
         'CMakeLists.txt', 'cmake'], cwd=ROOT, text=True).split()
    assert changed == sorted(SOURCES), changed
    subprocess.run(['git', 'diff', '--exit-code', INTERIM, BEFORE, '--',
                    'src/borg/borg-io.c'], cwd=ROOT, check=True)
    subprocess.run(['git', 'merge-base', '--is-ancestor', args.fix, 'HEAD'], cwd=ROOT, check=True)

    before_gate = json.loads(args.before_gate.resolve().read_text())
    assert before_gate['success'] and before_gate['commit'] == BEFORE
    subprocess.run(['git', 'diff', '--exit-code', before_gate['commit'], BEFORE,
                    '--', 'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
    product_gate = json.loads(args.product_gate.resolve().read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert product_gate['success']
    # The gate must be an ancestor of HEAD with identical game sources; only
    # docs/tooling commits may sit between the gate and this run.
    subprocess.run(['git', 'merge-base', '--is-ancestor', product_gate['commit'], 'HEAD'],
                   cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--exit-code', product_gate['commit'], 'HEAD', '--',
                    'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)

    for core in (asan, before_asan):
        flags = (core / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
        assert '-fsanitize=address' in flags

    # Before-phase headers come from the before ref: the unsized declaration
    # must match the before core while the worktree already carries the fix.
    subprocess.run(['git', 'archive', BEFORE, 'src'], cwd=ROOT, check=True,
                   stdout=(out / 'before-src.tar').open('wb'))
    (out / 'before-src').mkdir()
    subprocess.run(['tar', '-xf', str(out / 'before-src.tar')], cwd=out / 'before-src', check=True)

    report = {
        'fixture_commit': EVIDENCE,
        'fixture_sha256': sha(out / 'scenario.c'),
        'source_fix': FIX,
        'source_interim': INTERIM,
        'fix': args.fix,
        'provenance': 'source diff applied to the before module == product module',
        'before_commit': BEFORE,
        'before_native_gate': before_gate,
        'before_binary_sha256': sha(before / 'game/angband'),
        'product_commit': head,
        'product_native_gate': product_gate,
        'product_binary_sha256': sha(build / 'game/angband'),
        'asan_options': ASAN_OPTIONS,
        'phases': {}, 'verified': False,
    }
    headers = {'normal-before': out / 'before-src', 'asan-before': out / 'before-src',
               'normal-after': ROOT, 'asan-after': ROOT}
    for phase in ('normal-before', 'normal-after', 'asan-before', 'asan-after'):
        core = before if phase.endswith('before') else build
        if phase.startswith('asan'):
            core = before_asan if phase == 'asan-before' else asan
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        (out / 't287-variant.h').write_text(f'#define T287_SIZED {SIZED[phase]}\n')
        binary = out / (phase + '-scenario')
        command = ['cc', '-g', '-DALLOW_BORG',
                   '-I' + str(headers[phase] / 'src'),
                   '-I' + str(headers[phase] / 'src/tests')]
        if phase.startswith('asan'):
            command += ['-fsanitize=address', '-fno-omit-frame-pointer']
        command += [str(out / 'scenario.c'), *map(str, objects + helpers),
                    '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            env = dict(os.environ, T287_MODE=mode, T287_PROFILE=str(out / 'profile'),
                       LC_ALL='C.UTF-8')
            if phase.startswith('asan'):
                env['ASAN_OPTIONS'] = ASAN_OPTIONS
            result = subprocess.run([str(binary), '-v'], cwd=build / 'game', env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=180)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            row = {
                'exit': result.returncode,
                'passed': 'native-c/text-287 finished: 1/1 passed' in text,
                # Actual sanitizer reports say "AddressSanitizer: <kind>";
                # the wide case's LAYOUT line only mentions the name in prose.
                'asan': re.search(r'AddressSanitizer: [a-z]', text) is not None,
                'log_sha256': sha(log),
            }
            match = re.search(r'OUTCOME (.*)', text)
            if match:
                row['outcome'] = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', match[1])}
            if 'stack-buffer-overflow' in text:
                row['report'] = {
                    'stack-buffer-overflow': True,
                    'write_of_1201': 'WRITE of size 1201' in text,
                    'wcstombs_frame': 'wcstombs' in text,
                    'borg_what_text_frame': 'borg_what_text' in text,
                }
            rows[mode] = row
            print(phase, mode, row, flush=True)
        report['phases'][phase] = {
            'cases': rows, 'command': command, 'binary_sha256': sha(binary),
            'objects_sha256': {str(o): sha(o) for o in objects + helpers},
        }
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    nb, na = report['phases']['normal-before']['cases'], report['phases']['normal-after']['cases']
    ab, aa = report['phases']['asan-before']['cases'], report['phases']['asan-after']['cases']
    # Before (patch 0025 state): the 0025 contract still holds, the wide case
    # overflows the guard and fails.
    for mode in ('multibyte', 'control'):
        row = nb[mode]
        assert row['exit'] == 0 and row['passed'] and not row['asan'], ('normal-before', mode)
    assert nb['multibyte']['outcome'] == {'terminated': 1, 'strnlen': 81}
    assert nb['control']['outcome'] == {'terminated': 1, 'strnlen': 80}
    assert nb['wide']['exit'] == 0 and not nb['wide']['passed'] and not nb['wide']['asan']
    assert nb['wide']['outcome'] == {'terminated': 0, 'strnlen': 1024, 'guard_overwritten': 177}
    # After: every mode passes, the sized bound terminates inside the buffer.
    for mode in MODES:
        row = na[mode]
        assert row['exit'] == 0 and row['passed'] and not row['asan'], ('normal-after', mode)
    assert na['multibyte']['outcome'] == {'terminated': 1, 'strnlen': 81}
    assert na['control']['outcome'] == {'terminated': 1, 'strnlen': 80}
    assert na['wide']['outcome'] == {'terminated': 1, 'strnlen': 1020, 'guard_overwritten': 0}
    assert nb['control']['log_sha256'] == na['control']['log_sha256'], 'ASCII control changed'
    assert nb['multibyte']['log_sha256'] == na['multibyte']['log_sha256'], 'multibyte log changed'
    # ASan phases mirror the normal ones; only the before wide case reports.
    for mode in ('multibyte', 'control'):
        assert ab[mode]['exit'] == 0 and ab[mode]['passed'] and not ab[mode]['asan'], ('asan-before', mode)
    assert ab['wide']['exit'] != 0 and not ab['wide']['passed']
    assert ab['wide'].get('report') == {'stack-buffer-overflow': True, 'write_of_1201': True,
                                        'wcstombs_frame': True, 'borg_what_text_frame': True}
    for mode in MODES:
        row = aa[mode]
        assert row['exit'] == 0 and row['passed'] and not row['asan'], ('asan-after', mode)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
