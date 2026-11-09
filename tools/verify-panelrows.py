#!/usr/bin/env python3
"""Verify the source348 panel-scan bounds (source fix 82702575) on product cores.

borg_flow_light(), borg_flow_vault() and borg_excavate_vault() scan the
visible map panel, w_y .. w_y + SCREEN_HGT by w_x .. w_x + SCREEN_WID,
and index borg_grids[y][x] for each grid.  borg_grids has DUNGEON_HGT
(66) rows of DUNGEON_WID (198) grids, but the panel grows with the
terminal: with the default sidebar, a terminal of 69 or more rows or
213 or more columns shows more rows or columns than a full-size level
has.  The game then places the panel at the level's edge and the scans
read past the last row pointer of borg_grids (taller terminal) or past
the end of a row (wider terminal).  With a 70-row terminal the read of
the missing row crashes the game; a wider terminal silently reads
neighbouring memory.  The correction stops each scan at the edge of the
Borg's map; the grids that are on the map are scanned exactly as before.
Memory-safety defect: ASan phases per the verification contract
(0068/0070 precedent).  As the kit records: the light-tall, vault-tall
and dig-tall modes crash before (no outcome) and pass after; the seven
wide/normal/fit controls pass in both phases with identical rows.
Fixture: kit a9303c7c at head 24159739b.  The ASan phases build with
-DNDEBUG exactly like the source kit.
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
BEFORE = '9a428ea388b7356c68f67d0ba7f341480c6bfd0f'
FIX = '82702575b2179cb27cb7eac24272515dfea0830e'
EVIDENCE = '24159739b3b1642615afb362217213f290cf0127'
PIN = 'a9303c7ca621ef1a326000f127b7fec089a93b3c'
PREFIX = 'docs/audit/c-reports/panelrows-348/'
SOURCES = ('src/borg/borg-flow-misc.c',
           'src/borg/borg-think-dungeon-util.c')
MODES = ('light-tall', 'light-wide', 'light-normal', 'light-fit',
           'vault-tall', 'vault-wide', 'vault-normal', 'dig-tall', 'dig-wide',
           'dig-normal')
FLIP = ('light-tall', 'vault-tall', 'dig-tall')
# expected AddressSanitizer leaf function per flip mode
FLIP_SITE = {'light-tall': 'borg_flow_light', 'vault-tall': 'borg_flow_vault',
             'dig-tall': 'borg_excavate_vault', 'light-wide': 'borg_flow_light',
             'vault-wide': 'borg_flow_vault', 'dig-wide': 'borg_excavate_vault'}
# kit-recorded outcome rows (normal build); the tall modes crash before
ROWS = {
 'light-tall': {'completed': 1, 'targets': 88, 'offmap': 0, 'progress': 1},
 'light-wide': {'completed': 1, 'targets': 66, 'offmap': 0, 'progress': 1},
 'light-normal': {'completed': 1, 'targets': 66, 'offmap': 0, 'progress': 1},
 'light-fit': {'completed': 1, 'targets': 88, 'offmap': 0, 'progress': 1},
 'vault-tall': {'completed': 1, 'targets': 1, 'offmap': 0, 'progress': 1},
 'vault-wide': {'completed': 1, 'targets': 1, 'offmap': 0, 'progress': 1},
 'vault-normal': {'completed': 1, 'targets': 1, 'offmap': 0, 'progress': 1},
 'dig-tall': {'completed': 1, 'targets': 1, 'offmap': 0, 'progress': 1},
 'dig-wide': {'completed': 1, 'targets': 1, 'offmap': 0, 'progress': 1},
 'dig-normal': {'completed': 1, 'targets': 1, 'offmap': 0, 'progress': 1},
}
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
        ['git', 'diff', FIX + '^', FIX, '--'] + list(SOURCES), cwd=ROOT)
    with tempfile.TemporaryDirectory(dir='/tmp/opencode') as tmp:
        d = Path(tmp)
        for source in SOURCES:
            (d / source).parent.mkdir(parents=True, exist_ok=True)
            (d / source).write_bytes(read(BEFORE, source))
        subprocess.run(['patch', '-p1', '-s'], input=source_diff, cwd=d, check=True)
        for source in SOURCES:
            layered = (d / source).read_bytes()
            assert (ROOT / source).read_bytes() == layered, \
                'product module != before + source diff: ' + source
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
            env = dict(os.environ, PR348_MODE=mode, PR348_PROFILE=str(out / 'profile'),
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
            site = leaf.group(1) if leaf else None
            rows[mode] = {
                'exit': result.returncode,
                'passed': 'native-c/panelrows-348 finished: 1/1 passed' in text,
                'assert_abort': "Assertion `square_in_bounds(c, grid)' failed" in text,
                'asan': re.search(r'AddressSanitizer: [a-z]', text) is not None,
                # borg_grids is a global array: the OOB read of the row
                # pointer past the last row reports as a
                # global-buffer-overflow READ (not heap).
                'asan_read': re.search(r'ERROR: AddressSanitizer: global-buffer-overflow'
                                       r'.*\nREAD of size', text) is not None,
                'asan_site': site,
                'outcome': {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', omatch[1])} if omatch else {},
                'log_sha256': sha(log),
            }
            print(phase, mode, rows[mode], flush=True)
        report['phases'][phase] = {'cases': rows, 'command': command,
                                   'binary_sha256': sha(binary)}
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    nb, na = report['phases']['normal-before']['cases'], report['phases']['normal-after']['cases']
    ab, aa = report['phases']['asan-before']['cases'], report['phases']['asan-after']['cases']
    # controls: the modes whose panels fit the map (never OOB)
    CTRL = [m for m in MODES if m.endswith(('normal', 'fit'))]
    # Normal before: the tall modes crash (exit != 0, no outcome row);
    # the controls complete cleanly with the kit's recorded rows.
    for mode in FLIP:
        assert nb[mode]['exit'] != 0 and not nb[mode]['passed'], mode
        assert nb[mode]['outcome'] == {}, mode
    for mode in CTRL:
        assert nb[mode]['exit'] == 0 and nb[mode]['passed'], mode
        assert nb[mode]['outcome'] == ROWS[mode], (mode, nb[mode]['outcome'])
        assert not nb[mode]['assert_abort'] and not nb[mode]['asan'], mode
    # Normal after: every mode passes with the kit's recorded rows; the
    # controls are byte-identical to their before logs (the on-map grids
    # are scanned exactly as before).
    for mode in MODES:
        assert na[mode]['exit'] == 0 and na[mode]['passed'], mode
        assert na[mode]['outcome'] == ROWS[mode], (mode, na[mode]['outcome'])
        assert not na[mode]['assert_abort'] and not na[mode]['asan'], mode
    for mode in CTRL:
        assert nb[mode]['log_sha256'] == na[mode]['log_sha256'], ('control changed', mode)
    # ASan before: each out-of-map mode (tall and wide) reports a
    # sanitizer READ from its own scan function -- the tall modes as a
    # global-buffer-overflow of the borg_grids row pointer (size 8),
    # the wide modes as a heap-buffer-overflow of the grid byte
    # (size 2); the kinds are kept in the recorded rows.  The
    # normal/fit controls complete cleanly.
    OOB = [m for m in MODES if m not in ('light-normal', 'light-fit',
                                         'vault-normal', 'dig-normal')]
    for mode in OOB:
        assert ab[mode]['exit'] != 0 and not ab[mode]['passed'], mode
        assert ab[mode]['asan'] and not ab[mode]['assert_abort'], mode
        assert ab[mode]['asan_site'] == FLIP_SITE[mode], \
            (mode, ab[mode]['asan_site'])
    for mode in CTRL:
        assert ab[mode]['exit'] == 0 and ab[mode]['passed'], mode
        assert not ab[mode]['asan'], mode
    # ASan after: every mode passes report-free; the controls are
    # byte-identical to their asan-before logs.
    for mode in MODES:
        assert aa[mode]['exit'] == 0 and aa[mode]['passed'], mode
        assert not aa[mode]['asan'] and not aa[mode]['assert_abort'], mode
        assert aa[mode]['outcome'] == ROWS[mode], (mode, aa[mode]['outcome'])
    for mode in CTRL:
        assert ab[mode]['log_sha256'] == aa[mode]['log_sha256'], ('asan control changed', mode)
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
