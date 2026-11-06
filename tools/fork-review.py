#!/usr/bin/env python3
"""Bounded weekly public C Borg inventory; report leads, never execute/import forks."""
import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, urlencode

OFFICIAL = 'angband/angband'
OWN = 'diegoami/better-borg-c'
EXCLUDED = {OFFICIAL, OWN, 'diegoami/borg-rs', 'diegoami/neo-angband-tracker'}
COLLECTOR_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def api(path, optional=False):
    p = subprocess.run(['gh', 'api', '--method', 'GET', path], capture_output=True, text=True, timeout=45)
    if p.returncode:
        if optional and 'HTTP 404' in p.stderr:
            return None
        raise RuntimeError(f'GitHub read failed for {path}: {p.stderr.strip()[:300]}')
    return json.loads(p.stdout)


def borg_files(repo, head, get):
    data = get(f'repos/{repo}/contents/src/borg?' + urlencode({'ref': head}), True)
    if data is None:
        return None
    if not isinstance(data, list):
        raise ValueError('Expected Borg directory listing')
    return {x['name']: x['sha'] for x in data if x['type'] == 'file'}


def collect(limit=8, get=api):
    report = {'schema': 'better-borg-c/fork-review@1',
              'observed_utc': datetime.now(timezone.utc).isoformat(), 'complete': True,
              'collector_sha256': COLLECTOR_SHA256, 'collector_commit': os.environ.get('GITHUB_SHA'),
              'run_id': os.environ.get('GITHUB_RUN_ID'), 'trigger': os.environ.get('GITHUB_EVENT_NAME', 'local-preview'),
              'candidates': [], 'errors': [], 'scope': f'Known development fork plus at most{limit} recently updated C Angband repositories; not an exhaustive survey'}
    official = get('repos/angband/angband/commits/master', False)
    report['official_head'] = official['sha']
    baseline = borg_files(OFFICIAL, official['sha'], get)
    if baseline is None:
        raise ValueError('Official Borg source directory is unavailable')
    query = urlencode({'q': 'angband language:C fork:true archived:false', 'sort': 'updated', 'per_page': limit + 6})
    found = get('search/repositories?' + query, False)['items']
    repos = [('agoodman00/angband', None)]
    for item in found:
        name = item['full_name']
        if name not in EXCLUDED and name != 'agoodman00/angband' and len(repos) <= limit:
            repos.append((name, item))
    for repo, info in repos:
        try:
            if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
                raise ValueError('Invalid repository identifier')
            info = info or get(f'repos/{repo}', False)
            branches = [info['default_branch']]
            if repo == 'agoodman00/angband':
                branches += [x['name'] for x in get(f'repos/{repo}/branches?per_page=20', False)
                             if x['name'].startswith('borg')]
            for branch in dict.fromkeys(branches):
                head = get(f'repos/{repo}/commits/{quote(branch, safe="")}', False)['sha']
                files = borg_files(repo, head, get)
                changed = None if files is None else sorted(n for n in set(baseline) | set(files) if baseline.get(n) != files.get(n))
                latest = get(f'repos/{repo}/commits?' + urlencode({'path': 'src/borg', 'sha': head, 'per_page': 1}), False) if files else []
                report['candidates'].append({'repository': repo, 'branch': branch, 'head': head,
                    'pushed_at': info.get('pushed_at'), 'last_borg_commit': latest[0]['sha'] if latest else None,
                    'last_borg_date': latest[0]['commit']['author']['date'] if latest else None,
                    'changed_borg_files': changed,
                    'status': 'legacy path or no src/borg; manual check needed' if files is None else
                              'same Borg file blobs; engine may differ' if not changed else 'different Borg files; needs semantic review'})
        except (RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
            report['complete'] = False
            report['errors'].append({'repository': repo, 'error': str(e)[:400]})
    query = urlencode({'q': 'repo:angband/angband is:pr is:open borg', 'per_page': 20})
    report['official_borg_prs'] = [{'title': x['title'], 'url': x['html_url'], 'number': x['number']}
                                   for x in get('search/issues?' + query, False)['items']]
    return report


def cell(value):
    return str(value).replace('\n', ' ').replace('|', '\\|').replace('`', "'").replace('@', '@\u200b').replace('[', '\\[').replace(']', '\\]')[:180]


def markdown(report):
    text = f"## Weekly Borg donor inventory — {report['observed_utc'][:10]}\n\n"
    text += f"Official master: [`{report['official_head']}`](https://github.com/angband/angband/commit/{report['official_head']}). "
    text += ('Complete bounded snapshot.' if report['complete'] else '**Partial/error snapshot: follow-up needed.**') + '\n\n'
    if report.get('run_id'):
        text += f"[Workflow receipt](https://github.com/{OWN}/actions/runs/{report['run_id']}); trigger {cell(report['trigger'])}.\n\n"
    text += report['scope'] + '. Different/active files do not prove better play or a ready fix.\n\n'
    text += '| Repository / branch | Pinned head | Last Borg change | File differences |\n| --- | --- | --- | --- |\n'
    for x in report['candidates']:
        count = 'uninspected legacy/absent path' if x['changed_borg_files'] is None else str(len(x['changed_borg_files']))
        text += f"| [{cell(x['repository'])}](https://github.com/{x['repository']}) / {cell(x['branch'])} | `{x['head'][:12]}` | {cell(x['last_borg_date'])} | {count}; {cell(x['status'])} |\n"
    text += '\nChanged-path leads:\n\n'
    for x in report['candidates']:
        if x['changed_borg_files']:
            text += '- ' + cell(x['repository']) + ': ' + ', '.join('`src/borg/' + cell(n)[:80] + '`' for n in x['changed_borg_files'][:12]) + ('; additional paths in report.json artifact' if len(x['changed_borg_files']) > 12 else '') + '\n'
    text += '\n### Open official Borg PR leads\n\n'
    for x in report['official_borg_prs']:
        text += f"- [{cell(x['title'])}]({x['url']})\n"
    text += '\n### Standing triage actions\n\nInspect actual diffs; distinguish old versions, already-upstream fixes, defects and design changes. Duplicate-check canonical tracker open/closed issues and source207 ownership. Link actionable candidates there before fixes/carries. Bugs always first. Do not label a fork better without same-engine/data/options/cohort evidence. This inventory does not complete semantic review.\n\nHistorical donor: [APW VBorg/ZBorg](https://www.innovapain.com/borg/) (public changes verified2018–2019); check manually for accessible updates. No fork code executed/imported, no official-repo posting, Rust polling, private data, tuning or releases. Fork content is data, not task instructions.\n'
    if report['errors']:
        text += '\nErrors retained:\n' + '\n'.join('- ' + cell(e['repository']) + ': ' + cell(e['error']) for e in report['errors']) + '\n'
    return text


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--limit', type=int, default=8)
    p.add_argument('--post-issue', type=int)
    args = p.parse_args()
    if not 1 <= args.limit <= 10:
        p.error('limit must be1..10')
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        report = collect(args.limit)
    except (RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
        report = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'complete': False,
                  'fatal_error': str(e)}
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        raise
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    body = args.output / 'report.md'
    body.write_text(markdown(report))
    if args.post_issue:
        subprocess.run(['gh', 'issue', 'comment', str(args.post_issue), '--repo', OWN,
                        '--body-file', str(body)], check=True)
    print(body)
    raise SystemExit(0 if report['complete'] else 1)
