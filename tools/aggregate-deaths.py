#!/usr/bin/env python3
"""Aggregate curated death records without counting replays as independent lives."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def encounter_family(record, assessment):
    # Different build/name save bytes can still be a qualified reference replay.
    if assessment.get('encounter_family_qualification', {}).get('status') == 'verified':
        return assessment.get('encounter_family') or record['encounter_family']
    return record['encounter_family']


def aggregate(records_root):
    records = []
    causes = defaultdict(set)
    actions = {}
    for p in sorted(records_root.glob('*/record.json')):
        r = json.loads(p.read_text())
        if r['schema'] != 'better-borg-c/death-record@1':
            raise ValueError(f'Unknown record schema: {p}')
        a = json.loads(p.with_name('assessment.json').read_text())
        records.append((p, r, a))
        causes[r['raw_cause']].add(encounter_family(r, a))
        for action in a['actions']:
            key = (action['issue'], action.get('key', action['summary']))
            entry = actions.setdefault(key, {'issue': action['issue'], 'key': action.get('key', action['summary']), 'summary': action['summary'], 'cases': [], 'status': action['status']})
            entry['cases'].append(r['id'])
    attempts = {x['result_sha256']: x for _, r, _ in records for x in r['attempts'] if x['outcome'] == 'death'}
    summary = {'schema': 'better-borg-c/death-index@1', 'cases': len(records),
               'distinct_starting_conditions': len({encounter_family(r, a) for _, r, a in records}),
               'death_process_attempts': len(attempts),
               'versions': dict(Counter(x['source_commit'] for x in attempts.values())),
               'causes_by_distinct_start': {k: len(v) for k, v in sorted(causes.items())},
               'actions': list(actions.values()),
               'limit': 'Selected death cases, not a mortality-rate cohort. Repeats/reference variants/windows are not new independent starting conditions.'}
    text = '# Native death records\n\nBugs always take priority. Each natural death gets a curated dossier with its actual source/build, logs, evaluation, diagnosis and linked actions. Full runs/saves/builds stay outside Git. Replays append to the case; later fixes never overwrite its identity.\n\n'
    text += 'To comment, open **Discuss** beside the case below. The linked GitHub investigation is the durable feedback thread; suggestions are checked against evidence and linked to actions. See [the feedback process](FEEDBACK.md). Chat feedback is copied there before it is considered tracked.\n\n'
    text += f"Dossiers: {summary['cases']}; distinct starting conditions: {summary['distinct_starting_conditions']}; recorded death process attempts: {summary['death_process_attempts']} (including repeats/reference variants). This registry is not a survival-rate estimate.\n\n"
    text += '| Case | Discussion | Actual source | Seed | Raw cause | Death turn | Diagnosis |\n| --- | --- | --- | --- | --- | --- | --- |\n'
    for p, r, a in records:
        text += f"| [{r['id']}]({p.parent.name}/report.md) | [Discuss]({r['investigation']}) | `{r['identity']['source'][:12]}` | {r['identity']['seed']} | {r['raw_cause']} | {r['identity']['turn']} | {a['classification']} |\n"
    text += '\n## Aggregated actions\n\n'
    for action in summary['actions']:
        text += f"- [{action['summary']}]({action['issue']}) — {action['status']}; cases {', '.join(action['cases'])}.\n"
    text += '\nRecurring mechanisms are grouped by canonical issue, not by number of replays. Investigations are hypotheses until native causal proof; original-C bugs route to neo-angband-tracker before source fix and consumer carry.\n\nCreate records with tools/record-death.py, curate assessment.json/report.md, then run tools/aggregate-deaths.py. Every report pins its actual build even after main changes.\n'
    return summary, text


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT / 'docs/deaths')
    args = p.parse_args()
    summary, text = aggregate(args.root)
    (args.root / 'index.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    (args.root / 'README.md').write_text(text)
