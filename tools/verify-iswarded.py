#!/usr/bin/env python3
"""Verify the source198 rune-check bounds correction (source PR452, 62242ac2) on product cores.

When a monster hits the Borg while it tracks runes, or a Rune of Protection
breaks, the message handler clears the tracked runes and then cheats a look
at the rune under borg.c. Messages are parsed at the Borg's next keypress,
before borg_update() moves borg.c onto the current level: a -more- line
stored just before a level change (Word of Recall firing in the same game
turn as the monster's action) is parsed on the new level with the previous
level's position. On a smaller new level (the 66x22 town) that position lies
outside the level: square_iswarded() fails the square_istrap bounds
assertion in the normal build, and with assertions off reads outside the
level's row array (AddressSanitizer: heap-buffer-overflow, READ of size 8 in
square_istrap from borg_parse_aux). The correction skips the rune check when
the position is not on the current level; the tracked runes are still
cleared.

Before phases (merged main 47be91c95): the two town cases abort on the
bounds assertion in the normal build and report the heap-buffer-overflow
READ under AddressSanitizer; the three inside controls pass unchanged.
After phases: every mode completes the first town keypress (survived=1) with
no assertion and no sanitizer report. Control logs are byte-identical across
the correction in both builds.

Fixture: kit 563a2616 at head 5454144a. The ASan phases build with
-DNDEBUG (assertions off) exactly like the source kit, so the town cases
report the heap-buffer-overflow READ instead of aborting on the bounds
assertion; the normal phases keep assertions and abort with SIGABRT.
Run under the shared native lock after this tree's gate build, with
the before snapshots built at the before commit (its gate result recorded
under --before-gate; the ASan before twin in the retained before worktree).
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
BEFORE = '47be91c95b471aae5dc1de8bca9bb2942ae769d7'
FIX = '62242ac26bab4f128793d767f0f502bf4ca4d820'
EVIDENCE = '5454144a624ef51ec68cbd37e8291b45d10d865d'
PIN = '563a26167a52131d3b8ab387af4fbfd4b5b7226b'
PREFIX = 'docs/audit/c-reports/iswarded-198/'
SOURCE = 'src/borg/borg-messages.c'
MODES = ('rune-town', 'hit-town', 'rune-inside', 'hit-inside', 'hit-noglyph')
FLIP = ('rune-town', 'hit-town')
SITE = 'square_istrap <- borg_parse_aux'
ASAN_OPTIONS = 'detect_leaks=0:intercept_strcmp=0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-build', required=True, type=Path)
    p.add_argument('--before-asan-build', required=True, type=Path)
    p.add_argument('--before-gate', required=True, type=Path)
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
    same = subprocess.run(
        ['git', 'diff', '--exit-code', PIN, EVIDENCE, '--',
         PREFIX + 'scenario.c', PREFIX + 'borg.txt', PREFIX + 'profile'],
        cwd=ROOT, capture_output=True)
    assert same.returncode == 0, 'runtime fixtures changed since the run pin'
    before, before_asan = args.before_build.resolve(), args.before_asan_build.resolve()
    build, asan = args.product_build.resolve(), args.asan_build.resolve()

    source_diff = subprocess.check_output(
        ['git', 'diff', FIX + '^', FIX, '--', SOURCE], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
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
    for core in (asan, before_asan):
        flags = (core / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text()
        assert '-fsanitize=address' in flags

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
        'asan_options': ASAN_OPTIONS,
        'phases': {}, 'verified': False,
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
            # The ASan cores are NDEBUG (assertions off, like the source
            # kit); the scenario must match or flag_on_dbg is unresolved.
            command += ['-fsanitize=address', '-fno-omit-frame-pointer', '-DNDEBUG']
        command += [str(out / 'scenario.c'), *map(str, objects + helpers),
                    '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            env = dict(os.environ, ISW198_MODE=mode, ISW198_PROFILE=str(out / 'profile'),
                       LC_ALL='C.UTF-8')
            if phase.startswith('asan'):
                env['ASAN_OPTIONS'] = ASAN_OPTIONS
            result = subprocess.run([str(binary), '-v'], cwd=build / 'game', env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=300)
            text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
            log = out / f'{phase}-{mode}.log'
            log.write_text(text)
            omatch = re.search(r'OUTCOME (.*)', text)
            leaf = re.search(r'#0 0x[0-9a-f]+ in (\w+) ', text)
            aux = re.search(r'in borg_parse_aux \S*?(borg-messages\.c:\d+)', text)
            site = leaf and aux
            rows[mode] = {
                'exit': result.returncode,
                'passed': 'native-c/iswarded-198 finished: 1/1 passed' in text,
                'assert_abort': "Assertion `square_in_bounds(c, grid)' failed" in text,
                'asan': re.search(r'AddressSanitizer: [a-z]', text) is not None,
                'asan_read': re.search(r'ERROR: AddressSanitizer: heap-buffer-overflow'
                                       r'.*\nREAD of size', text) is not None,
                'asan_site': (leaf.group(1) + ' <- borg_parse_aux ' + aux.group(1)) if site else None,
                'outcome': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch[1])} if omatch else {},
                'log_sha256': sha(log),
            }
            print(phase, mode, rows[mode], flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command,
                                   'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    nb, na = report['phases']['normal-before']['cases'], report['phases']['normal-after']['cases']
    ab, aa = report['phases']['asan-before']['cases'], report['phases']['asan-after']['cases']
    # Before: the town cases abort with SIGABRT from the bounds assertion
    # (exit -6); every other row exits cleanly.
    for mode in MODES:
        if mode in FLIP:
            assert nb[mode]['exit'] != 0, mode
        else:
            assert nb[mode]['exit'] == 0, mode
        assert na[mode]['exit'] == 0, mode
    # Before: the two town cases abort on the bounds assertion; the controls
    # complete and stay free of assertions.
    for mode in FLIP:
        assert nb[mode]['exit'] != 0 and not nb[mode]['passed'] and nb[mode]['assert_abort'], mode
    for mode in MODES:
        if mode not in FLIP:
            assert nb[mode]['passed'] and not nb[mode]['assert_abort'] and not nb[mode]['asan'], mode
            assert nb[mode]['outcome'] == {'survived': 1}
    # After: every mode survives the first town keypress; no assertion anywhere.
    for mode in MODES:
        assert na[mode]['passed'] and not na[mode]['assert_abort'] and not na[mode]['asan'], mode
        assert na[mode]['outcome'] == {'survived': 1}
    for mode in MODES:
        if mode not in FLIP:
            assert nb[mode]['log_sha256'] == na[mode]['log_sha256'], ('control changed', mode)
    # ASan phases: the town cases report the heap-buffer-overflow READ from
    # square_istrap under borg_parse_aux (source file lines shift on the
    # product, so the function path is asserted, the site recorded);
    # controls stay clean; after phases are report-free.
    for mode in FLIP:
        assert ab[mode]['exit'] != 0 and not ab[mode]['passed'], mode
        assert ab[mode]['asan_read'] and not ab[mode]['assert_abort'], mode
        assert ab[mode]['asan_site'] and ab[mode]['asan_site'].startswith(SITE), ab[mode]['asan_site']
    for mode in MODES:
        if mode not in FLIP:
            assert ab[mode]['passed'] and not ab[mode]['asan'], mode
            assert ab[mode]['log_sha256'] == aa[mode]['log_sha256'], ('asan control changed', mode)
        assert aa[mode]['passed'] and not aa[mode]['asan'] and not aa[mode]['assert_abort'], mode
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
