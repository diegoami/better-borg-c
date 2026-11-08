#!/usr/bin/env python3
"""Collect all natural deaths from a bounded batch of fresh recorded games."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import hashlib
import json
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


workflow = load('producer_helpers', 'death-workflow.py')
measurement = load('producer_measurement', 'measure-native.py')
reports = load('producer_reports', 'run-report.py')
BUILD_TOOLS = ('measure-native.py', 'native-observer.c', 'native-observer.h', 'native-replay.c', 'native-replay.h', 'native-inventory.h', 'native-spells.h')
DEFAULT_ISSUE = 'https://github.com/diegoami/better-borg-c/issues/163'


def seeds_for(args):
    if args.seeds is not None:
        if args.games is not None or args.seed is not None:
            raise ValueError('Use --seeds OR --games/--seed')
        seeds = args.seeds
    else:
        first = args.seed if args.seed is not None else secrets.randbits(32)
        seeds = [(first + i) % (2**32) for i in range(args.games if args.games is not None else 3)]
    if not seeds or len(set(seeds)) != len(seeds) or any(not 0 <= s <= 0xffffffff for s in seeds):
        raise ValueError('Use distinct uint32 seeds and at least one game')
    return seeds


# Include the carry ledger because death export derives provenance from the
# actual build's source commit. Documentation/launcher-only commits can reuse it.
BUILD_INPUTS = ('src', 'lib', 'cmake', 'scripts', 'm4', 'CMakeLists.txt',
                'configure.ac', 'patches/series.json')


def build_identity(commit):
    hashes = {name: workflow.sha(ROOT / 'tools' / name) for name in BUILD_TOOLS}
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]
    return workflow.artifacts() / 'builds' / (commit[:12] + '-' + fingerprint), hashes


def source_matches(source, requested):
    if source == requested:
        return True
    if not isinstance(source, str) or len(source) != 40 or any(c not in '0123456789abcdef' for c in source):
        return False
    return subprocess.run(['git', 'diff', '--quiet', source, requested, '--', *BUILD_INPUTS],
                          cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def validate_build(build, requested, hashes):
    manifest = workflow.read(build / 'build.json')
    if not isinstance(manifest, dict):
        raise ValueError('Build manifest must be an object')
    tools = manifest.get('tools_sha256')
    data = manifest.get('data_sha256')
    if (not manifest.get('complete') or not manifest.get('instrumented')
            or manifest.get('recording_schema') != 'borg-recording@1'
            or not source_matches(manifest.get('source_commit'), requested)
            or not isinstance(tools, dict) or not isinstance(data, dict) or not data
            or any(tools.get(k) != v for k, v in hashes.items())
            or workflow.sha(build / 'build/game/angband') != manifest.get('binary_sha256')):
        raise ValueError('Build must be complete, unchanged, fully recorded and match requested game/Borg source, carry ledger and observation tools')
    for name, digest in data.items():
        if workflow.sha(build / 'source' / name) != digest:
            raise ValueError(f'Cached build data changed: {name}')
    return manifest


def choose_build(args, commit):
    target, hashes = build_identity(commit)
    if args.build:
        build = args.build.resolve()
        if not build.exists():
            raise ValueError('Explicit --build does not exist; omit it to offer a recording build')
        return SimpleNamespace(path=build, manifest=validate_build(build, commit, hashes), reuse=True)
    if target.exists():
        # A changed/incomplete exact cache is preserved for investigation, never
        # overwritten or silently selected as valid historical evidence.
        return SimpleNamespace(path=target, manifest=validate_build(target, commit, hashes), reuse=True)
    candidates = []
    for folder in (workflow.artifacts() / 'builds', workflow.primary_root() / 'artifacts/headless/builds'):
        candidates.extend(folder.glob('*/build.json'))
    for path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            manifest = validate_build(path.parent, commit, hashes)
            return SimpleNamespace(path=path.parent, manifest=manifest, reuse=True)
        except (OSError, ValueError, KeyError):
            continue
    return SimpleNamespace(path=target, manifest=None, reuse=False)


def announce_build(choice, commit):
    description = measurement.git('show', '-s', '--format=%s', commit)
    print(f'Requested source: {commit[:12]} — {description}', flush=True)
    if choice.reuse:
        source = choice.manifest['source_commit']
        print(f'Current matching build: {source[:12]} — reusing {choice.path}', flush=True)
        if source != commit:
            print('Game/Borg sources and carry ledger match the requested revision; build provenance retains its original commit.', flush=True)
    else:
        print(f'No matching recording build. Will build/update to {commit[:12]} at {choice.path}', flush=True)


def approve_build(args, choice):
    if choice.reuse:
        return bool(getattr(args, 'yes', False))
    if getattr(args, 'no_build', False):
        raise ValueError('No matching build available (--no-build); no games started')
    if getattr(args, 'yes', False):
        return True
    if not sys.stdin.isatty():
        raise ValueError('A build is required. Run interactively to choose, or pass --yes to build/update; no games started')
    while True:
        answer = input('Build/update this version before starting games? [Y/n] ').strip().lower()
        if answer in ('', 'y', 'yes'):
            return True
        if answer in ('n', 'no'):
            return False


def prepare_build(args, commit):
    # Recheck inside the shared lock after the offer. Never wait for user input
    # while holding the lock, and never run an older mismatching build.
    choice = choose_build(args, commit)
    if not choice.reuse:
        if not getattr(args, '_build_approved', False):
            raise ValueError('Matching build is missing after preflight; rerun for the build offer')
        measurement.prepare(SimpleNamespace(output=choice.path, ref=commit, observe=True, recording=True, retry=False))
        _, hashes = build_identity(commit)
        manifest = validate_build(choice.path, commit, hashes)
    else:
        manifest = choice.manifest
    print(f"Running native build source: {manifest['source_commit'][:12]} ({choice.path})", flush=True)
    return choice.path


def export_death(run, issue):
    records = ROOT / 'docs/deaths'
    with workflow.locked(workflow.primary_root() / 'artifacts/headless/death-registry.lock'):
        numbers = [int(p.name[1:5]) for p in records.glob('D[0-9][0-9][0-9][0-9]-*')]
        number = max(numbers, default=0) + 1
        if number > 9999:
            raise ValueError('Four-digit death IDs exhausted')
        case_id = f'D{number:04d}'
        dossier = records / (case_id + '-collected')
        subprocess.run([sys.executable, str(ROOT / 'tools/record-death.py'), '--run', str(run),
                        '--output', str(dossier), '--id', case_id, '--issue', issue,
                        '--investigation', issue], check=True)
        subprocess.run([sys.executable, str(ROOT / 'tools/aggregate-deaths.py'), '--root', str(records)], check=True)
        return dossier


def recording_commands(run, result):
    manifest = run / 'recording.json'
    if not manifest.is_file():
        return {}
    record = workflow.read(manifest)
    if record.get('status') not in ('complete', 'incomplete') or 'files_sha256' not in record:
        return {}
    run = run.resolve()
    replay = ['./replay-borg.py', str(run)]
    if record['status'] != 'complete':
        replay.append('--view-only')
    commands = {'replay_command': shlex.join(replay)}
    if (record['status'] == 'complete' or
            (record.get('outcome') == result.get('outcome') == 'wall_timeout' and not result.get('error'))):
        commands['manual_play_command'] = shlex.join(['./play-from-replay.py', str(run), '--from-turn', 'latest'])
    return commands


def print_recording_commands(commands):
    if commands:
        print('Watch: ' + commands['replay_command'], flush=True)
        if commands.get('manual_play_command'):
            print('Play yourself (verifies prefix first): ' + commands['manual_play_command'], flush=True)


def show_collection_commands(directory, make_reports=False):
    plan = workflow.read(directory.resolve() / 'collection.json')
    for entry in plan['runs']:
        run = Path(entry['directory'])
        if not (run / 'result.json').is_file():
            print(f"Seed {entry['seed']}: no finalized recording available yet.")
            continue
        result = workflow.read(run / 'result.json')
        print(f"Seed {entry['seed']}: {result['outcome']}")
        if make_reports:
            path, _ = reports.create(run, result)
            print('Report: ' + str(path), flush=True)
            continue
        elif (run / 'reports/summary.md').is_file():
            print('Report: ' + str(run / 'reports/summary.md'), flush=True)
        commands = recording_commands(run, result)
        print_recording_commands(commands)
        if not commands:
            print('No finalized recording available yet.', flush=True)
    if make_reports:
        print('Reports index: ' + str(reports.collection_summary(directory, plan)), flush=True)


def collect(args, output, seeds, commit):
    configuration = 'borg_save_death = 1\n'
    munchkin = bool(getattr(args, 'munchkin', False))
    if munchkin:
        configuration += 'borg_munchkin_start = TRUE\n'
    # Freeze all starts and limits BEFORE results. Run every listed seed unless
    # an operational failure prevents safe collection; do not extend the budget.
    plan = {'schema': 'borg-death-collection@1', 'created_at': workflow.now(),
            'requested_source_commit': commit, 'source_commit': None, 'seeds': seeds, 'turn_cap': args.turns,
            'wall_limit_per_game_seconds': args.timeout, 'stall_timeout_seconds': args.stall_timeout,
            'stop_rule': 'listed seeds exhausted or operational failure other than wall timeout; deaths and time/turn limits start the next fresh character',
            'birth_policy': getattr(args, 'birth', 'random'),
            'borg_parameters': {'borg_munchkin_start':munchkin, 'borg_save_death':True},
            'requested_configuration_sha256':hashlib.sha256(configuration.encode()).hexdigest(),
            'character': ('Random race and class' if getattr(args, 'birth', 'random') == 'random' else 'Human Warrior') + '; default point buy; native Borg settings with declared overrides; death evidence on; cheat death and winner respawn off',
            'runner_sha256': workflow.sha(Path(__file__)), 'issue': args.death_issue,
            'runs': [], 'counts': {}, 'status': 'preparing',
            'limit': 'Death collection, not an unbiased survival-rate cohort; all attempted outcomes retained.'}
    workflow.write(output / 'collection.json', plan)
    try:
        print('Waiting for the shared native validation lock...', flush=True)
        with workflow.locked(Path('/tmp/angband-validation.lock')):
            build = prepare_build(args, commit)
            actual_source = workflow.read(build / 'build.json').get('source_commit', commit)
            plan.update(source_commit=actual_source, build=str(build), build_manifest_sha256=workflow.sha(build / 'build.json'), status='running')
            workflow.write(output / 'collection.json', plan)
            for index, seed in enumerate(seeds, 1):
                run = output / f'game-{index:03d}-seed-{seed}'
                entry = {'seed': seed, 'directory': str(run), 'outcome': 'harness_failure'}
                plan['runs'].append(entry)
                workflow.write(output / 'collection.json', plan)
                print(f'Game {index}/{len(seeds)}; seed {seed}; cap {args.turns}', flush=True)
                code = measurement.run(SimpleNamespace(build=build, output=run, seed=seed, cap=args.turns,
                    timeout=args.timeout, stall_timeout=args.stall_timeout, no_saves=False, load=None,
                    recording=True, random_birth=getattr(args, 'birth', 'random') == 'random', configuration=configuration))
                result = workflow.read(run / 'result.json')
                print('Character: ' + result.get('character', 'unknown'), flush=True)
                entry.update(outcome=result['outcome'], cause=result.get('cause'), character=result.get('character'),
                             result_sha256=workflow.sha(run / 'result.json'), wall_seconds=result.get('wall_seconds'),
                             final=result.get('states', [None])[-1] if result.get('states') else None)
                report_path, _ = reports.create(run, result)
                entry['report'] = str(report_path)
                print('Report: ' + str(report_path), flush=True)
                reports.collection_summary(output, plan)
                commands = recording_commands(run, result)
                entry.update(commands)
                print_recording_commands(commands)
                plan['counts'] = dict(Counter(e['outcome'] for e in plan['runs']))
                workflow.write(output / 'collection.json', plan)
                if result['outcome'] == 'death':
                    # Export even if runner also reports an error; a real death
                    # remains a death, while recording/export qualification may fail.
                    entry['dossier'] = str(export_death(run, args.death_issue))
                    entry['assessment'] = 'unassessed; owner replay and agent brainstorming pending'
                    workflow.write(output / 'collection.json', plan)
                    print(f"Natural death: {entry['dossier']}")
                    print('Next: ./replay_next_death.py; full death analysis remains pending.')
                    if code or result.get('error'):
                        raise ValueError(f'Operational failure after death export; retained evidence: {run}')
                    if index < len(seeds):
                        print('Continuing with the next fresh character.', flush=True)
                    continue
                if result['outcome'] == 'wall_timeout' and code in (0, 1) and not result.get('error'):
                    print(f'No early death within {args.timeout}s; evidence retained: {run}', flush=True)
                    if index < len(seeds):
                        print('Trying the next seed with the same time and turn limits.', flush=True)
                    continue
                if code or result.get('error') or result['outcome'] not in ('turn_cap', 'completion'):
                    raise ValueError(f'Operational failure; retained evidence: {run}')
        deaths = plan['counts'].get('death', 0)
        plan['status'] = 'completed_with_deaths' if deaths else 'limits_reached_without_death'
        workflow.write(output / 'collection.json', plan)
        print(f'Batch complete: {len(plan["runs"])} games; {deaths} natural deaths registered.', flush=True)
        for entry in plan['runs']:
            if entry.get('dossier'):
                print(f"Death: seed {entry['seed']} — {entry['dossier']}", flush=True)
        print('Reports index: ' + str(reports.collection_summary(output, plan)), flush=True)
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        plan.update(status='failed', error=str(exc))
        plan['counts'] = dict(Counter(e['outcome'] for e in plan['runs']))
        workflow.write(output / 'collection.json', plan)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--birth', choices=('random', 'fixed'), default='random', help='new characters: random race/class (default), or fixed Human Warrior')
    p.add_argument('--munchkin', action='store_true', help='start the existing native munchkin mode; recorded in configuration (default off)')
    p.add_argument('--games', type=int, help='fresh characters (default3); deaths and time/turn limits continue, operational errors stop')
    p.add_argument('--seed', type=int, help='first uint32 seed (default random); subsequent seeds are consecutive')
    p.add_argument('--seeds', nargs='+', type=int, help='explicit prospective seed list instead of --games/--seed')
    p.add_argument('--turns', type=int, default=200000, help='absolute engine-turn cap per new game (default200000)')
    p.add_argument('--timeout', type=int, default=120, help='wall-time limit in seconds per character (default120); build/lock wait separate')
    p.add_argument('--stall-timeout', type=int, default=30)
    p.add_argument('--ref', default='HEAD', help='committed native source; pinned before collection')
    p.add_argument('--build', type=Path, help='existing compatible recording build matching --ref; otherwise cached build prepared')
    approval = p.add_mutually_exclusive_group()
    approval.add_argument('--yes', action='store_true', help='accept a required build/update without prompting')
    approval.add_argument('--no-build', action='store_true', help='use an existing matching build only; fail if one is missing')
    action = p.add_mutually_exclusive_group()
    action.add_argument('--check-build', action='store_true', help='show requested/actual version and cache status, then exit without builds or games')
    action.add_argument('--commands', type=Path, metavar='COLLECTION', help='print report/watch/play paths for an existing collection; no builds or games')
    action.add_argument('--reports', type=Path, metavar='COLLECTION', help='create short/native character reports for existing runs; no replay from birth')
    p.add_argument('--output', type=Path, help='new directory below primary-checkout artifacts; default unique timestamp')
    p.add_argument('--death-issue', default=DEFAULT_ISSUE, help='discussion/work issue for any exported death')
    args = p.parse_args()
    if (args.games is not None and not 1 <= args.games <= 1000) or not 1 <= args.turns <= 2147483647 or min(args.timeout, args.stall_timeout) < 1 or (args.seed is not None and not 0 <= args.seed <= 0xffffffff):
        p.error('Use1..1000 games, uint32 seed, positive timeouts and1..2147483647 turns')
    try:
        if args.commands:
            show_collection_commands(args.commands)
            return 0
        if args.reports:
            print('Preparing reports from saved character states; waiting for validation lock...', flush=True)
            with workflow.locked(Path('/tmp/angband-validation.lock')):
                show_collection_commands(args.reports, make_reports=True)
            return 0
        seeds = seeds_for(args)
        if len(seeds) > 1000:
            raise ValueError('Maximum1000 prospective seeds per invocation')
        commit = measurement.git('rev-parse', '--verify', '--end-of-options', args.ref + '^{commit}')
        choice = choose_build(args, commit)
        announce_build(choice, commit)
        if args.check_build:
            return 0 if choice.reuse else 1
        args._build_approved = approve_build(args, choice)
        if not choice.reuse and not args._build_approved:
            print('Cancelled; no build or games started.', flush=True)
            return 0
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        output = (args.output or workflow.artifacts() / 'collections' / stamp).resolve()
        if not output.is_relative_to(workflow.primary_root() / 'artifacts'):
            raise ValueError('Full run output must stay under the primary checkout artifacts directory')
        output.mkdir(parents=True, exist_ok=False)
        print(f'Pinned source: {commit}\nProspective seeds: {seeds}\nEvidence: {output}', flush=True)
        return collect(args, output, seeds, commit)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
