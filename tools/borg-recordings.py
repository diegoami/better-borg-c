"""Historical recording readers; new capture lives in angband-recorder."""
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
