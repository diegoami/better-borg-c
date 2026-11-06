#!/usr/bin/env python3
"""Run every member of the frozen small cohort, retaining failures in totals.

Invoke under flock /tmp/angband-validation.lock. Generated output stays outside
Git. Baseline repetitions demonstrate reproducibility, not independent samples.
"""
import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('measurement', ROOT / 'tools/measure-native.py')
measurement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--phase', choices=('baseline', 'fixed'), required=True)
    parser.add_argument('--cohort', type=Path, default=ROOT / 'docs/measurement/cohort-v1.json')
    args = parser.parse_args()
    config = json.loads(args.cohort.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    repetitions = config[args.phase + '_repetitions_per_seed']
    report = {'cohort': config, 'cohort_sha256': measurement.sha(args.cohort), 'phase': args.phase,
              'runs': [], 'counts': {}, 'repeats_identical': {}}
    for seed in config['seeds']:
        traces = []
        for repeat in range(1, repetitions + 1):
            out = args.output / f'seed-{seed}-repeat-{repeat}'
            options = SimpleNamespace(build=args.build, output=out, seed=seed,
                                      cap=config['engine_turn_cap'], timeout=config['wall_limit_seconds'],
                                      stall_timeout=config['no_turn_progress_seconds'], no_saves=False, load=None)
            try:
                measurement.run(options)
            except Exception as exc:
                out.mkdir(parents=True, exist_ok=True)
                if not (out / 'result.json').exists():
                    measurement.write(out / 'result.json', {'outcome': 'harness_failure', 'error': str(exc), 'seed': seed})
            result = json.loads((out / 'result.json').read_text())
            outcome = result['outcome']
            report['counts'][outcome] = report['counts'].get(outcome, 0) + 1
            report['runs'].append({'directory': str(out), 'seed': seed, 'repeat': repeat,
                                   'outcome': outcome, 'cause': result.get('cause'),
                                   'wall_seconds': result.get('wall_seconds'),
                                   'final': result.get('states', [None])[-1] if result.get('states') else None,
                                   'result_sha256': measurement.sha(out / 'result.json')})
            traces.append(measurement.sha(out / 'trace.txt') if (out / 'trace.txt').exists() else None)
            measurement.write(args.output / 'cohort-result.json', report)
        if repetitions > 1:
            report['repeats_identical'][str(seed)] = traces[0] is not None and len(set(traces)) == 1
    measurement.write(args.output / 'cohort-result.json', report)
    print(json.dumps(report['counts']), flush=True)
    if any(k not in ('death', 'completion', 'turn_cap') for k in report['counts']) or not all(report['repeats_identical'].values()):
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
