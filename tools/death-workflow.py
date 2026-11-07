"""Shared local death queue and bounded collection helpers; no gameplay decisions."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def primary_root():
    common = Path(subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], cwd=ROOT, text=True).strip())
    return (ROOT / common).resolve().parent


def artifacts():
    return primary_root() / 'artifacts/death-workflow'


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def now():
    return datetime.now(timezone.utc).isoformat()


def family(record, assessment):
    if assessment.get('encounter_family_qualification', {}).get('status') == 'verified':
        return assessment.get('encounter_family') or record['encounter_family']
    return record['encounter_family']


def reviews():
    base = read(ROOT / 'docs/deaths/owner-reviews.json')['reviews']
    local = artifacts() / 'owner-reviews.json'
    if local.exists():
        base.update(read(local)['reviews'])
    return base


def cases():
    result = []
    for path in sorted((ROOT / 'docs/deaths').glob('D[0-9][0-9][0-9][0-9]-*/record.json')):
        record = read(path)
        assessment = read(path.with_name('assessment.json'))
        recording = record.get('recording')
        status = 'legacy: no full recording'
        if recording:
            manifest = Path(recording['raw_directory']) / 'recording.json'
            status = ('recording available' if manifest.is_file() and sha(manifest) == recording['manifest_sha256']
                      else 'recording missing or manifest changed; restore original bundle')
        result.append({'case': record['id'], 'directory': str(path.parent),
                       'family': family(record, assessment), 'cause': record['raw_cause'],
                       'turn': record['identity']['turn'], 'recording': status})
    return result


def queue():
    reviewed = reviews()
    grouped = {}
    for case in cases():
        group = grouped.setdefault(case['family'], {'family': case['family'], 'cases': [],
            'reviewed': reviewed.get(case['family'], {}).get('reviewed', False), 'playable': None})
        group['cases'].append(case)
        if group['playable'] is None and case['recording'] == 'recording available':
            group['playable'] = case
    return list(grouped.values())


def choose_case(case_id):
    matches = [c for c in cases() if case_id in (c['case'], Path(c['directory']).name)]
    if len(matches) != 1:
        raise ValueError('Choose an existing case ID such as D0004')
    return matches[0]


def mark(case_id, reviewed):
    case = choose_case(case_id)
    path = artifacts() / 'owner-reviews.json'
    with locked(path.with_suffix('.lock')):
        ledger = read(path) if path.exists() else {'schema': 'borg-owner-reviews@1', 'reviews': {}}
        ledger['reviews'][case['family']] = {'reviewed': reviewed, 'case': case['case'],
            'recorded_at': now(), 'reason': 'explicit owner command; independent of technical analysis status'}
        write(path, ledger)
    return case
