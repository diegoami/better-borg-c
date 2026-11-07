#!/usr/bin/env python3
"""Visible recording backend for start-borg.sh; Borg activation stays manual."""
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
LOADED_RUNNER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


named = module('visible_named', ROOT / 'run-borg-headless.py')
recordings = module('visible_recordings', ROOT / 'tools/borg-recordings.py')
measurement = named.measurement
saves = named.borg_saves


def run(character, seed):
    save = ROOT / 'build/native/game/lib/save' / character
    lock = save.parent / '.locks' / (character + '.lock')
    # The shell already owns fd9. Keep it open in this waiting parent until
    # its sole game process exits; different names still run concurrently.
    if os.fstat(9).st_ino != lock.stat().st_ino:
        raise ValueError('Run this backend through start-borg.sh')
    fcntl.flock(9, fcntl.LOCK_EX | fcntl.LOCK_NB)
    initial_digest = saves.digest(save) if save.exists() else None
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = ROOT / 'artifacts/recordings' / stamp
    out.mkdir(parents=True)
    for directory in ('user', 'save', 'scores', 'panic', 'archive'):
        original = ROOT / 'build/native/game/lib' / directory
        if directory == 'user' and original.exists():
            shutil.copytree(original, out / directory)
        else:
            (out / directory).mkdir()
    if not (out / 'user/borg.txt').exists():
        # An empty file selects the native defaults. Make that initial input
        # explicit instead of depending on a first-run path-specific warning.
        (out / 'user/borg.txt').write_text('# Native Borg defaults; recording origin.\n')
    build = named.prepared_build(allow_build=False)
    if build is None:
        older = next(named.compatible_builds(), None)
        print('A recording-enabled build of the current local runtime is needed.', flush=True)
        if older:
            print('Available older recording build: ' + older[1]['source_commit'][:12], flush=True)
        answer = input('Build and verify the current local checkout? [y/N] ').strip().lower()
        if answer in ('y', 'yes'):
            with named.locked(Path('/tmp/angband-validation.lock')):
                subprocess.run([sys.executable, str(ROOT / 'tools/verify-native.py')], cwd=ROOT, check=True)
                build = named.prepared_build()
        elif older:
            build = older[0]
            print('Continuing with the selected older recording engine.', flush=True)
        else:
            raise ValueError('No recording-capable engine available. Accept the initial build to start a recorded game.')
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('BORG_MEASURE_', 'BORG_RECORD_', 'BORG_REPLAY_')):
            env.pop(key)
    env.update(BORG_MEASURE_SEED=str(seed), BORG_MEASURE_CAP='2147483647',
               BORG_MEASURE_DIR=str(out), BORG_MEASURE_FINAL_SAVE=str(out / 'final.save'),
               LC_ALL='C.UTF-8', LANG='C.UTF-8')
    if initial_digest:
        env['BORG_MEASURE_LOAD'] = str(save)
    command = [str(build / 'build/game/angband'), '-mx11']
    command += [f'-d{key}={out / key}' for key in ('user', 'save', 'scores', 'panic', 'archive')]
    command += ['-u' + character, '--', '-n1']
    command = recordings.begin(build, out, command, env,
        {'frontend': 'x11', 'seed': seed, 'cap': 2147483647, 'play_turns': None, 'character': character})
    origin_label = f'native save SHA256 {initial_digest}' if initial_digest else 'new character'
    print(f'Recording: {out}\nOrigin: {origin_label}\nStartup seed: {seed}\nStart Borg manually: Ctrl+Z, confirm, then z.', flush=True)
    measurement.write(out / 'input.txt', {})
    result = {'build': json.loads((build / 'build.json').read_text()),
              'runner_sha256': LOADED_RUNNER_SHA256, 'harness_commit': measurement.git('rev-parse', 'HEAD'),
              'character': character, 'seed': seed, 'turn_cap': 2147483647,
              'wall_limit_seconds': None, 'stall_limit_seconds': None, 'command': command,
              'environment': {k: env[k] for k in env if k.startswith(('BORG_MEASURE_', 'BORG_RECORD_'))},
              'cwd': str(out), 'configuration_sha256': recordings.sha(out / 'user/borg.txt') if (out / 'user/borg.txt').exists() else None,
              'input_sha256': recordings.sha(out / 'input.txt'), 'starting_save_sha256': initial_digest,
              'calendar_context': {'status': 'recorded', 'start': measurement.calendar_snapshot(),
                                   'clock_policy': 'Native clock inputs recorded without overriding the original clock'},
              'outcome': 'harness_failure', 'publication': 'not published'}
    started = time.monotonic()
    process = None
    last_autosave = None
    try:
        with (out / 'terminal.log').open('w') as log:
            process = subprocess.Popen(command, cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, start_new_session=True)
            measurement.write(out / 'process.json', {'pid': process.pid})
            while process.poll() is None:
                autosave = out / 'autosave.save'
                if autosave.exists():
                    # Native saves replace an inode atomically. Read one open
                    # descriptor so a subsequent autosave cannot race this copy.
                    with autosave.open('rb') as source:
                        data = source.read()
                    digest = hashlib.sha256(data).hexdigest()
                    if digest != last_autosave:
                        publication = out / 'autosave-publication.save'
                        publication.write_bytes(data)
                        saves.publish(save, publication, initial_digest)
                        initial_digest = saves.digest(save)
                        last_autosave = digest
                time.sleep(0.1)
        trace = (out / 'trace.txt').read_text() if (out / 'trace.txt').exists() else ''
        result['states'] = measurement.parse_states(trace)
        result['exit_code'] = process.returncode
        result['outcome'] = measurement.classify(process.returncode, result['states'])
        result['cause'] = next((s[6:] for s in trace.splitlines() if s.startswith('CAUSE ')), None)
        shutil.copyfile(out / 'events.txt', out / 'input.txt')
        result['input_sha256'] = recordings.sha(out / 'input.txt')
        maps = list((out / 'archive').glob('*.map'))
        if len(maps) == 1:
            result['native_map'] = str(maps[0].relative_to(out))
        if result['states']:
            result['actual_additional_turns'] = result['states'][-1]['turn'] - result['states'][0]['turn']
        if result['outcome'] in ('saved', 'death', 'completion') and (out / 'final.save').exists():
            if result['outcome'] == 'death':
                saves.backup(save, out / 'recent.save')
            elif not result['starting_save_sha256']:
                saves.backup(save, out / 'start.save')
            saves.publish(save, out / 'final.save', initial_digest)
            result['publication'] = 'published'
            result['published_save_sha256'] = saves.digest(save)
    except (OSError, ValueError, KeyError, EOFError, subprocess.CalledProcessError) as exc:
        result['error'] = str(exc)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if process is not None:
            result['exit_code'] = process.returncode
        result['wall_seconds'] = time.monotonic() - started
        result['calendar_context']['end'] = measurement.calendar_snapshot()
        recordings.finalize(out, result)
        result['files_sha256'] = {str(p.relative_to(out)): recordings.sha(p) for p in out.rglob('*')
                                  if p.is_file() and p.name != 'result.json'}
        measurement.write(out / 'result.json', result)
    print(f"{result['outcome']}; evidence: {out}", flush=True)
    print(f'Replay: {ROOT / "replay-borg.py"} {out}', flush=True)
    if result['outcome'] == 'death' and result['cause'] not in ('Quitting', 'Retiring'):
        named.record_natural_death(out, 'https://github.com/diegoami/better-borg-c/issues/134')
    return 0 if result['publication'] == 'published' else 1


if __name__ == '__main__':
    try:
        if len(sys.argv) not in (2, 3):
            raise ValueError('Use start-borg.sh [NAME] [--seed SEED]')
        raise SystemExit(run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) == 3 else secrets.randbits(32)))
    except (OSError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
