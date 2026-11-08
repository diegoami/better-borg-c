#!/usr/bin/env python3
"""Verify source404's unchanged native fixture on the actual consumer cores.

Run under /tmp/angband-validation.lock after before/after native gates. The
source reproduction is imported for its variant derivation and expectations;
its pristine-build main is never run. Partial-fix objects replace only the flow
object in the actual product core. No fixture assertions or game inputs change.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BEFORE = 'e9eb2915130dac6a83b31df1f24a0cd8c2c47cef'
FIX = 'b71b32c152e272886cb46bb8f253e8c4f5130711'
EVIDENCE = '89326f5216148ab47a18585236678c391bb4e559'
PREFIX = 'docs/audit/c-reports/flowcache-404/'
SOURCE = 'src/borg/borg-flow.c'


def read(ref, path):
    return subprocess.check_output(['git', 'show', ref + ':' + path], cwd=ROOT)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-build', type=Path, required=True)
    parser.add_argument('--product-build', type=Path, default=ROOT / 'build/native')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'profile').mkdir()
    for name in ('scenario.c', 'borg.txt', 'run-cases.py', 'reproduce.py'):
        (out / name).write_bytes(read(EVIDENCE, PREFIX + name))
    (out / 'profile/borg.txt').write_bytes((out / 'borg.txt').read_bytes())
    assert (out / 'borg.txt').read_bytes() == (ROOT / 'src/borg/borg.txt').read_bytes()
    spec = importlib.util.spec_from_file_location('source_flowcache_contract', out / 'reproduce.py')
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    before_text = read(BEFORE, SOURCE).decode()
    assert before_text == read(source.BASE, SOURCE).decode(), 'layered flow module needs a fresh overlap audit'
    fixed_text = read(FIX, SOURCE).decode()
    assert (ROOT / SOURCE).read_text() == fixed_text, 'product module differs from source correction'
    texts = source.derive(before_text, fixed_text)
    builds = {'before': args.before_build.resolve(), 'after': args.product_build.resolve()}
    gates = {}
    for name, build in builds.items():
        gate = json.loads((build.parents[1] / 'artifacts/native/result.json').read_text())
        assert gate['success'] and gate['summaries']['unit']['passed'] == 965
        assert gate['summaries']['frontend']['passed'] == 5
        expected = BEFORE if name == 'before' else 'HEAD'
        subprocess.run(['git', 'diff', '--exit-code', gate['commit'], expected, '--',
                        'src', 'lib', 'CMakeLists.txt', 'cmake'], cwd=ROOT, check=True)
        gates[name] = gate
    rows, links = {}, {}
    for variant in source.VARIANTS:
        core = builds['before'] if variant == 'before' else builds['after']
        objects = sorted((core / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
        helpers = sorted((core / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
        assert len(objects) >= 150 and helpers
        flow = core / 'CMakeFiles/OurCoreLib.dir/src/borg/borg-flow.c.o'
        assert flow in objects
        if variant not in ('before', 'after'):
            # Derive the exact partial fixes, compile only that module with the
            # product's generated flags, and preserve every other core object.
            path = out / (variant + '.c')
            path.write_text(texts[variant])
            flags = {}
            for line in (core / 'CMakeFiles/OurCoreLib.dir/flags.make').read_text().splitlines():
                if line.startswith(('C_DEFINES = ', 'C_INCLUDES = ', 'C_FLAGS = ')):
                    key, value = line.split(' = ', 1)
                    flags[key] = shlex.split(value)
            replacement = out / (variant + '.o')
            command = ['cc', *flags['C_DEFINES'], *flags['C_INCLUDES'], *flags['C_FLAGS'],
                       '-I' + str(ROOT / 'src/borg'), '-c', str(path), '-o', str(replacement)]
            with (out / (variant + '-compile.log')).open('w') as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
            objects = [replacement if p == flow else p for p in objects]
        game = out / variant / 'game'
        game.mkdir(parents=True)
        (game / 'lib').symlink_to(core / 'game/lib', target_is_directory=True)
        executable = game / 'FC404Observer'
        command = ['cc', '-g', '-DALLOW_BORG', '-I' + str(ROOT / 'src'), '-I' + str(ROOT / 'src/tests'),
                   str(out / 'scenario.c'), *map(str, objects + helpers), '-lm',
                   '-Wl,--wrap=borg_danger', '-Wl,--wrap=borg_note', '-o', str(executable)]
        with (out / (variant + '-link.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        started = time.monotonic()
        subprocess.run([sys.executable, str(out / 'run-cases.py'), variant, str(executable), str(out)],
                       cwd=core / 'game', check=True)
        rows[variant] = json.loads((out / (variant + '-results.json')).read_text())
        links[variant] = {'command': command, 'binary_sha256': sha(executable),
                         'objects_sha256': {str(p): sha(p) for p in objects + helpers},
                         'case_runner_wall_seconds': time.monotonic() - started}
        failed = {case for case, row in rows[variant].items() if not row['passed']}
        assert len(rows[variant]) == 30 and failed == source.EXPECTED_FAIL[variant], (variant, failed)
        assert all(row['exit'] == 0 for row in rows[variant].values()), variant
    def behavior(row):
        keep = lambda values: {k:v for k,v in values.items() if 'calls' not in k}
        return {'state': keep(row.get('state', {})), 'outcome': keep(row.get('outcome', {})),
                'passed': row['passed']}
    for case, row in rows['before'].items():
        if row['role'] in ('control', 'limit'):
            assert behavior(row) == behavior(rows['after'][case]), case
    for mode in source.MODES:
        mixed = lambda variant: rows[variant][f'costmixed-{mode}']['state']['second_normal_calls']
        assert mixed('before') == mixed('after') == 0 and mixed('alt-wipe') > 0, mode
    for mode in ('desperate', 'digging'):
        fresh = rows['after']['control-safe']['state']['danger_calls']
        extra = rows['after'][f'safe-{mode}-spread']['state']['p2_danger_calls']
        assert extra <= fresh + 1, mode
    assert all(not row.get('state', {}).get('rng_touched', 0)
               for variant in rows.values() for row in variant.values())
    report = {'verified': True, 'before_commit': BEFORE, 'product_commit': subprocess.check_output(
                  ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_fix': FIX, 'fixture_commit': EVIDENCE,
              'fixture_sha256': sha(out / 'scenario.c'), 'normal_gates': gates,
              'variant_sources_sha256': {v: hashlib.sha256(s.encode()).hexdigest() for v,s in texts.items()},
              'failed_cases': {v: sorted(c for c,r in data.items() if not r['passed']) for v,data in rows.items()},
              'cases': rows, 'links': links,
              'scope': '150 native scenarios on actual consumer cores, not independent games; no survival claim'}
    (out / 'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('VERIFIED: product before/after, partial-fix controls and unchanged controls match the contract.',flush=True)


if __name__ == '__main__':
    main()
