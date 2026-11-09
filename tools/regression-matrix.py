#!/usr/bin/env python3
"""Rerun the accumulated prior-fixture regression matrix against a product build.

Every earlier native carry's fixture is linked against the given build's
core objects and executed, and each case is checked against its recorded
expectation:

* local-baseline groups (the 48 groups of the 0049-era matrix plus the
  kits retained under .worktrees/ since 0050) are also compared
  value-for-value against the OUTCOME rows of their recorded baseline
  logs, and byte-identity to those baselines is reported per case.  A
  byte difference is information, not a failure: later carries
  legitimately touch shared paths.  A row difference is a failure unless
  the mode declares an intentional transition.
* source-tracker kit groups (the milestone-6/0064-0067 kits whose
  worktrees are retired; the fixtures are fetched at the ledger's
  evidence pins through the kit's own run-cases.py) must pass every mode,
  and the rows recorded here become their baseline for future reruns.
  recallmana-157 is the declared standing exception: the unchanged kit
  fixture stays red on the product since the 0053 flee branch (asserted
  by tools/verify-recallmana.py; the fail-before/pass-after proof used an
  adapted one-line fixture, see RECALL-MANA.md and the milestone 6
  layered-interaction section).

Declared intentional transitions (from the original 0049-era run, kept
asserted): dispel-248 'undead' must keep the losdispel-326 replaced
launch values and the undead refusal outcome; dispel-259 'reserve' and
'clear' must keep failing (the blast scan the losdispel correction made
reachable moves their absolute values).

Usage (under the shared validation lock):
  python3 tools/regression-matrix.py --build build/native --output artifacts/m7-matrix
Requires the repo-root baseline trees (artifacts/, .worktrees/) for the
local groups and the source-tracker remote for the kit groups.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# name, baseline dir (repo-root relative), env tag, modes, options.
# Options: scenario= overrides the fixture source; no_profile omits the
# TAG_PROFILE variable (the fixture does not read it); env= adds fixed
# environment; fail= modes expected not to pass (with reason);
# rows_free= modes exempt from the baseline-row comparison;
# rows_must= extra required OUTCOME pairs for a mode;
# baseline_log= callable giving the baseline log name for a mode.
GROUPS = [
    # --- the 0049-era matrix (carries 1-48) ---
    ('swap', 'artifacts/per-spell-carry/regressions/swap', 'CBUG0066',
     ('armour-better', 'weapon-better', 'armour-only', 'weapon-only', 'tie',
      'no-benefit', 'both-helpful', 'electric-weapon', 'fire-armour'), {}),
    ('knockout', 'artifacts/per-spell-carry/regressions/knockout', 'CBUG0002',
     ('knockout', 'heavy-stun', 'paralysis', 'none'),
     {'rows_free': ('paralysis',),
      'rows_must': {'paralysis': {'delta': 3}},
      'rows_note': 'paralysis: painmsg-197 (0071) shifts the absolute reaction '
                   'counts by +1 (reactions_before 0 -> 1, after 3 -> 4) while '
                   'the knockout fix invariant delta=3 is preserved — attributed '
                   'by rerunning the mode at the 0070-after build (0/3) and the '
                   '0071-applied build (1/4)'}),
    ('preparation', 'artifacts/per-spell-carry/regressions/preparation', 'CBUG0094',
     ('regen-only', 'speed-wins', 'speed-only', 'already-active', 'unlearned',
      'low-mana', 'town', 'blind', 'confused'), {}),
    ('cold-protection', 'artifacts/per-spell-carry/regressions/cold-protection', 'CBUG0004',
     ('acid-only', 'cold-only', 'neither', 'both', 'physical-acid-control',
      'physical-cold-control'), {}),
    ('rings', 'artifacts/per-spell-carry/regressions/rings', 'CBUG0062',
     ('left-ready', 'right-charging-left-ready', 'right-control', 'both-ready',
      'no-ring', 'left-charging', 'blind-control'), {}),
    ('potion-timing', 'artifacts/per-spell-carry/regressions/potion-timing', 'CBUG0061',
     ('long-gap', 'recent', 'boundary-four', 'same-turn', 'bypass-control',
      'first-use', 'first-turn', 'empty-control', 'reserve-control'), {}),
    ('itangast', 'artifacts/per-spell-carry/regressions/itangast', 'CBUG0086',
     ('named-dragon', 'ogre-control', 'unseen-control', 'it-control',
      'lower-it-control'), {}),
    ('shot-path', 'artifacts/per-spell-carry/shot-path-interaction', 'SHOTPATH279',
     ('clear-path', 'blocked', 'ball-control', 'direct-control',
      'boulder-control', 'boulder-blocked'), {}),
    ('per-spell', '.worktrees/per-spell/artifacts/per-spell/scenarios', 'CBUG0048',
     ('clear-path', 'blocked', 'ball-control', 'direct-control',
      'boulder-control'),
     {'baseline_log': lambda mode: f'both-after-{mode}.log'}),
    ('glyph', '.worktrees/glyph-tracker/artifacts/glyph/adapted', 'CBUG0102',
     ('stairs', 'clear-floor', 'pairing'), {}),
    ('missile', '.worktrees/missile-no-target/artifacts/missile/scenarios', 'M254',
     ('no-target', 'live-shot', 'simulated'), {}),
    ('tp-other', '.worktrees/tp-other-skip/artifacts/tp/scenarios', 'CBUG0051',
     ('two-phase', 'no-morgoth-phase', 'single'), {}),
    ('dispel', '.worktrees/dispel-filter/artifacts/dispel/adapted', 'D248',
     ('living', 'undead', 'bolt'),
     {'scenario': 'tools/dispel-filter-scenario.c',
      'rows_free': ('undead',),
      'rows_must': {'undead': {'hp_before': 47, 'hp_after': 47, 'hp_lost': 0,
                               'undead': 1}}}),
    ('arc', '.worktrees/arc-angle/artifacts/arc/scenarios', 'A253',
     ('arc-bystander', 'arc-both'), {}),
    ('munchkin', '.worktrees/munchkin-stair/artifacts/m244/scenarios', 'M244',
     ('phantom', 'on-stair'), {}),
    ('vampire', '.worktrees/vampire-strike/artifacts/v257/scenarios', 'V257',
     ('near-far', 'near-near', 'far'), {}),
    ('slay', '.worktrees/slay-traits/artifacts/slay/scenarios', 'S239',
     ('animal', 'nonanimal'), {}),
    ('detect', '.worktrees/detect-panel/artifacts/d290/scenarios', 'D290',
     ('stale', 'fresh'), {}),
    ('activ', '.worktrees/activ-lookup/artifacts/a260/scenarios', 'A260',
     ('miswired', 'control'), {}),
    ('reserve', '.worktrees/reserve-bolt/artifacts/r258/scenarios', 'R258',
     ('veto', 'control'), {}),
    ('dispel259', '.worktrees/dispel-reserve/artifacts/d259/scenarios', 'D259',
     ('reserve', 'clear'),
     {'fail': ('reserve', 'clear'),
      'fail_reason': 'losdispel-326 makes the radius-10 blast scan reachable; '
                     'the absolute eq moves (recorded +296 at the 0049 tip)',
      'rows_free': ('reserve', 'clear')}),
    ('losdispel', '.worktrees/losdispel/artifacts/l326/scenarios', 'L326',
     ('storm', 'control'), {}),
    ('staff', '.worktrees/staff-holy/artifacts/s262/scenarios', 'S262',
     ('holy', 'control'), {}),
    ('blind', '.worktrees/blind-frighten/artifacts/b261/adapted', 'B261',
     ('blind', 'control'), {}),
    ('text', '.worktrees/text-multibyte/artifacts/t287/scenarios', 'T287',
     ('multibyte', 'control'),
     {'skip': 'retired: targets the pre-0068 five-argument borg_what_text '
              'signature and no longer compiles against the tip; superseded '
              'by the text-bufsize kit (0068) in this matrix'}),
    ('calcreload', '.worktrees/calc-reload/artifacts/c325/scenarios', 'T325',
     ('reload', 'control'), {'no_profile': True}),
    ('staletarget', '.worktrees/stale-target/artifacts/s322/scenarios', 'T322',
     ('stale', 'control'), {}),
    ('glowoverflow', '.worktrees/glow-overflow/artifacts/g311/scenarios', 'T311',
     ('glow', 'control'), {}),
    ('light', '.worktrees/light-modifier/artifacts/l238/scenarios', 'T238',
     ('phial', 'torch'), {}),
    ('surrounded', '.worktrees/surrounded-traps/artifacts/s312/scenarios', 'T312',
     ('traps', 'walls'), {}),
    ('homeblows', '.worktrees/home-blows/artifacts/h313/scenarios', 'T313',
     ('stack', 'single'), {}),
    ('lunal', '.worktrees/lunal-state/artifacts/l314/scenarios', 'T314',
     ('town', 'pack'), {}),
    ('opblock', '.worktrees/opblock-leak/artifacts/o324/scenarios', 'T324',
     ('operators', 'control'), {'no_profile': True}),
    ('calfree', '.worktrees/calfree-tokens/artifacts/c323/scenarios', 'T323',
     ('free', 'control'), {'no_profile': True}),
    ('brand', 'artifacts/b240/scenarios', 'N240', ('brand', 'control'), {}),
    ('stairtrack', 'artifacts/s232/scenarios', 'T232', ('known', 'fresh'), {}),
    ('acidarc', 'artifacts/a252/scenarios', 'AC252', ('edge', 'near', 'empty'), {}),
    ('outoflight', 'artifacts/o229/scenarios', 'OL229',
     ('dying', 'lit', 'everburn', 'dead'), {}),
    ('mapwall', 'artifacts/m212/scenarios', 'MW212',
     ('door-close', 'door-open', 'no-change'), {}),
    ('enlightenment', 'artifacts/e065/scenarios', 'CBUG0065',
     ('dungeon', 'town-control', 'unknown-control', 'unrelated-control',
      'augmentation-dungeon', 'augmentation-town'), {}),
    ('stairreturn', 'artifacts/s230/scenarios', 'SR230',
     ('stairs-dead-torch', 'lit', 'dead-no-stairs'), {}),
    ('blowname', 'artifacts/b247/scenarios', 'BW247', ('plain',),
     {'env': {'ASAN_OPTIONS': 'halt_on_error=0:detect_leaks=0'},
      'baseline_log': lambda mode: 'normal-after.log'}),
    ('excavate', 'artifacts/e236/scenarios', 'EV236', ('excavate', 'no-target'), {}),
    ('calllight', 'artifacts/cl231/scenarios', 'CL231', ('own-open-door', 'floor'), {}),
    ('gloves', 'artifacts/gl205/scenarios', 'GL205',
     ('glove-fa', 'plain', 'have-fa'), {}),
    ('detectcarry', 'artifacts/dc219/scenarios', 'DC219',
     ('new-level', 'same-level'), {}),
    ('maimfoe', 'artifacts/mf256/scenarios', 'MF256',
     ('wrong-return', 'single', 'none'), {}),
    ('recalldepth', 'artifacts/rd310/scenarios', 'RD310',
     ('endgame', 'generic', 'mismatch'), {}),
    # --- kits retained under .worktrees/ since 0050 ---
    ('glowtrace-213', '.worktrees/glowtrace/artifacts/gt213/scenarios', 'GLOW213',
     ('main',), {'no_mode_env': True,
                 'baseline_log': lambda mode: 'normal-after-main.log'}),
    ('glow-isglow', '.worktrees/glow-isglow/artifacts/gtisg/scenarios', 'GLOW213',
     ('main', 'door', 'torchlit', 'unlit'), {}),
    ('text-bufsize', '.worktrees/text-bufsize/artifacts/t287buf/scenarios', 'T287',
     ('multibyte', 'control', 'wide'), {}),
    ('iswarded-198', '.worktrees/iswarded/artifacts/isw198/scenarios', 'ISW198',
     ('rune-town', 'hit-town', 'rune-inside', 'hit-inside', 'hit-noglyph'), {}),
    ('painmsg-197', '.worktrees/pain-spastic/artifacts/pm197/scenarios', 'PM197',
     ('held', 'command', 'uncommand', 'shapefail', 'stun', 'hurt', 'puff'),
     {'fail': ('puff',),
      'fail_reason': 'outside the fix: the puff line has no monster name and '
                     'stays unrecognised in both phases (kit contract)'}),
    ('trollswap-201', '.worktrees/swap-drop/artifacts/ts201/scenarios', 'TS201',
     ('troll-orc', 'troll-plain'), {}),
    ('drophole-136', '.worktrees/swap-drop/artifacts/dh136/scenarios', 'DH136',
     ('salt-water', 'spare-esp', 'restore-mana', 'level30'), {}),
    ('wearskip-85', '.worktrees/wearskip/artifacts/ws85/scenarios', 'WS85',
     ('tight', 'roomy', 'nocloak'), {}),
    ('lantern-90', '.worktrees/lantern/artifacts/ln90/scenarios', 'LN90',
     ('empty', 'single'), {}),
    ('homebanish-54', '.worktrees/homebanish/artifacts/hb54/scenarios', 'HB54',
     ('banish', 'mass'), {}),
    ('necrolight-crash', 'docs/audit/c-reports/necrolight-296-crash', 'NL296',
     ('stale-town', 'stale-far', 'lit', 'dark', 'mage-lit'), {}),
]

# Source-tracker kit groups (retired worktrees; fixtures at the ledger's
# evidence pins). name, evidence ref, declared expectations.
KIT_GROUPS = [
    ('stairrange-245', '3c9a75e20233', {}),
    ('clockreset-246', '85ff225404d9', {}),
    ('dangerflee-156', '809e556b39e4', {}),
    ('recallmana-157', 'b6bd252e1c9b',
     {'fail': ('lowmana',),
      'fail_reason': 'standing 0053 interaction: an ordinary Borg in excessive '
                     'danger flees via desperate stairs before the recall-wait '
                     'line, so the unchanged lowmana fixture stays red '
                     '(verify-recallmana asserts exactly this: lowmana red, '
                     'halfmana green, restore_mana=0 in both)',
      'rows_must': {'lowmana': {'restore_mana': 0}, 'halfmana': {'restore_mana': 0}}}),
    ('deskstair-153', '366fd1b08c4d', {}),
    ('backaway-155', 'fa0293e587d8', {}),
    ('cfghang-141', 'a3164a61b830', {}),
    ('cfgminus-142', '18f79a3cc631', {}),
    ('cfgmissing-144', '1ff9ca1e59d6', {}),
    ('countsell-134', '68b23b2a1b2e', {}),
    ('drainedive-235', '557c85260f8b', {}),
    ('respois-184', 'af01d73ccfcb', {}),
    ('respoiswar-185', '6f130a4eea68', {}),
    ('spastic-146', 'da9a39f4da30', {}),
    ('glyphflow-345', 'fbe06401c54c', {}),
    ('swapacid-199', '9eca003a5896', {}),
    ('staircycle-403', '43dee40ed052', {}),
]

TAG_RE = re.compile(r"(\w+)'?\s*\+\s*'?_PROFILE|(\w+)_PROFILE")


def git_show(ref, path):
    return subprocess.check_output(['git', 'show', ref + ':' + path], cwd=ROOT)


def git_ls(ref, path):
    out = subprocess.check_output(['git', 'ls-tree', '--name-only', ref, path],
                                  cwd=ROOT, text=True)
    return [line.rstrip('/') for line in out.splitlines() if line.strip()]


def baseline_rows(text):
    m = re.search(r'OUTCOME (.*)', text)
    if not m:
        return None
    return {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', m.group(1))}


def baseline_log_name(dirpath, mode, opts):
    fn = opts.get('baseline_log')
    if fn:
        return fn(mode)
    for name in (f'{mode}.log', f'normal-after-{mode}.log', f'after-{mode}.log'):
        if (dirpath / name).exists():
            return name
    return None


def run_group(name, tag, modes, dest, objects, opts, build):
    link = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
            '-I' + str(ROOT / 'src/tests'), str(dest / 'scenario.c'),
            *map(str, objects), '-lm', '-o', str(dest / 'scenario')]
    with (dest / 'link.log').open('w') as log:
        subprocess.run(link, stdout=log, stderr=subprocess.STDOUT, check=True)
    cases = {}
    for mode in modes:
        env = {'LC_ALL': 'C.UTF-8'}
        if not opts.get('no_mode_env'):
            env[tag + '_MODE'] = mode
        if not opts.get('no_profile'):
            env[tag + '_PROFILE'] = str(dest / 'profile')
        env.update(opts.get('env', {}))
        result = subprocess.run(
            [str(dest / 'scenario'), '-v'], cwd=build / 'game', env=dict(os.environ, **env),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        text = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout.decode(errors='replace'))
        (dest / (mode + '.log')).write_text(text)
        passed = ' finished: 1/1 passed' in text
        rows = baseline_rows(text)
        case = {'exit': result.returncode, 'passed': passed,
                'outcome': rows or {},
                'log_sha256': hashlib.sha256(text.encode()).hexdigest()}
        expecting_fail = mode in opts.get('fail', ())
        if expecting_fail:
            case['expectation'] = 'fail: ' + opts['fail_reason']
            case['ok'] = (not passed)
        else:
            case['expectation'] = 'pass'
            case['ok'] = result.returncode == 0 and passed
        if mode in opts.get('rows_must', {}):
            for key, want in opts['rows_must'][mode].items():
                if (rows or {}).get(key) != want:
                    case['ok'] = False
                    case.setdefault('row_mismatch', {})[key] = {'want': want, 'got': (rows or {}).get(key)}
        blname = opts.get('_baseline_logs', {}).get(mode)
        if blname:
            previous = (opts['_baseline_dir'] / blname).read_text(errors='replace')
            prow = baseline_rows(previous)
            case['baseline_rows'] = prow
            case['baseline_log_sha256'] = hashlib.sha256(previous.encode()).hexdigest()
            case['byte_identical'] = text == previous
            if prow is not None and rows is not None and mode not in opts.get('rows_free', ()):
                if rows != prow:
                    case['ok'] = False
                    case['row_mismatch'] = {'baseline': prow, 'got': rows}
        cases[mode] = case
        print(f'  {name}/{mode}: {"OK" if case["ok"] else "MISMATCH"} '
              f'passed={passed} rows={rows}', flush=True)
    return cases


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', default=ROOT / 'build/native', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--only', action='append', default=[],
                   help='run only these groups (repeatable; smoke tests)')
    args = p.parse_args()
    build = args.build.resolve()
    objects = sorted((build / 'CMakeFiles/OurCoreLib.dir').rglob('*.o')) + \
        sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    assert len(objects) >= 150, 'build objects missing'
    out = args.output.resolve()
    assert not out.exists(), f'{out} exists'
    out.mkdir(parents=True)
    report = {'build': str(build), 'groups': {}, 'total_cases': 0, 'ok': True}

    for name, dir_rel, tag, modes, opts in GROUPS:
        if args.only and name not in args.only:
            continue
        if opts.get('skip'):
            report['groups'][name] = {'kind': 'local', 'baseline': dir_rel,
                                      'skipped': True, 'reason': opts['skip'],
                                      'cases': {}, 'ok': True}
            print(f'{name}: SKIPPED ({opts["skip"][:60]}...)', flush=True)
            continue
        print(name, flush=True)
        baseline = ROOT / dir_rel
        opts = dict(opts)
        opts['_baseline_dir'] = baseline
        opts['_baseline_logs'] = {m: n for m in modes
                                  if (n := baseline_log_name(baseline, m, opts))}
        missing = [m for m in modes if m not in opts['_baseline_logs']]
        assert not missing, (name, 'baseline logs missing', missing)
        dest = out / name
        dest.mkdir()
        (dest / 'profile').mkdir()
        scenario = opts.get('scenario')
        if scenario:
            (dest / 'scenario.c').write_bytes((ROOT / scenario).read_bytes())
        else:
            source = (baseline / 'scenario.c').read_text()
            (dest / 'scenario.c').write_text(source.replace(str(baseline), str(dest)))
        # companion headers and data some fixtures generate or carry
        for extra in baseline.glob('*.h'):
            (dest / extra.name).write_bytes(extra.read_bytes())
        for extra in baseline.glob('*.txt'):
            (dest / extra.name).write_bytes(extra.read_bytes())
        (dest / 'profile/borg.txt').write_bytes((baseline / 'profile/borg.txt').read_bytes())
        cases = run_group(name, tag, modes, dest, objects, opts, build)
        report['groups'][name] = {'kind': 'local', 'baseline': dir_rel,
                                  'cases': cases,
                                  'ok': all(c['ok'] for c in cases.values())}
        report['total_cases'] += len(cases)

    for name, ref, opts in KIT_GROUPS:
        if args.only and name not in args.only:
            continue
        print(name, flush=True)
        opts = dict(opts)
        entries = git_ls(ref, 'docs/audit/c-reports/')
        kits = [d for d in entries
                if 'run-cases.py' in subprocess.check_output(
                    ['git', 'ls-tree', '--name-only', ref, d + '/'],
                    cwd=ROOT, text=True)]
        assert len(kits) == 1, (name, 'kit dir ambiguous', kits)
        prefix = kits[0]
        dest = out / name
        dest.mkdir()
        for path in subprocess.check_output(
                ['git', 'ls-tree', '-r', '--name-only', ref, prefix + '/'],
                cwd=ROOT, text=True).splitlines():
            rel = path[len(prefix):].lstrip('/')
            if not rel:
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git_show(ref, path))
        source = (dest / 'run-cases.py').read_text()
        match = TAG_RE.search(source)
        tag = match.group(1) or match.group(2)
        (dest / 'profile/borg.txt').write_bytes(git_show(ref, prefix + '/borg.txt'))
        # The kit's runner sets the scenario's cwd to the binary's parent;
        # the game resolves its data (gamedata/) from the cwd, so the
        # linked binary goes into the build's game directory like the
        # original observer builds did.
        binary = build / 'game' / ('m7kit-' + name)
        link = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'),
                '-I' + str(ROOT / 'src/tests'), str(dest / 'scenario.c'),
                *map(str, objects), '-lm', '-o', str(binary)]
        with (dest / 'link.log').open('w') as log:
            subprocess.run(link, stdout=log, stderr=subprocess.STDOUT, check=True)
        env = dict(os.environ, LC_ALL='C.UTF-8')
        subprocess.run(['python3', str(dest / 'run-cases.py'), 'after', str(binary), str(dest)],
                       cwd=dest, env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.STDOUT, timeout=1200)
        rows = json.loads((dest / 'after-results.json').read_text())
        cases = {}
        for mode in sorted(rows):
            row = rows[mode]
            expecting_fail = opts.get('fail_all') or mode in opts.get('fail', ())
            if expecting_fail:
                ok = not row['passed']
            else:
                ok = row['exit'] == 0 and row['passed']
            case = {'exit': row['exit'], 'passed': row['passed'],
                    'outcome': row.get('outcome', {}),
                    'expectation': ('fail: ' + opts['fail_reason']) if expecting_fail else 'pass',
                    'ok': ok}
            for key, want in opts.get('rows_must', {}).get(mode, {}).items():
                if case['outcome'].get(key) != want:
                    case['ok'] = False
                    case.setdefault('row_mismatch', {})[key] = {'want': want, 'got': case['outcome'].get(key)}
            if (dest / f'after-{mode}.log').exists():
                text = (dest / f'after-{mode}.log').read_text(errors='replace')
                case['log_sha256'] = hashlib.sha256(text.encode()).hexdigest()
            cases[mode] = case
            print(f'  {name}/{mode}: {"OK" if ok else "MISMATCH"} '
                  f'passed={row["passed"]} rows={row.get("outcome")}', flush=True)
        report['groups'][name] = {'kind': 'kit', 'evidence_ref': ref, 'prefix': prefix,
                                  'cases': cases,
                                  'ok': all(c['ok'] for c in cases.values())}
        report['total_cases'] += len(cases)

    report['ok'] = all(g['ok'] for g in report['groups'].values())
    (out / 'regression-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    failed = [n for n, g in report['groups'].items() if not g['ok']]
    print(f'total cases: {report["total_cases"]}; failed groups: {failed or "none"}; '
          f'matrix ok: {report["ok"]}', flush=True)


if __name__ == '__main__':
    main()
