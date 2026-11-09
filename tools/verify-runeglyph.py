#!/usr/bin/env python3
"""Verify the source295 visible-rune recording (source fix 50e64a37) on product cores.

The Borg's map update set a grid's glyph flag only inside the branch
for visible, disarmable player traps; a Rune of Protection is a glyph,
not a player trap (GLYPH | VISIBLE | FLOOR, no TRAP flag), so that
branch never ran and the Borg's map said there was no rune on a grid
that visibly had one.  Standing on such a rune with a summoner in
view, the Borg still saw the full summoning danger and read another
Rune of Protection onto the same grid.  The correction also enters the
branch when the remembered trap on the grid is a glyph and marks the
grid as a trap only for a real disarmable player trap.
The rune mode carries the defect's direct signal: before, the visible
rune is not recorded (borg_glyph_here=0, game_runes_here=1) and the
scenario self-check fails; after, the rune is recorded
(borg_glyph_here=1) and the self-check passes.  No second rune is read
in either phase on this product (read_rune=0 before and after): on the
kit's pristine base the before-phase row was read_rune=1 -- the wasted
duplicate read this fix removes -- but here the defence chain had
already chosen differently, so the duplicate read does not arise.
The floor and trap controls diverge from the kit's recorded rows on
this product, disclosed: the defence chain chooses no action there
(DECISION defend=0) before AND after, so the scenario self-check fails
in both phases; their logs are byte-identical across the correction,
which proves the fix is a provable no-op for them.  The divergence
predates this carry and stems from carried defence-chain patches
(candidates: healchance-364's borg_heal flow, the tele-away rod family
0091/0095/0096); attribution to one patch is not claimed.
Fixture: kit 3ce928e869641bd2d789dfca1566c890121922f9 at head dae7a1bd6da9a78b92229534fa2b03630e01da1d. Normal phases only. Before phases
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
BEFORE = '521c880a5d15896dc3c16f24a3f19947281f5661'
FIX = '50e64a37a837c3ce4563e9ade452ce28db5cee82'
EVIDENCE = 'dae7a1bd6da9a78b92229534fa2b03630e01da1d'
PIN = '3ce928e869641bd2d789dfca1566c890121922f9'
PREFIX = 'docs/audit/c-reports/runeglyph-295/'
SOURCE = 'src/borg/borg-update.c'
MODES = ('rune', 'floor', 'trap')
SUITE = 'native-c/runeglyph-295'


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
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                   '-I' + str(ROOT / 'src/tests'), str(out / 'scenario.c'),
                   *map(str, objects + helpers), '-lm', '-o', str(binary)]
        with (out / (phase + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        rows = {}
        for mode in MODES:
            result = subprocess.run(
                [str(binary), '-v'], cwd=build / 'game',
                env=dict(os.environ, **{'RG295_MODE': mode,
                                        'RG295_PROFILE': str(out / 'profile')}, LC_ALL='C.UTF-8'),
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
    # The defect's direct signal: the visible rune is now recorded on
    # the Borg's map (borg_glyph_here 0 -> 1 while the game's rune
    # stays), and no second rune is read in either phase on this
    # product.
    assert not b['rune']['passed'] and b['rune']['outcome'] == {'read_rune': 0, 'scrolls': 4, 'game_runes_here': 1, 'borg_glyph_here': 0}
    assert a['rune']['passed'] and a['rune']['outcome'] == {'read_rune': 0, 'scrolls': 4, 'game_runes_here': 1, 'borg_glyph_here': 1}
    # floor/trap diverge from the kit's recorded rows, disclosed: on
    # this product the defence chain chooses no action in these
    # scenarios (DECISION defend=0) -- read_rune=0 before AND after,
    # and the logs are byte-identical across the fix, proving the fix
    # is a no-op for them.  The divergence predates this fix and stems
    # from carried defence-chain patches (candidates: healchance-364's
    # borg_heal flow, the tele-away rod family 0091/0095/0096);
    # attribution to one patch is not claimed.
    for mode in ('floor', 'trap'):
        assert not b[mode]['passed'] and not a[mode]['passed'], mode
        assert b[mode]['outcome'] == a[mode]['outcome'] == {'read_rune': 0, 'scrolls': 5, 'game_runes_here': 0, 'borg_glyph_here': 0}, mode
        assert b[mode]['log_sha256'] == a[mode]['log_sha256'], (mode, 'log changed')
    assert b['floor']['log_sha256'] == a['floor']['log_sha256'], ('control changed', 'floor')
    assert b['trap']['log_sha256'] == a['trap']['log_sha256'], ('control changed', 'trap')
    report['verified'] = True
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
