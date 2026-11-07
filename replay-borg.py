#!/usr/bin/env python3
"""Verify a recorded native life, then inspect its original frames locally."""
import argparse
import fcntl
from datetime import datetime, timezone
import importlib.util
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sys
import time

ROOT = Path(__file__).resolve().parent


def tool(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


recordings = tool('replay_recordings', 'borg-recordings.py')
measurement = tool('replay_measurement', 'measure-native.py')
viewer = tool('replay_viewer', 'borg-replay-viewer.py')
LOADED_REPLAY_SHA256 = recordings.sha(Path(__file__))


def resolve_recording(path):
    path = path.resolve()
    if path.is_file() and path.name == 'record.json':
        path = path.parent
    if (path / 'recording.json').exists():
        return path
    if (path / 'record.json').exists():
        dossier = json.loads((path / 'record.json').read_text())
        reference = dossier.get('recording')
        if not reference:
            raise ValueError('This historical dossier predates full recording; it has no verified movie to open')
        bundle = Path(reference['raw_directory']).resolve()
        if not (bundle / 'recording.json').exists():
            raise ValueError(f'Restore the raw recording bundle before replay: {bundle}')
        if recordings.sha(bundle / 'recording.json') != reference['manifest_sha256']:
            raise ValueError('Dossier recording manifest hash differs')
        return bundle
    return path


def first_difference(original, rerun, inventory_extension=False):
    for name in ('events.txt', 'actions.txt', 'clock.txt', 'file-inputs.txt', 'trace.txt'):
        if name == 'trace.txt' and not (original / name).exists():
            continue
        with (original / name).open() as a, (rerun / name).open() as b:
            for index, (left, right) in enumerate(itertools.zip_longest(a, b), 1):
                if left != right:
                    return {'stream': name, 'row': index, 'expected': left, 'actual': right}
    for source in original.glob('file-input-*.bin'):
        target = rerun / source.name
        if not target.exists() or recordings.sha(source) != recordings.sha(target):
            return {'stream': 'file input content', 'file': source.name}
    with viewer.frame_lines(original) as a, viewer.frame_lines(rerun) as b:
        for index, (left, right) in enumerate(itertools.zip_longest(a, b), 1):
            if left != right:
                expected, actual = json.loads(left) if left else {}, json.loads(right) if right else {}
                if inventory_extension and left is not None and right is not None and 'inventory' not in expected:
                    actual.pop('inventory', None)
                    if expected == actual:
                        continue
                keys = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
                return {'stream': 'frames', 'row': index, 'turn': expected.get('turn'), 'fields': keys}
    for name in ('start.save', 'recent.save', 'final.save', 'world-fingerprint.save'):
        if (original / name).exists():
            if not (rerun / name).exists() or recordings.sha(original / name) != recordings.sha(rerun / name):
                return {'stream': 'native save bytes', 'file': name}
    return None


def verify(original, output, timeout, engine=None, inventory_extension=False):
    record = recordings.validate(original)
    if output.exists():
        raise ValueError('Replay output must be a new directory; original evidence is never overwritten')
    output.mkdir(parents=True)
    for directory in ('user', 'save', 'scores', 'panic', 'archive'):
        if directory == 'user':
            shutil.copytree(original / 'initial-user', output / directory)
        else:
            (output / directory).mkdir()
    profile = record['profile']
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('BORG_MEASURE_', 'BORG_RECORD_', 'BORG_REPLAY_')):
            env.pop(key)
    env.update(record['environment'])
    env.update(BORG_MEASURE_SEED=str(profile['seed']), BORG_MEASURE_CAP=str(profile['cap']),
               BORG_MEASURE_DIR=str(output), BORG_RECORD_DIR=str(output),
               BORG_REPLAY_DIR=str(original), BORG_REPLAY_SYS=profile['frontend'],
               BORG_MEASURE_FINAL_SAVE=str(output / 'final.save'))
    geometry = json.loads((original / 'geometry.json').read_text())
    env.update(BORG_REPLAY_WIDTH=str(geometry['width']), BORG_REPLAY_HEIGHT=str(geometry['height']),
               BORG_REPLAY_KEY_SIZE=str(geometry.get('key_size', 256)))
    if (original / 'timezone.tzif').exists():
        env['TZ'] = ':' + str(original / 'timezone.tzif')
    if profile.get('play_turns'):
        env['BORG_MEASURE_PLAY_TURNS'] = str(profile['play_turns'])
    if profile['frontend'] == 'x11':
        env['BORG_RECORD_VISIBLE'] = '1'
    if record['origin']:
        shutil.copy2(original / record['origin'], output / 'origin.save')
        env['BORG_MEASURE_LOAD'] = str(output / 'origin.save')
    command = [str(engine or original / 'engine'), '-mtest']
    command += [f'-d{key}={output / key}' for key in ('user', 'save', 'scores', 'panic', 'archive')]
    command += [f'-d{key}={original / "data" / name}' for key, name in (
        ('gamedata', 'gamedata'), ('pref', 'customize'), ('screens', 'screens'), ('help', 'help'))]
    command += ['-u' + profile['character']]
    interrupted = None
    process = None
    error = None
    started = time.monotonic()
    print('Waiting for the shared native validation lock...', flush=True)
    with Path('/tmp/angband-validation.lock').open('a') as guard, (output / 'terminal.log').open('w') as log:
        fcntl.flock(guard, fcntl.LOCK_EX)
        try:
            process = subprocess.Popen(command, cwd=output, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT)
            interrupted = measurement.monitor(process, output / 'trace.txt', timeout, timeout)
        except OSError as exc:
            error = str(exc)
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    missing = [name for name in ('events.txt', 'clock.txt', 'actions.txt', 'file-inputs.txt', 'frames.jsonl')
               if not (output / name).exists()]
    difference = {'stream': 'missing replay output', 'files': missing} if missing else first_difference(original, output, inventory_extension)
    complete = (output / 'record-complete.json').exists()
    result = {'schema': 'borg-replay-verification@1', 'original': str(original),
              'recording_sha256': recordings.sha(original / 'recording.json'),
              'exit_code': process.returncode if process is not None else None, 'interrupted': interrupted, 'error': error,
              'complete': complete, 'first_difference': difference,
              'verified': process is not None and process.returncode == 0 and not interrupted and complete and difference is None,
              'scope': 'All recorded input, Borg actions, clock/file inputs, native-save fingerprints, RNG/player state and logical terminal frames; no checkpoint restore or new independent life'}
    if engine is not None:
        result.update(engine_mode='historical rebuild with inventory-only observation extension',
                      engine_sha256=recordings.sha(engine), original_engine_sha256=recordings.sha(original / 'engine'))
    recordings.write(output / 'verification.json', result)
    original_result = json.loads((original / 'result.json').read_text()) if (original / 'result.json').exists() else {}
    rerun = dict(original_result)
    trace = (output / 'trace.txt').read_text() if (output / 'trace.txt').exists() else ''
    rerun.update(replay_of=str(original), replay_verified=result['verified'],
                 runner_sha256=LOADED_REPLAY_SHA256, command=command, cwd=str(output),
                 wall_seconds=time.monotonic() - started, exit_code=result['exit_code'],
                 states=measurement.parse_states(trace),
                 outcome=original_result.get('outcome') if result['verified'] else 'replay_diverged',
                 calendar_context={'status': 'recorded replay inputs',
                                   'clock_policy': 'Original native time inputs replayed; system clock not changed'})
    if (original / 'input.txt').exists():
        shutil.copy2(original / 'input.txt', output / 'input.txt')
        rerun['input_sha256'] = recordings.sha(output / 'input.txt')
    rerun['files_sha256'] = {str(p.relative_to(output)): recordings.sha(p) for p in output.rglob('*')
                              if p.is_file() and p.name != 'result.json'}
    recordings.write(output / 'result.json', rerun)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path, help='run directory printed by either launcher, or a death dossier directory')
    parser.add_argument('--from-turn', type=int, help='first engine turn to inspect (default: last 105 turns)')
    parser.add_argument('--verify-only', action='store_true', help='rerun/compare without opening the terminal viewer')
    parser.add_argument('--view-only', action='store_true', help='inspect original frames without claiming a verified rerun')
    parser.add_argument('--dump-turn', type=int, help='print one recorded frame instead of an interactive viewer')
    parser.add_argument('--output', type=Path, help='new directory for verification evidence')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    if args.timeout < 1 or (args.verify_only and args.view_only):
        parser.error('Use a positive timeout and select only one of verify-only/view-only')
    try:
        original = resolve_recording(args.recording)
        recordings.validate(original, require_complete=not args.view_only)
        verified = False
        if not args.view_only:
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            output = args.output.resolve() if args.output else ROOT / 'artifacts/replays' / stamp
            print('Rerunning the recorded start with the original engine and inputs...', flush=True)
            result = verify(original, output, args.timeout)
            print('VERIFIED' if result['verified'] else 'DIVERGED', '-', output / 'verification.json')
            if not result['verified']:
                print(json.dumps(result['first_difference'], indent=2))
                print('Original frames remain available with --view-only.')
                return 1
            verified = True
        if not args.verify_only:
            display = original
            with viewer.frame_lines(original) as rows:
                native_inventory = 'inventory' in json.loads(next(rows))
            if not native_inventory and args.dump_turn is None:
                inventory = tool('replay_inventory_extension', 'replay-inventory.py')
                display = inventory.cached(original, sys.modules[__name__]) or original
                if display == original and not args.view_only:
                    display = inventory.prepare(original, sys.modules[__name__], args.timeout)
            viewer.show(display, args.dump_turn if args.dump_turn is not None else args.from_turn,
                        verified=verified, dump=args.dump_turn is not None)
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
