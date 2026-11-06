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
LOADED_RUNNER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


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
    out.mkdir(parents=True, exist_ok=args.retry)
    if args.retry:
        previous = out / ('attempt-' + str(time.time_ns()))
        previous.mkdir()
        for name in ('build.json', 'configure.log', 'build.log'):
            if (out / name).exists():
                (out / name).rename(previous / name)
    source = out / 'source'
    source.mkdir(exist_ok=args.retry)
    commit = git('rev-parse', args.ref + '^{commit}')
    archive = out / 'source.tar'
    subprocess.run(['git', 'archive', '--format=tar', '-o', str(archive), commit], cwd=ROOT, check=True)
    with tarfile.open(archive) as tar:
        tar.extractall(source, filter='data')
    manifest = {'source_commit': commit, 'source_archive_sha256': sha(archive),
                'harness_commit': git('rev-parse', 'HEAD'),
                'instrumented': args.observe, 'commands': [], 'complete': False,
                'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
                'platform': subprocess.check_output(['uname', '-sm'], text=True).strip(),
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
    (source / 'version').write_text(commit + ('-observer' if args.observe else '') )
    env.update(LC_ALL='C.UTF-8', LANG='C.UTF-8', GIT_CEILING_DIRECTORIES=str(source))
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
                    data_sha256={str(p.relative_to(source)): sha(p) for d in ('gamedata', 'customize', 'screens', 'help')
                                 for p in sorted((source / 'lib' / d).rglob('*')) if p.is_file()})
    write(out / 'build.json', manifest)


def refresh_observer(args):
    out = args.output.resolve()
    manifest = json.loads((out / 'build.json').read_text())
    binary = out / 'build/game/angband'
    if not manifest['complete'] or not manifest['instrumented'] or sha(binary) != manifest['binary_sha256']:
        raise ValueError('Require unchanged complete observer build')
    previous = out / ('attempt-' + str(time.time_ns()))
    previous.mkdir()
    (previous / 'build.json').write_bytes((out / 'build.json').read_bytes())
    (previous / 'angband').write_bytes(binary.read_bytes())
    for name in ('native-observer.c', 'native-observer.h'):
        source = out / 'source/src' / name
        data = (ROOT / 'tools' / name).read_bytes()
        if source.read_bytes() != data:
            source.write_bytes(data)
    manifest.update(complete=False, harness_commit=git('rev-parse', 'HEAD'),
                    tools_sha256={p.name: sha(p) for p in (ROOT / 'tools').glob('*') if p.is_file()})
    command = ['cmake', '--build', str(out / 'build'), '--target', 'OurExecutable', '--parallel', '2']
    manifest['commands'].append(command)
    write(out / 'build.json', manifest)
    with (previous / 'refresh.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    manifest.update(complete=True, binary_sha256=sha(binary),
                    previous_binary_sha256=sha(previous / 'angband'))
    write(out / 'build.json', manifest)


INPUT = '''key space
key a
key a
key a
key enter
key enter
key enter
key enter
key space
key C-z
key space
key space
key y
key z
'''


def parse_states(text):
    states = []
    for line in text.splitlines(keepends=True):
        # A concurrent read may stop in the middle of one native fprintf record.
        if line.endswith('\n') and line.startswith('STATE '):
            parts = line.split()
            states.append({'kind': parts[1], **{k: int(v) if len(v) < 20 and v.lstrip('-').isdigit() else v
                                               for k, v in (p.split('=', 1) for p in parts[2:])}})
    return states


def classify(code, states, interrupted=None):
    if interrupted:
        return interrupted
    if code < 0:
        return 'crash'
    if code == 0 and states and states[-1]['kind'] in ('death', 'completion', 'turn_cap'):
        return states[-1]['kind']
    return 'harness_failure'


def monitor(process, trace_path, wall_limit, stall_limit):
    start = changed = time.monotonic()
    last_turn = None
    while process.poll() is None:
        states = parse_states(trace_path.read_text()) if trace_path.exists() else []
        current_turn = states[-1]['turn'] if states else None
        now = time.monotonic()
        if current_turn != last_turn:
            last_turn, changed = current_turn, now
        reason = ('stalled' if current_turn is not None and now - changed >= stall_limit
                  else 'wall_timeout' if now - start >= wall_limit else None)
        if reason:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return reason
        time.sleep(0.1)
    return None


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
    run_input = ('key space\nkey C-z\nkey space\nkey space\nkey y\nkey z\n' if args.load else INPUT)
    (out / 'input.txt').write_text(run_input)
    command = [str(build / 'build/game/angband'), '-mtest', '-uMeasure']
    command += [f'-d{d}={out / d}' for d in ('user', 'archive', 'save', 'scores', 'panic')]
    command += [f'-d{key}={build / "source/lib" / directory}' for key, directory in (('gamedata', 'gamedata'), ('pref', 'customize'))]
    env = os.environ.copy()
    env.update(BORG_MEASURE_SEED=str(args.seed), BORG_MEASURE_CAP=str(args.cap),
               BORG_MEASURE_DIR=str(out), LC_ALL='C.UTF-8', LANG='C.UTF-8')
    for key in ('BORG_MEASURE_NO_SAVES', 'BORG_MEASURE_LOAD'):
        env.pop(key, None)
    if args.load:
        env['BORG_MEASURE_LOAD'] = str(args.load.resolve())
    if args.no_saves:
        env['BORG_MEASURE_NO_SAVES'] = '1'
    result = {'runner_sha256': LOADED_RUNNER_SHA256, 'harness_commit': git('rev-parse', 'HEAD'),
              'harness_dirty': git('status', '--porcelain', '--untracked-files=no'),
              'input_sha256': sha(out / 'input.txt'),
              'starting_save_sha256': sha(args.load) if args.load else None,
              'seed': args.seed, 'turn_cap': args.cap, 'wall_limit_seconds': args.timeout, 'stall_limit_seconds': args.stall_timeout,
              'checkpoint_saves': not args.no_saves,
              'command': command, 'cwd': str(build / 'source'),
              'environment': {k: env[k] for k in ('BORG_MEASURE_SEED', 'BORG_MEASURE_CAP', 'BORG_MEASURE_DIR', 'LC_ALL', 'LANG', 'BORG_MEASURE_NO_SAVES', 'BORG_MEASURE_LOAD') if k in env},
              'build': manifest, 'character': 'Human Warrior; default point buy; normal UI birth',
              'configuration_sha256': sha(out / 'user/borg.txt'), 'outcome': 'harness_failure'}
    write(out / 'result.json', result)
    start = time.monotonic()
    p = None
    try:
        with (out / 'input.txt').open() as inp, (out / 'terminal.log').open('w') as log:
            p = subprocess.Popen(command, cwd=build / 'source', env=env, stdin=inp, stdout=log, stderr=subprocess.STDOUT)
            interrupted = monitor(p, out / 'trace.txt', args.timeout, args.stall_timeout)
            result['exit_code'] = p.returncode
        trace = (out / 'trace.txt').read_text() if (out / 'trace.txt').exists() else ''
        states = parse_states(trace)
        result['states'] = states
        result['outcome'] = classify(p.returncode, states, interrupted)
        result['cause'] = next((line[6:] for line in trace.splitlines() if line.startswith('CAUSE ')), None)
    except (OSError, ValueError) as exc:
        result['error'] = str(exc)
    finally:
        # A trace/reader failure must not abandon an owned native process.
        if p is not None and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
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
    prep.add_argument('--retry', action='store_true', help='retain failed attempt receipts and rebuild same output')
    refresh = sub.add_parser('refresh-observer', help='preserve old binary/manifest, rebuild only observer')
    refresh.add_argument('--output', type=Path, required=True)
    r = sub.add_parser('run')
    r.add_argument('--build', type=Path, required=True)
    r.add_argument('--output', type=Path, required=True)
    r.add_argument('--seed', type=int, required=True)
    r.add_argument('--cap', type=int, required=True)
    r.add_argument('--timeout', type=int, default=120)
    r.add_argument('--stall-timeout', type=int, default=30)
    r.add_argument('--load', type=Path, help='diagnostic load; continuation reproducibility is not assumed')
    r.add_argument('--no-saves', action='store_true', help='observer non-interference control')
    args = p.parse_args()
    if args.action == 'run' and (not 0 <= args.seed <= 0xffffffff or args.cap < 2 or args.timeout < 1):
        p.error('seed must be uint32, cap >=2 and timeout positive')
    if args.action == 'refresh-observer':
        return refresh_observer(args)
    if args.action == 'prepare':
        return prepare(args)
    existed = args.output.exists()
    try:
        return run(args)
    except (OSError, ValueError, KeyError) as exc:
        if existed:
            raise
        args.output.mkdir(parents=True, exist_ok=True)
        write(args.output / 'result.json', {'outcome': 'harness_failure', 'phase': 'preflight',
              'seed': args.seed, 'turn_cap': args.cap, 'error': str(exc),
              'runner_sha256': LOADED_RUNNER_SHA256})
        print(str(exc), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
