"""Frozen historical observer builds and qualified manual replay branches."""
import argparse
import ctypes
import ctypes.util
import shlex
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


replay = module('takeover_replay', ROOT / 'replay-borg.py')
workflow = module('takeover_workflow', ROOT / 'tools/death-workflow.py')
inventory = module('takeover_inventory', ROOT / 'tools/replay-inventory.py')
records = replay.recordings


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def clean_environment():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(('BORG_MEASURE_', 'BORG_RECORD_', 'BORG_REPLAY_', 'BORG_TAKEOVER_'))}


# Prefer the owner's readable size. A minimal WSLg font server may provide
# scalable misc-fixed but no Courier or 10x20 alias.
FONT_CANDIDATES = (
    '-adobe-courier-medium-r-normal--28-*-*-*-*-*-iso8859-1',
    '-urw-nimbus mono l-regular-r-normal--28-*-*-*-p-*-iso8859-1',
    '-misc-fixed-medium-r-semicondensed--28-*-*-*-c-*-iso8859-1',
    '-misc-fixed-medium-r-normal--24-*-*-*-c-*-iso8859-1',
    '12x24', '10x20', '9x15', 'fixed',
)


def x11_library():
    name = ctypes.util.find_library('X11')
    if not name:
        raise ValueError('X11 client library is unavailable; no replay started')
    lib = ctypes.CDLL(name)
    lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    lib.XOpenDisplay.restype = ctypes.c_void_p
    lib.XLoadQueryFont.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.XLoadQueryFont.restype = ctypes.c_void_p
    lib.XFreeFont.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
    lib.XGetFontPath.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    lib.XGetFontPath.restype = ctypes.POINTER(ctypes.c_char_p)
    lib.XFreeFontPath.argtypes = [ctypes.POINTER(ctypes.c_char_p)]
    lib.XSetFontPath.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int]
    lib.XSetErrorHandler.argtypes = [ctypes.c_void_p]
    lib.XSetErrorHandler.restype = ctypes.c_void_p
    lib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
    return lib


def load_font(lib, connection, name):
    font = lib.XLoadQueryFont(connection, name.encode())
    if not font:
        return False
    lib.XFreeFont(connection, font)
    return True


def registered_font(lib, connection, candidates):
    """Append an installed font path only when it supplies a requested font.

    WSLg accesses the client distro through /mnt/wslg/distro. Preserve every
    existing path and restore it after unsuccessful attempts. No installation.
    """
    count = ctypes.c_int()
    pointer = lib.XGetFontPath(connection, ctypes.byref(count))
    if not pointer:
        return None
    paths = [pointer[i] for i in range(count.value)]
    lib.XFreeFontPath(pointer)
    if not paths:
        return None
    errors = []
    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
    def handler(display, event):
        errors.append(True)
        return 0
    previous = lib.XSetErrorHandler(ctypes.cast(handler, ctypes.c_void_p))
    def set_paths(values):
        array = (ctypes.c_char_p * len(values))(*values)
        lib.XSetFontPath(connection, array, len(values))
        lib.XSync(connection, 0)
    try:
        for path in (b'/usr/share/fonts/X11/Type1', b'/mnt/wslg/distro/usr/share/fonts/X11/Type1'):
            if path in paths:
                continue
            errors.clear()
            set_paths(paths + [path])
            if not errors:
                for name in candidates:
                    if load_font(lib, connection, name):
                        return name
            set_paths(paths)
    finally:
        lib.XSetErrorHandler(previous)
    return None


def select_x11_font(env):
    display = env.get('DISPLAY')
    if not display:
        raise ValueError('X11 DISPLAY required; --prepare-only qualifies a save without a window')
    lib = x11_library()
    connection = lib.XOpenDisplay(display.encode())
    if not connection:
        raise ValueError(f'Cannot open X11 display {display}; no replay started')
    requested = env.get('BORG_PLAY_FONT') or env.get('ANGBAND_X11_FONT_0')
    preferred = (requested,) if requested else FONT_CANDIDATES[:-2]
    try:
        for name in preferred:
            if load_font(lib, connection, name):
                return name
        name = registered_font(lib, connection, preferred)
        if name:
            return name
        if not requested:
            for name in FONT_CANDIDATES[-2:]:
                if load_font(lib, connection, name):
                    return name
    finally:
        lib.XCloseDisplay(connection)
    if requested:
        raise ValueError(f'X11 font {requested!r} is unavailable on {display}; choose an installed BORG_PLAY_FONT')
    raise ValueError(f'No usable X11 font on {display}; set BORG_PLAY_FONT to an installed bitmap font')


def validate_recording(original):
    # A finalized timeout may contain a reproducible prefix even though the
    # original run did not finish normally. Keep all file-integrity checks.
    record = records.validate(original, require_complete=False)
    if record.get('status') == 'complete':
        return record
    if record.get('status') != 'incomplete' or record.get('outcome') != 'wall_timeout':
        raise ValueError('Takeover needs a complete recording or a finalized wall-timeout recording')
    result = workflow.read(original / 'result.json')
    if result.get('outcome') != 'wall_timeout' or result.get('error'):
        raise ValueError('Timed-out recording has a conflicting outcome or recording error')
    required = {'engine', 'geometry.json', 'events.txt', 'actions.txt', 'clock.txt',
                'file-inputs.txt', 'trace.txt'}
    files = record['files_sha256']
    if not required.issubset(files) or not any(n in files for n in ('frames.jsonl', 'frames.jsonl.gz')):
        raise ValueError('Timed-out recording is missing finalized replay inputs')
    return record


def parse_turn(value):
    if value == 'latest':
        return value
    try:
        turn = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('Use a positive engine turn or latest')
    if turn < 1:
        raise argparse.ArgumentTypeError('Use a positive engine turn or latest')
    return turn


def boundary(original, turn):
    first = None
    latest = None
    with replay.viewer.frame_lines(original) as frames:
        for line in frames:
            frame = json.loads(line)
            if frame['phase'] == 'command' and not frame['dead']:
                if first is None:
                    first = frame['turn']
                if turn == 'latest':
                    # Existing historical hook stops at the first command in a
                    # turn. Preserve that exact same-turn boundary semantics.
                    if latest is None or frame['turn'] > latest['turn']:
                        latest = frame
                    continue
                if frame['turn'] >= turn:
                    if turn < first:
                        raise ValueError(f'Recording starts at turn {first}; choose that turn or later')
                    return frame
    if latest is not None:
        return latest
    raise ValueError('No living player-command boundary at or after this turn in the recording')


def cache(original):
    import hashlib
    identity = ''.join(records.sha(p) for p in (original / 'recording.json',
                    Path(__file__), ROOT / 'tools/native-takeover.h'))
    return workflow.artifacts() / 'takeover/builds' / hashlib.sha256(identity.encode()).hexdigest()


def existing_build(base, original):
    if not base.exists():
        return None
    receipt = workflow.read(base / 'complete.json')
    manifest = workflow.read(base / 'build.json')
    if (receipt['original_manifest_sha256'] != records.sha(original / 'recording.json')
            or records.sha(base / 'build/game/angband') != receipt['engine_sha256']
            or manifest['binary_sha256'] != receipt['engine_sha256']
            or records.sha(base / 'source/src/native-takeover.h') != receipt['helper_sha256']
            or records.sha(base / 'source/src/native-observer.c') != receipt['observer_sha256']):
        raise ValueError('Frozen takeover build changed; preserve it for investigation')
    return base


def build(original, record, base):
    overlay = original / 'instrumentation'
    if not overlay.is_dir():
        legacy = inventory.legacy_observer(original, replay)
        if not legacy or legacy['source_commit'] != record['build']['source_commit']:
            raise ValueError('Historical observer sources unavailable; restore them before takeover')
        overlay = Path(legacy['directory'])
        for name, digest in legacy['files_sha256'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts or records.sha(overlay / name) != digest:
                raise ValueError('Archived historical observer source changed')
    with workflow.locked(Path('/tmp/angband-validation.lock')):
        if base.exists():
            return existing_build(base, original)
        source = base / 'source'
        source.mkdir(parents=True, exist_ok=False)
        archive = base / 'source.tar'
        subprocess.run(['git', 'archive', '--format=tar', '-o', str(archive), record['build']['source_commit']],
                       cwd=ROOT, check=True)
        with tarfile.open(archive) as stream:
            stream.extractall(source, filter='data')
        shutil.copytree(overlay, source, dirs_exist_ok=True)
        observer = source / 'src/native-observer.c'
        text = observer.read_text()
        site = '    record_frame("command", decisions);'
        if text.count(site) != 1 or 'takeover_boundary' in text:
            raise ValueError('Historical observer does not have the supported command boundary')
        text = text.replace('void measure_frame(void)', '#include "native-takeover.h"\n\nvoid measure_frame(void)')
        observer.write_text(text.replace(site, site + '\n    takeover_boundary();'))
        shutil.copy2(ROOT / 'tools/native-takeover.h', source / 'src/native-takeover.h')
        env = clean_environment()
        env.update(LC_ALL='C.UTF-8', LANG='C.UTF-8', GIT_CEILING_DIRECTORIES=str(source))
        commands = [
            ['cmake', '-S', str(source), '-B', str(base / 'build'), '-DSUPPORT_BORG=ON',
             '-DSUPPORT_TEST_FRONTEND=ON', '-DSUPPORT_X11_FRONTEND=ON', '-DCMAKE_BUILD_TYPE=Debug'],
            ['cmake', '--build', str(base / 'build'), '--target', 'OurExecutable', '--parallel', '2']]
        for label, command in zip(('configure', 'build'), commands):
            print(f'{label}: {base}', flush=True)
            with (base / (label + '.log')).open('w') as log:
                subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        manifest = dict(record['build'], commands=commands,
                        binary_sha256=records.sha(base / 'build/game/angband'),
                        takeover_of_binary_sha256=record['build']['binary_sha256'])
        manifest['tools_sha256'] = dict(manifest['tools_sha256'],
                    **{'native-takeover.h': records.sha(source / 'src/native-takeover.h'),
                       'native-observer.c': records.sha(observer)})
        # The historical data are restored from the original frozen bundle.
        for name, digest in manifest['data_sha256'].items():
            if records.sha(source / name) != digest:
                raise ValueError('Historical runtime data differ from the frozen recording')
        workflow.write(base / 'build.json', manifest)
        workflow.write(base / 'complete.json', {'original_manifest_sha256': records.sha(original / 'recording.json'),
            'engine_sha256': manifest['binary_sha256'], 'helper_sha256': records.sha(source / 'src/native-takeover.h'),
            'observer_sha256': records.sha(observer)})
    return base


def prefix_difference(original, output, expected):
    counts = {}
    for name in ('events.txt', 'actions.txt', 'clock.txt', 'file-inputs.txt', 'trace.txt'):
        count = 0
        with (original / name).open('rb') as source, (output / name).open('rb') as actual:
            for count, row in enumerate(actual, 1):
                if row != source.readline():
                    return {'stream': name, 'row': count}, None
        counts[name] = count
    last = None
    with replay.viewer.frame_lines(original) as source, (output / 'frames.jsonl').open() as actual:
        for line in actual:
            frame = json.loads(line)
            if line != next(source, None):
                return {'stream': 'frames', 'index': frame.get('index')}, None
            last = frame
    if last != expected:
        return {'stream': 'handoff boundary', 'expected_index': expected['index'],
                'actual_index': last.get('index') if last else None}, None
    footer = workflow.read(output / 'record-complete.json')
    if (footer['frames'] != expected['index'] or footer['inputs'] != counts['events.txt']
            or counts['events.txt'] != expected['input']):
        return {'stream': 'recording footer'}, None
    with (output / 'file-inputs.txt').open() as inputs:
        for index, present in enumerate(inputs, 1):
            if present.strip() == '1':
                name = f'file-input-{index:06d}.bin'
                if not (output / name).is_file() or records.sha(output / name) != records.sha(original / name):
                    return {'stream': 'file input', 'file': name}, None
    # The snapshot used for manual play must be the exact world in this frame.
    value = 14695981039346656037
    with (output / 'world-fingerprint.save').open('rb') as source:
        for block in iter(lambda: source.read(65536), b''):
            for byte in block:
                value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    if f'{value:016x}' != expected['world']:
        return {'stream': 'handoff native save'}, None
    return None, counts


def capture(original, record, base, output, expected, requested, timeout):
    output.mkdir(parents=True, exist_ok=False)
    for name in ('user', 'save', 'scores', 'panic', 'archive'):
        if name == 'user':
            shutil.copytree(original / 'initial-user', output / name)
        else:
            (output / name).mkdir()
    profile = record['profile']
    env = clean_environment()
    env.update(record['environment'])
    env.update(BORG_MEASURE_SEED=str(profile['seed']), BORG_MEASURE_CAP=str(profile['cap']),
               BORG_MEASURE_DIR=str(output), BORG_RECORD_DIR=str(output), BORG_REPLAY_DIR=str(original),
               BORG_REPLAY_SYS=profile['frontend'], BORG_MEASURE_FINAL_SAVE=str(output / 'final.save'),
               BORG_TAKEOVER_TURN=str(requested))
    geometry = workflow.read(original / 'geometry.json')
    env.update(BORG_REPLAY_WIDTH=str(geometry['width']), BORG_REPLAY_HEIGHT=str(geometry['height']),
               BORG_REPLAY_KEY_SIZE=str(geometry.get('key_size', 256)))
    if (original / 'timezone.tzif').exists():
        env['TZ'] = ':' + str(original / 'timezone.tzif')
    if profile.get('play_turns'):
        env['BORG_MEASURE_PLAY_TURNS'] = str(profile['play_turns'])
    if profile['frontend'] == 'x11':
        env['BORG_RECORD_VISIBLE'] = '1'
    if record['origin']:
        shutil.copy2(original / record['origin'], output / 'origin.save')
        env['BORG_MEASURE_LOAD'] = str(output / 'origin.save')
    command = [str(base / 'build/game/angband'), '-mtest']
    command += [f'-d{k}={output / k}' for k in ('user', 'save', 'scores', 'panic', 'archive')]
    command += [f'-d{k}={original / "data" / v}' for k, v in (
        ('gamedata', 'gamedata'), ('pref', 'customize'), ('screens', 'screens'), ('help', 'help'))]
    command += ['-u' + profile['character']]
    print(f'Replaying to command boundary {expected["turn"]} (frame {expected["index"]})...', flush=True)
    with workflow.locked(Path('/tmp/angband-validation.lock')), (output / 'terminal.log').open('w') as log:
        process = subprocess.Popen(command, cwd=output, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            interrupted = replay.measurement.monitor(process, output / 'trace.txt', timeout, timeout)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    receipt = {'schema': 'borg-takeover-prefix@1', 'original': str(original),
               'original_manifest_sha256': records.sha(original / 'recording.json'),
               'requested_turn': requested, 'boundary': expected,
               'original_status': record.get('status'), 'original_outcome': record.get('outcome'),
               'scope': 'Selected original prefix only; not full-run verification of a timed-out source', 'engine_sha256': records.sha(base / 'build/game/angband'),
               'exit_code': process.returncode, 'interrupted': interrupted, 'verified': False}
    try:
        if process.returncode or interrupted:
            raise ValueError('Takeover rerun failed or timed out')
        marker = workflow.read(output / 'takeover.json')
        if marker['turn'] != expected['turn'] or marker['requested_turn'] != requested:
            raise ValueError('Takeover marker does not match the requested boundary')
        difference, counts = prefix_difference(original, output, expected)
        receipt.update(first_difference=difference, prefix_rows=counts)
        if difference:
            raise ValueError(f'Takeover prefix diverged: {difference}')
        receipt.update(verified=True, save_sha256=records.sha(output / 'world-fingerprint.save'))
    except (OSError, ValueError, KeyError) as exc:
        receipt['error'] = str(exc)
        raise
    finally:
        workflow.write(output / 'verification.json', receipt)
    return receipt


def manual(original, record, base, branch, origin, font=None):
    out = branch / 'sessions' / stamp()
    out.mkdir(parents=True)
    for name in ('user', 'save', 'scores', 'panic', 'archive'):
        if name == 'user':
            shutil.copytree(original / 'initial-user', out / name)
        else:
            (out / name).mkdir()
    env = clean_environment()
    env.update(BORG_MEASURE_SEED=str(record['profile']['seed']), BORG_MEASURE_CAP='2147483647',
               BORG_MEASURE_DIR=str(out), BORG_MEASURE_FINAL_SAVE=str(out / 'final.save'),
               BORG_MEASURE_LOAD=str(origin), LC_ALL='C.UTF-8', LANG='C.UTF-8')
    env['ANGBAND_X11_FONT_0'] = font or select_x11_font(env)
    character = record['profile']['character']
    command = [str(base / 'build/game/angband'), '-mx11']
    command += [f'-d{k}={out / k}' for k in ('user', 'save', 'scores', 'panic', 'archive')]
    command += ['-u' + character, '--', '-n1']
    command = records.begin(base, out, command, env, {'frontend': 'x11', 'seed': record['profile']['seed'],
                               'cap': 2147483647, 'play_turns': None, 'character': character})
    parent = {'branch': str(branch), 'original': str(original),
              'original_manifest_sha256': records.sha(original / 'recording.json'),
              'qualification': 'manual counterfactual; excluded from independent Borg survival counts'}
    recording = workflow.read(out / 'recording.json')
    recording['counterfactual_of'] = parent
    workflow.write(out / 'recording.json', recording)
    result = {'build': workflow.read(base / 'build.json'), 'seed': record['profile']['seed'],
              'character': character, 'command': command, 'counterfactual_of': parent,
              'outcome': 'harness_failure', 'publication': 'isolated manual branch only'}
    print(f'Manual play; Borg is off. Save and exit: Ctrl+X.\nBranch recording: {out}', flush=True)
    workflow.write(branch / 'latest-session.json', {'directory': str(out)})
    started = time.monotonic()
    process = None
    try:
        with (out / 'terminal.log').open('w') as log:
            process = subprocess.Popen(command, cwd=out, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT)
            process.wait()
        if not (out / 'trace.txt').exists():
            raise ValueError(f'Game failed before loading; see {out / "terminal.log"}')
        states = replay.measurement.parse_states((out / 'trace.txt').read_text())
        result.update(states=states, exit_code=process.returncode,
                      outcome=replay.measurement.classify(process.returncode, states))
    except (OSError, ValueError, KeyboardInterrupt) as exc:
        result['error'] = str(exc)
        print('Resume without replaying: ' + shlex.join(['./play-from-replay.py', '--resume', str(branch)]), flush=True)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        result['wall_seconds'] = time.monotonic() - started
        records.finalize(out, result)
        workflow.write(out / 'result.json', result)
    print(f'{result["outcome"]}; branch save/recording retained at {out}', flush=True)
    return 0 if result['outcome'] in ('saved', 'death', 'completion') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recording', type=Path, nargs='?', help='original recording or death dossier')
    parser.add_argument('--from-turn', type=parse_turn, help='positive engine turn, or latest for the first command at the last living command turn')
    parser.add_argument('--resume', type=Path, help='resume an existing isolated manual branch')
    parser.add_argument('--prepare-only', action='store_true', help='build/qualify the boundary save without opening X11')
    parser.add_argument('--yes', action='store_true', help='accept first-use separate historical helper build')
    parser.add_argument('--no-build', action='store_true', help='require an existing matching frozen helper')
    parser.add_argument('--timeout', type=int, default=600, help='headless prefix replay wall limit in seconds')
    args = parser.parse_args()
    try:
        if args.timeout < 1 or (args.yes and args.no_build):
            raise ValueError('Use positive timeout and select only one of --yes/--no-build')
        if args.resume:
            if args.recording or args.from_turn is not None or args.prepare_only:
                raise ValueError('--resume takes only an existing branch directory')
            branch = args.resume.resolve()
            receipt = workflow.read(branch / 'branch.json')
            original = Path(receipt['original'])
        else:
            if not args.recording or args.from_turn is None:
                raise ValueError('Use RECORDING_OR_DOSSIER --from-turn N or --from-turn latest')
            original = replay.resolve_recording(args.recording)
        record = validate_recording(original)
        base = Path(receipt['build']) if args.resume else cache(original)
        print(f'Frozen source: {record["build"]["source_commit"][:12]}\nOriginal engine: {record["build"]["binary_sha256"]}', flush=True)
        if args.resume and receipt['original_manifest_sha256'] != records.sha(original / 'recording.json'):
            raise ValueError('Manual branch original recording changed')
        if record.get('status') != 'complete':
            print('Original run timed out; only the selected prefix will be verified. Original evidence stays incomplete.', flush=True)
        font = None
        if not args.prepare_only:
            font = select_x11_font(clean_environment())
            print('X11 font: ' + font, flush=True)
        if not args.resume:
            expected = boundary(original, args.from_turn)
        existing = existing_build(base, original)
        if existing is None:
            if args.resume or args.no_build:
                raise ValueError('Frozen takeover helper missing; original replay build is unchanged')
            print('A separate takeover helper must be built from the historical source. Original replay/build stays untouched.', flush=True)
            if not args.yes:
                if not sys.stdin.isatty() or input('Build this separate historical helper? [y/N] ').strip().lower() not in ('y', 'yes'):
                    print('Cancelled; original recording/build unchanged.')
                    return 1
            build(original, record, base)
        if args.resume:
            verified = workflow.read(branch / 'prefix/verification.json')
            if not verified['verified'] or verified['original_manifest_sha256'] != records.sha(original / 'recording.json'):
                raise ValueError('Manual branch has no matching verified prefix')
        else:
            case = workflow.case_for(original)
            branch = workflow.artifacts() / 'takeover/branches' / workflow.label(
                case, stamp(), f't{expected["turn"]}' if case else None)
            branch.mkdir(parents=True)
            workflow.link_case(case, 'branches', branch)
            requested = expected['turn'] if args.from_turn == 'latest' else args.from_turn
            verified = capture(original, record, base, branch / 'prefix', expected, requested, args.timeout)
            shutil.copy2(branch / 'prefix/world-fingerprint.save', branch / 'origin.save')
            receipt = {'schema': 'borg-manual-branch@1', 'original': str(original),
                       'original_manifest_sha256': records.sha(original / 'recording.json'),
                       'build': str(base), 'source_commit': record['build']['source_commit'],
                       'requested_turn': args.from_turn, 'actual_turn': expected['turn'],
                       'original_status': record.get('status'), 'original_outcome': record.get('outcome'),
                       'origin_sha256': records.sha(branch / 'origin.save'),
                       'scope': 'Verified original prefix then native save/load for manual play; Borg memory is not restored; not an independent Borg life'}
            workflow.write(branch / 'branch.json', receipt)
        print(f'Verified branch at turn {receipt["actual_turn"]}: {branch}', flush=True)
        if args.prepare_only:
            print(f'Play later: ./play-from-replay.py --resume {branch}')
            return 0
        with workflow.locked(branch / 'manual.lock'):
            origin = branch / 'origin.save'
            if (branch / 'latest-session.json').exists():
                previous = Path(workflow.read(branch / 'latest-session.json')['directory'])
                if (previous / 'result.json').exists() and workflow.read(previous / 'result.json')['outcome'] == 'death':
                    raise ValueError('This manual branch died; start another branch from the original replay')
                candidates = [previous / name for name in ('final.save', 'autosave.save', 'start.save')]
                origin = next((p for p in candidates if p.is_file()), origin)
            if origin == branch / 'origin.save' and records.sha(origin) != receipt['origin_sha256']:
                raise ValueError('Manual branch origin save changed')
            return manual(original, record, base, branch, origin, font)
    except (OSError, ValueError, KeyError, EOFError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'Takeover stopped: {exc}', file=sys.stderr)
        return 1
