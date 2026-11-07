"""Immutable local recording bundles shared by visible and headless launchers."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil

SCHEMA = 'borg-recording@1'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def parent_recording(origin_hash):
    if not origin_hash:
        return None
    root = Path(__file__).resolve().parents[1]
    matches = []
    for parent in ('artifacts/headless/runs', 'artifacts/recordings'):
        for path in (root / parent).glob('*/recording.json'):
            try:
                record = json.loads(path.read_text())
                if record.get('status') != 'complete':
                    continue
                files = record.get('files_sha256', {})
                for kind in ('final.save', 'recent.save', 'start.save', 'autosave.save'):
                    if files.get(kind) == origin_hash:
                        matches.append({'recording': str(path.parent), 'snapshot': kind,
                                        'origin_sha256': origin_hash})
                        break
            except (OSError, ValueError):
                continue
    if not matches:
        return None
    return dict(matches[-1], matching_candidates=len(matches),
                qualification='Exact saved-state hash match; this does not restore or imply prior Borg memory')


def begin(build, out, command, env, profile):
    """Freeze executable, runtime data/config and origin before the first input."""
    manifest = json.loads((build / 'build.json').read_text())
    if manifest.get('recording_schema') != SCHEMA:
        raise ValueError('This observer build predates full recording; prepare a recording build')
    if sha(build / 'build/game/angband') != manifest['binary_sha256']:
        raise ValueError('Recording engine differs from its build manifest')
    for name, digest in manifest['data_sha256'].items():
        if sha(build / 'source' / name) != digest:
            raise ValueError(f'Recording data differs from its build manifest: {name}')
    engine = out / 'engine'
    shutil.copy2(build / 'build/game/angband', engine)
    engine.chmod(0o500)
    for directory in ('gamedata', 'customize', 'screens', 'help'):
        shutil.copytree(build / 'source/lib' / directory, out / 'data' / directory)
    source_files = ['CMakeLists.txt', 'version'] + ['src/' + name for name in (
        'native-observer.c', 'native-observer.h', 'native-replay.c', 'native-replay.h',
        'main.c', 'main-test.c', 'ui-term.c', 'ui-game.c', 'game-world.c', 'savefile.c',
        'z-rand.c', 'randname.c', 'mon-make.c', 'ui-input.c', 'ui-prefs.c',
        'player-util.c', 'ui-death.c', 'borg/borg.c', 'borg/borg-io.c',
        'borg/borg-commands.c', 'borg/borg-init.c', 'borg/borg-log.c')]
    for helper in ('native-inventory.h', 'native-spells.h', 'native-takeover.h'):
        if (build / 'source/src' / helper).is_file():
            source_files.append('src/' + helper)
    for name in source_files:
        source = build / 'source' / name
        target = out / 'instrumentation' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copytree(out / 'user', out / 'initial-user')
    origin = env.get('BORG_MEASURE_LOAD')
    if origin:
        shutil.copy2(origin, out / 'origin.save')
        env['BORG_MEASURE_LOAD'] = str(out / 'origin.save')
    env['BORG_RECORD_DIR'] = str(out)
    env.pop('BORG_REPLAY_DIR', None)
    env.pop('BORG_REPLAY_SYS', None)
    env['BORG_RECORD_VISIBLE'] = '1' if profile['frontend'] == 'x11' else ''
    if not env['BORG_RECORD_VISIBLE']:
        env.pop('BORG_RECORD_VISIBLE')
    updated = [str(engine)] + command[1:]
    replacements = {'gamedata': 'gamedata', 'pref': 'customize', 'screens': 'screens', 'help': 'help'}
    for key, directory in replacements.items():
        updated = [v for v in updated if not v.startswith(f'-d{key}=')]
        updated.append(f'-d{key}={out / "data" / directory}')
    if '--' in updated:
        # Frontend suboptions must follow ALL engine options.
        at = updated.index('--')
        tail = updated[at + 1:]
        engine_options = [v for v in tail if v.startswith('-d')]
        updated = updated[:at] + engine_options + ['--'] + [v for v in tail if not v.startswith('-d')]
    tz = env.get('TZ')
    zone = Path('/etc/localtime') if not tz else Path(tz.lstrip(':'))
    if tz and not zone.is_absolute():
        zone = Path('/usr/share/zoneinfo') / tz
    if zone.is_file():
        shutil.copy2(zone, out / 'timezone.tzif')
    record = {'schema': SCHEMA, 'created_utc': datetime.now(timezone.utc).isoformat(),
              'build': manifest, 'profile': profile, 'command': updated,
              'origin': 'origin.save' if origin else None,
              'environment': {k: env[k] for k in ('LC_ALL', 'LANG', 'TZ') if k in env},
              'status': 'recording', 'input_model': 'terminal polls/events plus native clock inputs; original Borg code executes',
              'fingerprint': 'serialized native-save FNV1a64 at command/input boundaries plus player/game/Borg RNG and action stream; files protected by SHA256',
              'frames': 'logical terminal cells/colors; each world tick and command/input boundary, with explicit phase'}
    record['parent'] = parent_recording(sha(out / 'origin.save') if origin else None)
    record['immutable_sha256'] = {str(p.relative_to(out)): sha(p) for p in out.rglob('*')
        if p.is_file() and (p == engine or p.name in ('origin.save', 'timezone.tzif')
                           or any(name in p.relative_to(out).parts for name in ('data', 'initial-user', 'instrumentation')))}
    write(out / 'recording.json', record)
    return updated


def finalize(out, result):
    path = out / 'recording.json'
    if not path.exists():
        return
    record = json.loads(path.read_text())
    for name, expected in record.get('immutable_sha256', {}).items():
        if sha(out / name) != expected:
            record['status'] = 'immutable-input-changed'
            write(path, record)
            raise ValueError(f'Frozen recording input changed: {name}')
    frame_file = out / 'frames.jsonl'
    if frame_file.exists():
        compressed = out / 'frames.jsonl.gz'
        with frame_file.open('rb') as source, gzip.open(compressed, 'wb') as target:
            shutil.copyfileobj(source, target)
        # Verify lossless compression before removing this generated raw stream.
        original = sha(frame_file)
        with gzip.open(compressed, 'rb') as source:
            digest = hashlib.sha256()
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != original:
            raise ValueError('Frame compression verification failed; raw stream retained')
        frame_file.unlink()
        record['uncompressed_frames_sha256'] = original
    record['outcome'] = result.get('outcome')
    footer = out / 'record-complete.json'
    normal = result.get('outcome') in ('death', 'turn_cap', 'saved', 'completion')
    record['status'] = 'complete' if footer.exists() and normal else 'incomplete'
    if footer.exists():
        counts = json.loads(footer.read_text())
        with (out / 'events.txt').open() as events:
            if sum(1 for _ in events) != counts['inputs']:
                raise ValueError('Recording input/footer count differs')
        with gzip.open(out / 'frames.jsonl.gz', 'rt') as frames:
            total = 0
            for total, line in enumerate(frames, 1):
                if json.loads(line)['index'] != total:
                    raise ValueError('Recording frame order differs')
            if total != counts['frames']:
                raise ValueError('Recording frame/footer count differs')
    record['files_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                             if p.is_file() and p.name not in ('recording.json', 'result.json', 'verification.json')}
    write(path, record)


def validate(out, require_complete=True):
    if not (out / 'recording.json').is_file():
        raise ValueError('This run predates full recording; seed-only exact replay is unavailable. Historical evidence is unchanged.')
    record = json.loads((out / 'recording.json').read_text())
    if record.get('schema') != SCHEMA:
        raise ValueError('Unsupported/legacy recording: a seed alone cannot verify this run')
    if require_complete and record.get('status') != 'complete':
        raise ValueError('Recording is incomplete; original frames remain viewable without a verified-rerun claim')
    if 'files_sha256' not in record:
        raise ValueError('Recording has not finalized yet; close the game or wait for the run to finish')
    for name, expected in record['files_sha256'].items():
        path = (out / name).resolve()
        if not path.is_relative_to(out.resolve()) or sha(path) != expected:
            raise ValueError(f'Recording file changed: {name}')
    return record
