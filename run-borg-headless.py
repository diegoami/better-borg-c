#!/usr/bin/env python3
"""Run a named Borg character headlessly, then publish its final native save."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('measurement', ROOT / 'tools/measure-native.py')
measurement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)
save_spec = importlib.util.spec_from_file_location('borg_saves', ROOT / 'tools/borg-saves.py')
borg_saves = importlib.util.module_from_spec(save_spec)
save_spec.loader.exec_module(borg_saves)


@contextmanager
def locked(path, blocking=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        yield


def prepared_build():
    commit = measurement.git('rev-parse', 'HEAD')
    changed = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'src', 'lib', 'CMakeLists.txt', 'scripts'], cwd=ROOT)
    if changed.returncode:
        raise ValueError('Commit runtime source changes before exporting a headless build')
    identity = hashlib.sha256()
    identity.update(inspect.getsource(measurement.prepare).encode())
    identity.update(inspect.getsource(measurement.named_play_bridge).encode())
    for name in ('native-observer.c', 'native-observer.h'):
        identity.update((ROOT / 'tools' / name).read_bytes())
    build = ROOT / 'artifacts/headless/builds' / (commit[:12] + '-' + identity.hexdigest()[:12])
    if build.exists():
        manifest = json.loads((build / 'build.json').read_text())
        if (not manifest.get('complete') or manifest.get('source_commit') != commit
                or manifest.get('binary_sha256') != measurement.sha(build / 'build/game/angband')
                or manifest.get('tools_sha256', {}).get('native-observer.c') != measurement.sha(ROOT / 'tools/native-observer.c')):
            raise ValueError(f'Incomplete or changed cached build at {build}; preserve it and investigate')
    else:
        print(f'Preparing headless build from {commit[:12]} (first run only).', flush=True)
        measurement.prepare(SimpleNamespace(output=build, ref=commit, observe=True, retry=False))
    return build


def record_natural_death(out, issue):
    """Export an unassessed case; causal investigation remains agent work."""
    with locked(ROOT / 'artifacts/headless/death-registry.lock'):
        records = ROOT / 'docs/deaths'
        numbers = [int(p.name[1:5]) for p in records.glob('D[0-9][0-9][0-9][0-9]-*')]
        case = f'D{max(numbers, default=0) + 1:04d}'
        dossier = records / (case + '-named-headless')
        subprocess.run([sys.executable, str(ROOT / 'tools/record-death.py'),
            '--run', str(out), '--output', str(dossier), '--id', case,
            '--issue', issue, '--investigation', issue], check=True)
        subprocess.run([sys.executable, str(ROOT / 'tools/aggregate-deaths.py'), '--root', str(records)], check=True)
        print(f'Natural death dossier: {dossier} (unassessed; replay/diagnosis pending).')
        return str(dossier)


def run(args):
    saves = ROOT / 'build/native/game/lib/save'
    saves.mkdir(parents=True, exist_ok=True)
    save = saves / args.character
    try:
        with locked(saves / '.locks' / (args.character + '.lock'), blocking=False):
            if args.from_backup is not None:
                borg_saves.restore(save, args.from_backup)
            original_digest = borg_saves.backup(save)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            out = ROOT / 'artifacts/headless/runs' / stamp
            # The runner itself creates its output directory; preserve the input
            # alongside it so the final publication never races a live save.
            frozen = out.with_name(out.name + '.input.save')
            frozen.parent.mkdir(parents=True, exist_ok=True)
            if original_digest:
                shutil.copy2(save, frozen)
                if measurement.sha(frozen) != original_digest:
                    raise ValueError('Starting save changed while copying')
            user_config = ROOT / 'build/native/game/lib/user/borg.txt'
            config = user_config.read_text() if user_config.exists() else ''
            config += '\nborg_save_death = 1\n'
            print(f'Character: {args.character}; additional engine turns: {args.turns}', flush=True)
            print('Waiting for the shared native validation lock...', flush=True)
            with locked(Path('/tmp/angband-validation.lock')):
                build = prepared_build()
                options = SimpleNamespace(build=build, output=out, seed=args.seed, cap=2,
                    timeout=args.timeout, stall_timeout=args.stall_timeout, no_saves=False,
                    load=frozen if original_digest else None, play_turns=args.turns,
                    save_name=args.character, configuration=config)
                code = measurement.run(options)
            result = json.loads((out / 'result.json').read_text())
            result['named_save'] = str(save)
            result['named_runner_sha256'] = measurement.sha(Path(__file__))
            result['restored_backup_slot'] = args.from_backup
            result['run_kind'] = ('backup replay branch' if args.from_backup is not None
                                  else 'save continuation' if original_digest else 'new character')
            result['publication'] = 'not published'
            measurement.write(out / 'result.json', result)
            if code or not (out / 'final.save').is_file():
                raise ValueError(f'Run did not finish normally; original save preserved. Evidence: {out}')
            if original_digest and measurement.sha(frozen) != original_digest:
                raise ValueError(f'Frozen input changed; original save preserved. Evidence: {out}')
            if result['outcome'] == 'death':
                checkpoints = [s for s in result['states'] if s['kind'] == 'checkpoint' and not s['dead']]
                if not checkpoints or not (out / 'recent.save').is_file():
                    raise ValueError(f'Death has no living recovery checkpoint; original save preserved. Evidence: {out}')
                borg_saves.backup(save, out / 'recent.save')
                result['recovery_backup'] = {'slot': 1, 'turn': checkpoints[-1]['turn'],
                                             'source': str(out / 'recent.save')}
            elif original_digest is None:
                borg_saves.backup(save, out / 'start.save')
            borg_saves.publish(save, out / 'final.save', original_digest)
            result['publication'] = 'published'
            result['published_save_sha256'] = measurement.sha(save)
            measurement.write(out / 'result.json', result)
            print(f"{result['outcome']}: {result.get('actual_additional_turns', '?')} additional engine turns.")
            print(f'Saved: {save}\nEvidence: {out}')
            if result['outcome'] == 'death':
                record_natural_death(out, args.death_issue)
            return 0
    except BlockingIOError:
        raise ValueError(f"Character '{args.character}' is already open through a launcher")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('character', help='same save name used by start-borg.sh')
    parser.add_argument('--turns', type=int, required=True, help='additional engine turns; stop at the next command boundary')
    parser.add_argument('--seed', type=int, default=1, help='new-character RNG seed (loaded saves restore their own game RNG)')
    parser.add_argument('--timeout', type=int, default=300, help='wall limit in seconds; failures leave the original save untouched')
    parser.add_argument('--stall-timeout', type=int, default=30)
    parser.add_argument('--from-backup', type=int, choices=range(1, 6), nargs='?', const=1,
                        help='explicitly restore rolling backup slot 1 (or 1..5); preserve the current save first')
    parser.add_argument('--death-issue', default='https://github.com/diegoami/better-borg-c/issues/111',
                        help='discussion/work issue linked from any newly exported death dossier')
    args = parser.parse_args()
    if (not args.character or args.character[0] in '.-' or '/' in args.character
            or not 1 <= args.turns <= 2147483647 or not 0 <= args.seed <= 0xffffffff
            or args.timeout < 1 or args.stall_timeout < 1):
        parser.error('Use a plain character name, positive limits and a uint32 seed')
    try:
        return run(args)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
