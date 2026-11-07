"""Qualify a native inventory overlay for an immutable older recording."""
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


workflow = module('inventory_workflow', 'death-workflow.py')


def cache_base(original, replay, include_spells=False):
    helper = ROOT / 'tools/native-inventory.h'
    identity = hashlib.sha256((replay.recordings.sha(original / 'recording.json') +
        replay.recordings.sha(helper) + 'inventory-observer@1').encode()).hexdigest()
    if include_spells:
        identity = hashlib.sha256((identity + replay.recordings.sha(ROOT / 'tools/native-spells.h') + 'spells@1').encode()).hexdigest()
    return workflow.artifacts() / 'inventory' / identity


def cached(original, replay, include_spells=False):
    verified = cache_base(original, replay, include_spells) / 'qualified.json'
    if not verified.exists():
        return None
    receipt = workflow.read(verified)
    output = Path(receipt['output'])
    if (receipt['original_manifest_sha256'] != replay.recordings.sha(original / 'recording.json')
            or receipt['frames_sha256'] != replay.recordings.sha(output / 'frames.jsonl')
            or receipt['verification_sha256'] != replay.recordings.sha(output / 'verification.json')
            or not workflow.read(output / 'verification.json')['verified']):
        raise ValueError('Cached native inventory overlay changed; preserve it and investigate')
    return output


def prepare(original, replay, timeout, include_spells=False):
    record = replay.recordings.validate(original)
    helper = ROOT / 'tools/native-inventory.h'
    base = cache_base(original, replay, include_spells)
    with workflow.locked(base.with_suffix('.lock')):
        existing = cached(original, replay, include_spells)
        if existing is not None:
            return existing
        verified = base / 'qualified.json'
        # Rebuild the ACTUAL historical source with its frozen recording overlay.
        # Only the player-visible inventory observer is added; original streams,
        # state fingerprints/RNG and native saves must all still match.
        build = base / 'build'
        engine = build / 'build/game/angband'
        print('Preparing in-game inventory for this older recording...', flush=True)
        with workflow.locked(Path('/tmp/angband-validation.lock')):
            if not (build / 'complete.json').exists():
                source = build / 'source'
                source.mkdir(parents=True, exist_ok=False)
                archive = build / 'historical-source.tar'
                subprocess.run(['git', 'archive', '--format=tar', '-o', str(archive), record['build']['source_commit']],
                               cwd=ROOT, check=True)
                with tarfile.open(archive) as stream:
                    stream.extractall(source, filter='data')
                shutil.copytree(original / 'instrumentation', source, dirs_exist_ok=True)
                target = source / 'src/native-replay.c'
                text = target.read_text()
                start = 'void record_frame(const char *phase, long decisions)'
                if text.count(start) != 1:
                    raise ValueError('Historical recorder does not match the qualified extension site')
                if '#include "native-inventory.h"' not in text:
                    end = '    previous_details = detail_hash;\n    fprintf(frames, "}\\n");'
                    if text.count(end) != 1:
                        raise ValueError('Historical recorder inventory extension site differs')
                    text = text.replace(start, '#include "native-inventory.h"\n\n' + start).replace(
                        end, '    previous_details = detail_hash;\n    replay_inventory(full);\n    fprintf(frames, "}\\n");')
                    shutil.copy2(helper, source / 'src/native-inventory.h')
                if include_spells:
                    if '#include "native-spells.h"' in text or text.count('    replay_inventory(full);') != 1:
                        raise ValueError('Historical recorder spell extension site differs')
                    text = text.replace('#include "native-inventory.h"', '#include "native-inventory.h"\n#include "native-spells.h"').replace(
                        '    replay_inventory(full);', '    replay_inventory(full);\n    replay_spells(full);')
                    shutil.copy2(ROOT / 'tools/native-spells.h', source / 'src/native-spells.h')
                target.write_text(text)
                env = os.environ.copy()
                env.update(LC_ALL='C.UTF-8', LANG='C.UTF-8', GIT_CEILING_DIRECTORIES=str(source))
                for label, command in [
                    ('configure', ['cmake', '-S', str(source), '-B', str(build / 'build'),
                        '-DSUPPORT_BORG=ON', '-DSUPPORT_TEST_FRONTEND=ON', '-DSUPPORT_X11_FRONTEND=ON', '-DCMAKE_BUILD_TYPE=Debug']),
                    ('build', ['cmake', '--build', str(build / 'build'), '--target', 'OurExecutable', '--parallel', '2'])]:
                    print(label, build, flush=True)
                    with (build / (label + '.log')).open('w') as log:
                        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
                workflow.write(build / 'complete.json', {'engine_sha256': replay.recordings.sha(engine),
                    'source_commit': record['build']['source_commit'], 'helper_sha256': replay.recordings.sha(helper)})
            if workflow.read(build / 'complete.json')['engine_sha256'] != replay.recordings.sha(engine):
                raise ValueError('Inventory observer engine changed')
        # verify() owns the native lock itself; do not recursively acquire it.
        output = base / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
        result = replay.verify(original, output, timeout, engine=engine, inventory_extension=True, spells_extension=include_spells)
        if not result['verified']:
            raise ValueError(f'Native inventory rerun diverged; evidence: {output / "verification.json"}')
        workflow.write(verified, {'output': str(output),
            'original_manifest_sha256': replay.recordings.sha(original / 'recording.json'),
            'frames_sha256': replay.recordings.sha(output / 'frames.jsonl'),
            'verification_sha256': replay.recordings.sha(output / 'verification.json'),
            'scope': 'Historical native descriptions; every original frame/state/input/action/native-save field matches, only inventory observation added'})
        return output
