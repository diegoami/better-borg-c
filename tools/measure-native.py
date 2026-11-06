#!/usr/bin/env python3
"""Small native Borg measurement driver. Run heavy commands under shared flock."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = 'e473720ed88a0f0c7ca66815cef3000eb4a38bc3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f'Expected one instrumentation site: {path}: {old}')
    path.write_text(text.replace(old, new))


def prepare(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / 'source'
    source.mkdir()
    commit = git('rev-parse', args.ref + '^{commit}')
    archive = out / 'source.tar'
    subprocess.run(['git', 'archive', '--format=tar', '-o', str(archive), commit], cwd=ROOT, check=True)
    with tarfile.open(archive) as tar:
        tar.extractall(source, filter='data')
    manifest = {'source_commit': commit, 'source_archive_sha256': sha(archive),
                'harness_commit': git('rev-parse', 'HEAD'),
                'instrumented': args.observe, 'commands': [], 'complete': False,
                'tools_sha256': {p.name: sha(p) for p in (ROOT / 'tools').glob('*') if p.is_file()}}
    write(out / 'build.json', manifest)
    if args.observe:
        for name in ('native-observer.c', 'native-observer.h'):
            (source / 'src' / name).write_bytes((ROOT / 'tools' / name).read_bytes())
        for file in ('main-test.c', 'game-world.c', 'ui-game.c', 'borg/borg.c', 'borg/borg-io.c'):
            p = source / 'src' / file
            p.write_text('#include "native-observer.h"\n' + p.read_text())
        replace(source / 'src/main-test.c', 'term_data_link(0);', 'measure_init();\n\tterm_data_link(0);')
        replace(source / 'src/game-world.c', '\t\t\tturn++;', '\t\t\tturn++;\n\t\t\tmeasure_tick();')
        replace(source / 'src/ui-game.c', '\t\t\tpre_turn_refresh();', '\t\t\tmeasure_boundary();\n\t\t\tpre_turn_refresh();')
        replace(source / 'src/ui-game.c', '\t\tclose_game(true);', '\t\tmeasure_end();\n\t\tclose_game(true);')
        replace(source / 'src/borg/borg.c', 'while (!borg_think())', 'while (!(measure_decision(), borg_think()))')
        replace(source / 'src/borg/borg-io.c', '    /* Log the message */', '    measure_note(what);\n\n    /* Log the message */')
        with (source / 'CMakeLists.txt').open('a') as f:
            f.write('\ntarget_sources(OurExecutable PRIVATE src/native-observer.c)\n')
    with (source / 'CMakeLists.txt').open('a') as f:
        f.write(f'\nadd_compile_definitions(PRIVATE_USER_PATH="{out / "private-user"}")\n')
    env = os.environ.copy()
    env.update(LC_ALL='C.UTF-8', LANG='C.UTF-8')
    env.pop('FORCE_PATH', None)
    env.pop('VERBOSE', None)
    for label, command in [
        ('configure', ['cmake', '-S', str(source), '-B', str(out / 'build'),
                       '-DSUPPORT_BORG=ON', '-DSUPPORT_TEST_FRONTEND=ON',
                       '-DSUPPORT_X11_FRONTEND=ON', '-DCMAKE_BUILD_TYPE=Debug']),
        ('build', ['cmake', '--build', str(out / 'build'), '--target', 'OurExecutable', '--parallel', '2'])]:
        manifest['commands'].append(command)
        write(out / 'build.json', manifest)
        print(label, out, flush=True)
        with (out / (label + '.log')).open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    manifest.update(binary_sha256=sha(out / 'build/game/angband'), complete=True,
                    data_sha256={str(p.relative_to(source)): sha(p) for d in ('gamedata', 'customize')
                                 for p in sorted((source / 'lib' / d).rglob('*')) if p.is_file()})
    write(out / 'build.json', manifest)


INPUT = '''key space
key a
key a
key a
key enter
key enter
key enter
key enter
key C-z
key z
'''


def parse_states(text):
    states = []
    for line in text.splitlines():
        if line.startswith('STATE '):
            parts = line.split()
            states.append({'kind': parts[1], **{k: int(v) if len(v) < 20 and v.lstrip('-').isdigit() else v
                                               for k, v in (p.split('=', 1) for p in parts[2:])}})
    return states


def run(args):
    build = args.build.resolve()
    manifest = json.loads((build / 'build.json').read_text())
    if not manifest['complete'] or not manifest['instrumented']:
        raise ValueError('Require complete observer build')
    if sha(build / 'build/game/angband') != manifest['binary_sha256']:
        raise ValueError('Binary no longer matches build manifest')
    for name, digest in manifest['data_sha256'].items():
        if sha(build / 'source' / name) != digest:
            raise ValueError(f'Data changed: {name}')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for d in ('user', 'archive', 'save', 'scores', 'panic'):
        (out / d).mkdir()
    config = 'borg_cheat_death = FALSE\nborg_respawn_winners = FALSE\n'
    (out / 'user/borg.txt').write_text(config)
    (out / 'input.txt').write_text(INPUT)
    command = [str(build / 'build/game/angband'), '-mtest', '-uMeasure']
    command += [f'-d{d}={out / d}' for d in ('user', 'archive', 'save', 'scores', 'panic')]
    command += [f'-d{d}={build / "source/lib" / d}' for d in ('gamedata', 'customize')]
    env = os.environ.copy()
    env.update(BORG_MEASURE_SEED=str(args.seed), BORG_MEASURE_CAP=str(args.cap),
               BORG_MEASURE_DIR=str(out), LC_ALL='C.UTF-8', LANG='C.UTF-8')
    result = {'seed': args.seed, 'turn_cap': args.cap, 'wall_limit_seconds': args.timeout,
              'command': command, 'cwd': str(build / 'build/game'),
              'environment': {k: env[k] for k in ('BORG_MEASURE_SEED', 'BORG_MEASURE_CAP', 'BORG_MEASURE_DIR', 'LC_ALL', 'LANG')},
              'build': manifest, 'character': 'Human Warrior; default point buy; normal UI birth',
              'configuration_sha256': sha(out / 'user/borg.txt'), 'outcome': 'harness_failure'}
    write(out / 'result.json', result)
    start = time.monotonic()
    try:
        with (out / 'input.txt').open() as inp, (out / 'terminal.log').open('w') as log:
            p = subprocess.Popen(command, cwd=build / 'build/game', env=env, stdin=inp, stdout=log, stderr=subprocess.STDOUT)
            try:
                code = p.wait(timeout=args.timeout)
                result['exit_code'] = code
            except subprocess.TimeoutExpired:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
                result['outcome'] = 'wall_timeout'
                result['exit_code'] = p.returncode
        trace = (out / 'trace.txt').read_text() if (out / 'trace.txt').exists() else ''
        states = parse_states(trace)
        result['states'] = states
        if result['outcome'] != 'wall_timeout':
            if p.returncode < 0:
                result['outcome'] = 'crash'
            elif p.returncode != 0:
                result['outcome'] = 'harness_failure'
            elif states and states[-1]['kind'] in ('death', 'completion', 'turn_cap'):
                result['outcome'] = states[-1]['kind']
        result['cause'] = next((line[6:] for line in trace.splitlines() if line.startswith('CAUSE ')), None)
    except (OSError, ValueError) as exc:
        result['error'] = str(exc)
    finally:
        result['wall_seconds'] = time.monotonic() - start
        result['files_sha256'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                                  if p.is_file() and p.name != 'result.json'}
        write(out / 'result.json', result)
    print(json.dumps({k: result.get(k) for k in ('seed', 'outcome', 'wall_seconds', 'cause')}), flush=True)
    return 0 if result['outcome'] in ('death', 'completion', 'turn_cap') else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--ref', default=BASE)
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--observe', action='store_true')
    r = sub.add_parser('run')
    r.add_argument('--build', type=Path, required=True)
    r.add_argument('--output', type=Path, required=True)
    r.add_argument('--seed', type=int, required=True)
    r.add_argument('--cap', type=int, required=True)
    r.add_argument('--timeout', type=int, default=120)
    args = p.parse_args()
    if args.action == 'run' and (not 0 <= args.seed <= 0xffffffff or args.cap < 2 or args.timeout < 1):
        p.error('seed must be uint32, cap >=2 and timeout positive')
    return prepare(args) if args.action == 'prepare' else run(args)


if __name__ == '__main__':
    raise SystemExit(main())
