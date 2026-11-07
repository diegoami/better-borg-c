#!/usr/bin/env python3
"""Collect a natural recorded death, stopping after a fixed bounded set of games."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import hashlib
import json
from pathlib import Path
import secrets
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
BUILD_TOOLS = ('measure-native.py', 'native-observer.c', 'native-observer.h', 'native-replay.c', 'native-replay.h', 'native-inventory.h')
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


def prepare_build(args, commit):
    hashes = {name: workflow.sha(ROOT / 'tools' / name) for name in BUILD_TOOLS}
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]
    build = args.build.resolve() if args.build else workflow.artifacts() / 'builds' / (commit[:12] + '-' + fingerprint)
    if not build.exists():
        if args.build:
            raise ValueError('Explicit --build does not exist; omit it to prepare a recording build')
        measurement.prepare(SimpleNamespace(output=build, ref=commit, observe=True, recording=True, retry=False))
    manifest = workflow.read(build / 'build.json')
    if (not manifest.get('complete') or not manifest.get('instrumented')
            or manifest.get('recording_schema') != 'borg-recording@1'
            or manifest.get('source_commit') != commit
            or any(manifest.get('tools_sha256', {}).get(k) != v for k, v in hashes.items())
            or workflow.sha(build / 'build/game/angband') != manifest.get('binary_sha256')):
        raise ValueError('Build must be complete, unchanged, fully recorded and match --ref and current observation tools')
    return build


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


def collect(args, output, seeds, commit):
    # Freeze all potential starts and limits BEFORE build/run results; stopping at
    # the first death is declared sampling, never a survival-rate experiment.
    plan = {'schema': 'borg-death-collection@1', 'created_at': workflow.now(),
            'source_commit': commit, 'seeds': seeds, 'turn_cap': args.turns,
            'wall_limit_per_game_seconds': args.timeout, 'stall_timeout_seconds': args.stall_timeout,
            'stop_rule': 'first natural death, operational failure, or listed seeds exhausted',
            'birth_policy': getattr(args, 'birth', 'random'),
            'character': ('Random race and class' if getattr(args, 'birth', 'random') == 'random' else 'Human Warrior') + '; default point buy; native Borg defaults; death evidence on; cheat death and winner respawn off',
            'runner_sha256': workflow.sha(Path(__file__)), 'issue': args.death_issue,
            'runs': [], 'counts': {}, 'status': 'preparing',
            'limit': 'Death collection, not an unbiased survival-rate cohort; all attempted outcomes retained.'}
    workflow.write(output / 'collection.json', plan)
    try:
        print('Waiting for the shared native validation lock...', flush=True)
        with workflow.locked(Path('/tmp/angband-validation.lock')):
            build = prepare_build(args, commit)
            plan.update(build=str(build), build_manifest_sha256=workflow.sha(build / 'build.json'), status='running')
            workflow.write(output / 'collection.json', plan)
            for index, seed in enumerate(seeds, 1):
                run = output / f'game-{index:03d}-seed-{seed}'
                entry = {'seed': seed, 'directory': str(run), 'outcome': 'harness_failure'}
                plan['runs'].append(entry)
                workflow.write(output / 'collection.json', plan)
                print(f'Game {index}/{len(seeds)}; seed {seed}; cap {args.turns}', flush=True)
                code = measurement.run(SimpleNamespace(build=build, output=run, seed=seed, cap=args.turns,
                    timeout=args.timeout, stall_timeout=args.stall_timeout, no_saves=False, load=None,
                    recording=True, random_birth=getattr(args, 'birth', 'random') == 'random', configuration='borg_save_death = 1\n'))
                result = workflow.read(run / 'result.json')
                print('Character: ' + result.get('character', 'unknown'), flush=True)
                entry.update(outcome=result['outcome'], cause=result.get('cause'), character=result.get('character'),
                             result_sha256=workflow.sha(run / 'result.json'), wall_seconds=result.get('wall_seconds'),
                             final=result.get('states', [None])[-1] if result.get('states') else None)
                plan['counts'] = dict(Counter(e['outcome'] for e in plan['runs']))
                workflow.write(output / 'collection.json', plan)
                if result['outcome'] == 'death':
                    # Export even if runner also reports an error; a real death
                    # remains a death, while recording/export qualification may fail.
                    entry['dossier'] = str(export_death(run, args.death_issue))
                    entry['assessment'] = 'unassessed; owner replay and agent brainstorming pending'
                    plan['status'] = 'natural_death_recorded'
                    workflow.write(output / 'collection.json', plan)
                    print(f"Natural death: {entry['dossier']}")
                    print('Next: ./replay_next_death.py; full death analysis remains pending.')
                    return 1 if code else 0
                if code or result['outcome'] not in ('turn_cap', 'completion'):
                    raise ValueError(f'Operational failure; retained evidence: {run}')
        plan['status'] = 'limits_reached_without_death'
        workflow.write(output / 'collection.json', plan)
        print('No natural death within the declared games/limits. No cohort enlargement performed.')
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        plan.update(status='failed', error=str(exc))
        plan['counts'] = dict(Counter(e['outcome'] for e in plan['runs']))
        workflow.write(output / 'collection.json', plan)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--birth', choices=('random', 'fixed'), default='random', help='new characters: random race/class (default), or fixed Human Warrior')
    p.add_argument('--games', type=int, help='maximum games (default3); stops after first death/failure')
    p.add_argument('--seed', type=int, help='first uint32 seed (default random); subsequent seeds are consecutive')
    p.add_argument('--seeds', nargs='+', type=int, help='explicit prospective seed list instead of --games/--seed')
    p.add_argument('--turns', type=int, default=200000, help='absolute engine-turn cap per new game (default200000)')
    p.add_argument('--timeout', type=int, default=120, help='native game wall limit per attempt; build/lock wait separate')
    p.add_argument('--stall-timeout', type=int, default=30)
    p.add_argument('--ref', default='HEAD', help='committed native source; pinned before collection')
    p.add_argument('--build', type=Path, help='existing compatible recording build matching --ref; otherwise cached build prepared')
    p.add_argument('--output', type=Path, help='new directory below primary-checkout artifacts; default unique timestamp')
    p.add_argument('--death-issue', default=DEFAULT_ISSUE, help='discussion/work issue for any exported death')
    args = p.parse_args()
    if (args.games is not None and not 1 <= args.games <= 1000) or not 1 <= args.turns <= 2147483647 or min(args.timeout, args.stall_timeout) < 1 or (args.seed is not None and not 0 <= args.seed <= 0xffffffff):
        p.error('Use1..1000 games, uint32 seed, positive timeouts and1..2147483647 turns')
    try:
        seeds = seeds_for(args)
        if len(seeds) > 1000:
            raise ValueError('Maximum1000 prospective seeds per invocation')
        commit = measurement.git('rev-parse', '--verify', '--end-of-options', args.ref + '^{commit}')
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
