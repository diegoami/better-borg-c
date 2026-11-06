#!/usr/bin/env python3
"""Export a curated native death dossier; full runs/saves/builds stay outside Git."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def source_ledger(commit):
    exists = subprocess.run(['git', 'cat-file', '-e', commit + ':patches/series.json'],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if exists.returncode:
        subprocess.run(['git', 'cat-file', '-e', commit + '^{commit}'], cwd=ROOT, check=True)
        return {'baseline': commit, 'patches': []}
    return json.loads(subprocess.check_output(['git', 'show', commit + ':patches/series.json'], cwd=ROOT))


def identity(run):
    return {k: run[k] for k in ('seed', 'configuration_sha256', 'input_sha256')}


def observations(lines, turn):
    selected = []
    for line in lines:
        if line.startswith('BORG ') and int(line.split()[1]) < turn:
            selected.append(line)
        elif line.startswith('STATE '):
            parts = line.split()
            t = int(next(s.split('=')[1] for s in parts if s.startswith('turn=')))
            if parts[1] not in ('death', 'turn_cap', 'unexpected_stop') and t < turn:
                selected.append(line)
        elif line.startswith(('CHARACTER ', 'OPTIONS', 'ACTIVE_OPTIONS', 'BORG_OPTIONS')):
            selected.append(line)
    return selected


def calendar_context(run):
    return run.get('calendar_context', {'status': 'not captured by legacy runner',
        'limit': 'Native seasonal monster availability uses the calendar; do not substitute the current date for this old run.'})


def capture(args):
    original = args.run.resolve()
    run = read(original / 'result.json')
    if run['outcome'] != 'death' or run.get('cause') in ('Retiring', 'Quitting'):
        raise ValueError('A natural death is required; caps, failures and retirement are not deaths')
    terminal = run['states'][-1]
    if terminal['kind'] != 'death' or not terminal['dead']:
        raise ValueError('Terminal native state does not confirm death')
    out = args.output.resolve()
    key = {'source': run['build']['source_commit'], 'binary': run['build']['binary_sha256'],
           'seed': run['seed'], 'start_save': sha(original / 'start.save'),
           'turn': terminal['turn'], 'cause': run['cause']}
    if (out / 'record.json').exists() and read(out / 'record.json')['identity'] != key:
        raise ValueError('Existing death identity is immutable; use a new dossier for another build/case')
    lines = (original / 'trace.txt').read_text().splitlines()
    attempts = []
    builds = {}
    for role, paths in (('original', [original]), ('repeat', args.repeat), ('reference', args.reference)):
        for index, p in enumerate(paths):
            p = p.resolve()
            r = read(p / 'result.json')
            if identity(r) != identity(run) or sha(p / 'start.save') != key['start_save']:
                raise ValueError('Attempt has different starting conditions')
            same_trace = (p / 'trace.txt').read_bytes() == (original / 'trace.txt').read_bytes()
            if role == 'repeat' and (r['build']['source_commit'] != key['source'] or
                                     r['build']['binary_sha256'] != key['binary'] or not same_trace):
                raise ValueError('Unchanged repeat diverged; record a replay-fidelity investigation')
            build_name = 'build.json' if role in ('original', 'repeat') else f'reference-{index + 1}.build.json'
            builds[build_name] = r['build']
            attempts.append({'role': role, 'outcome': r['outcome'], 'cause': r.get('cause'),
                             'source_commit': r['build']['source_commit'], 'binary_sha256': r['build']['binary_sha256'],
                             'build_record': build_name, 'upstream_baseline': source_ledger(r['build']['source_commit'])['baseline'],
                             'carried_patches': source_ledger(r['build']['source_commit'])['patches'], 'harness_commit': r['harness_commit'],
                             'runner_sha256': r['runner_sha256'], 'calendar_context': calendar_context(r), 'terminal': r['states'][-1],
                             'wall_seconds': r['wall_seconds'], 'same_complete_trace': same_trace,
                             'raw_directory': str(p), 'result_sha256': sha(p / 'result.json'),
                             'trace_sha256': sha(p / 'trace.txt'), 'recent_save_sha256': sha(p / 'recent.save')})
    windows = []
    for p in args.window:
        p = p.resolve()
        r = read(p / 'result.json')
        if (identity(r) != identity(run) or r['build']['source_commit'] != key['source'] or
                r['build']['binary_sha256'] != key['binary'] or sha(p / 'start.save') != key['start_save']):
            raise ValueError('Window is from another source/build/start')
        turn = r['states'][-1]['turn']
        if r['outcome'] != 'turn_cap' or not turn < terminal['turn']:
            raise ValueError('Window must stop before the original death')
        if observations(lines, turn) != observations((p / 'trace.txt').read_text().splitlines(), turn):
            raise ValueError('Pre-window trajectory observations differ')
        windows.append({'offset_engine_turns': terminal['turn'] - turn, 'turn': turn,
                        'terminal': r['states'][-1], 'matching_prior_observations': True,
                        'phase': 'Immediately after world-turn increment, before remaining processing at that tick',
                        'snapshot': f"snapshots/T-minus-{terminal['turn'] - turn}.txt",
                        'raw_directory': str(p), 'result_sha256': sha(p / 'result.json'),
                        'native_map_sha256': sha(p / 'archive/Measure.map')})
    if (out / 'record.json').exists():
        previous = read(out / 'record.json')
        if {a['result_sha256'] for a in previous['attempts']} - {a['result_sha256'] for a in attempts}:
            raise ValueError('Existing attempts cannot be dropped; retain the original repeat/reference arguments')
    for name, data in builds.items():
        if (out / name).exists() and read(out / name) != data:
            raise ValueError('An existing build identity cannot be replaced')
    if (original / 'input.txt').exists() and sha(original / 'input.txt') != run['input_sha256']:
        raise ValueError('Input file no longer matches the run record')
    # Validate everything before writing; a later build must not replace an old death.
    out.mkdir(parents=True, exist_ok=True)
    (out / 'snapshots').mkdir(exist_ok=True)
    for name, data in builds.items():
        write(out / name, data)
    ledger = source_ledger(key['source'])
    for w in windows:
        native = Path(w['raw_directory']) / 'archive/Measure.map'
        (out / w['snapshot']).write_text(native.read_text().split('[Last Messages]')[0])
    shutil.copy2(original / 'archive/Measure.map', out / 'terminal.map.txt')
    if (original / 'input.txt').exists():
        shutil.copy2(original / 'input.txt', out / 'input.txt')
    tail = [s for s in lines if s.startswith('BORG ') and int(s.split()[1]) >= terminal['turn'] - 200]
    tail += ['', '[Terminal native state/cause]'] + [s for s in lines if s.startswith(('STATE death ', 'CAUSE '))]
    tail += ['', '[Recent native message buffer; no independent timestamps]'] + [s for s in lines if s.startswith('MESSAGE ')]
    (out / 'events.log').write_text('\n'.join(tail) + '\n')
    options = {}
    for s in lines:
        if s.startswith(('OPTIONS ', 'ACTIVE_OPTIONS ', 'BORG_OPTIONS ')):
            parts = s.split()
            options[parts[0]] = {k: int(v) for k, v in (p.split('=', 1) for p in parts[1:])}
    record = {'schema': 'better-borg-c/death-record@1', 'id': args.id, 'identity': key,
              'encounter_family': 'start-' + key['start_save'], 'raw_cause': run['cause'],
              'upstream_baseline': ledger['baseline'], 'carried_patches': ledger['patches'],
              'character': run['character'], 'native_character': next(s for s in lines if s.startswith('CHARACTER ')),
              'options': options, 'calendar_context': calendar_context(run), 'command': run['command'], 'environment': run['environment'], 'cwd': run['cwd'],
              'limits': {k: run[k] for k in ('turn_cap', 'wall_limit_seconds', 'stall_limit_seconds')},
              'attempts': attempts, 'windows': sorted(windows, key=lambda w: w['turn']),
              'issue': args.issue, 'investigation': args.investigation,
              'recording_scope': 'Exact selected Borg observations, terminal recent messages and native map snapshots; not video or a complete every-turn engine event stream',
              'curation': 'Native maps include diagnostic/internal state and legacy death labels even at live window caps; outcomes come from result.json. Full runs, saves and builds stay outside Git.'}
    write(out / 'record.json', record)
    if not (out / 'assessment.json').exists():
        write(out / 'assessment.json', {'classification': 'unassessed', 'confidence': 'unassessed',
                                        'findings': [], 'feedback': [], 'actions': []})
    if not (out / 'report.md').exists():
        (out / 'report.md').write_text(f"# {args.id}: {run['cause']} at turn {terminal['turn']}\n\n"
            f'[Discuss this death]({args.investigation}) · [Feedback process](../FEEDBACK.md)\n\n'
            'See record.json and build.json for immutable source/build/seed/options.\n\n'
            '## Evaluation and diagnosis\n\nUnassessed; do not infer a defect from death alone.\n\n'
            '## Action items\n\nRecord issue links and evidence before changes.\n')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--id', required=True)
    p.add_argument('--repeat', action='append', type=Path, default=[])
    p.add_argument('--reference', action='append', type=Path, default=[])
    p.add_argument('--window', action='append', type=Path, default=[])
    p.add_argument('--issue', required=True)
    p.add_argument('--investigation', required=True)
    capture(p.parse_args())
