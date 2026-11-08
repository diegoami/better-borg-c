#!/usr/bin/env python3
"""Replay the next recorded encounter not marked reviewed by the owner."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('replay_queue_helpers', ROOT / 'tools/death-workflow.py')
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def run(args):
    if args.mark_reviewed or args.mark_unreviewed:
        reviewed = bool(args.mark_reviewed)
        case = workflow.mark(args.mark_reviewed or args.mark_unreviewed, reviewed)
        print(f"{case['case']} encounter family marked {'reviewed' if reviewed else 'unreviewed'}.")
        return 0
    groups = workflow.queue()
    if args.list:
        if args.json:
            print(json.dumps(groups, indent=2))
        else:
            for group in groups:
                names = ', '.join(c['case'] for c in group['cases'])
                status = 'reviewed by owner' if group['reviewed'] else 'not reviewed by owner'
                replay = group['playable']['case'] if group['playable'] else 'no available full recording'
                print(f'{names}: {status}; replay: {replay}')
                for case in group['cases']:
                    if case['recording'] != 'recording available':
                        print(f"  {case['case']}: {case['recording']}")
        return 0
    selected = workflow.choose_case(args.case) if args.case else next(
        (g['playable'] for g in groups if not g['reviewed'] and g['playable']), None)
    if selected is None:
        print('No unreviewed encounter with an available full recording.')
        print('Use --list for legacy/missing/reviewed cases; ./produce_death.py collects new recorded games.')
        return 0
    if selected['recording'] != 'recording available':
        raise ValueError(selected['recording'])
    print(f"Replay {selected['case']}: {selected['cause']} at turn {selected['turn']}.", flush=True)
    print(f"When finished reviewing: ./replay_next_death.py --mark-reviewed {selected['case']}", flush=True)
    print('Closing the viewer does not mark a review complete.', flush=True)
    command = [sys.executable, str(ROOT / 'replay-borg.py'), selected['directory'], '--timeout', str(args.timeout)]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    command += ['--output', str(workflow.artifacts() / 'replays' / stamp)]
    for name in ('from_turn', 'view_only', 'verify_only', 'combat_log'):
        value = getattr(args, name, None)
        if value is not None and value is not False:
            command.append('--' + name.replace('_', '-'))
            if not isinstance(value, bool):
                command.append(str(value))
    return subprocess.run(command, cwd=ROOT).returncode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--list', action='store_true', help='list encounter families and owner review status')
    mode.add_argument('--case', help='explicit case, including a previously reviewed encounter')
    mode.add_argument('--mark-reviewed', metavar='CASE', help='explicitly mark the whole qualified family reviewed')
    mode.add_argument('--mark-unreviewed', metavar='CASE', help='put an encounter family back in the queue')
    p.add_argument('--json', action='store_true', help='JSON with --list')
    p.add_argument('--from-turn', type=int)
    view = p.add_mutually_exclusive_group()
    view.add_argument('--view-only', action='store_true', help='open original movie without rerun verification')
    view.add_argument('--verify-only', action='store_true', help='verify the chosen recording without opening the viewer')
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--combat-log', action='store_true', help='qualify native combat/HP/speed events using a separate historical observer')
    args = p.parse_args()
    if args.timeout < 1 or (args.from_turn is not None and args.from_turn < 0) or (args.json and not args.list):
        p.error('Use positive timeout, nonnegative turn and --json only with --list')
    try:
        return run(args)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
