"""Qualify combat-message/HP observations and a wide-terminal replay reader.

Builds only a separate historical export. Every original stream/frame/native
save must match before the added combat channel is offered to the viewer.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]


def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


workflow=module('combat_workflow',ROOT/'tools/death-workflow.py')
legacy=module('combat_legacy',ROOT/'tools/replay-inventory.py')


def wide_geometry(original):
    with (original/'events.txt').open() as stream:
        return any(any(int(v)>255 for v in line.split()[-2:]) for line in stream if line.strip())


def needs_wide_reader(original):
    if not wide_geometry(original):
        return False
    source=original/'instrumentation/src/native-replay.c'
    return not source.is_file() or 'width > 255' in source.read_text()


def cache(original,replay):
    identity=''.join(replay.recordings.sha(p) for p in (original/'recording.json',Path(__file__),ROOT/'tools/native-combat.h'))
    return workflow.artifacts()/'combat'/hashlib.sha256(identity.encode()).hexdigest()


def cached(original,replay):
    base=cache(original,replay);p=base/'qualified.json'
    if not p.exists():return None
    r=workflow.read(p);out=Path(r['output'])
    if (r['original_sha256']!=replay.recordings.sha(original/'recording.json')
            or r['combat_sha256']!=replay.recordings.sha(out/'combat.jsonl')
            or r['verification_sha256']!=replay.recordings.sha(out/'verification.json')
            or not workflow.read(out/'verification.json')['verified']):
        raise ValueError('Qualified combat observer changed; preserve it for investigation')
    return out


def instrument(source):
    def edit(name,old,new):
        p=source/'src'/name;t=p.read_text()
        if t.count(old)!=1:raise ValueError('Unsupported historical observation site: '+name)
        p.write_text(t.replace(old,new))
    header=source/'src/native-replay.h';text=header.read_text()
    text+='\nvoid combat_message(const char *, uint16_t);\nvoid combat_damage(int, int, int, const char *);\nvoid combat_speed(void);\n'
    header.write_text(text)
    edit('native-replay.c','    fflush(frames);\n}', '    fflush(frames);\n    combat_speed();\n}')
    recorder=source/'src/native-replay.c';text=recorder.read_text()
    # term.wid/hgt and Term_resize use ints. The old recording reader's byte
    # bound rejected real maximized windows. Retain explicit resource bounds.
    text=text.replace('width > 255 || height < 1 || height > 255',
        'width > 4096 || height < 1 || height > 4096 || (long)width * height > 1048576')
    recorder.write_text(text+'\n#include "native-combat.h"\n')
    shutil.copy2(ROOT/'tools/native-combat.h',source/'src/native-combat.h')
    p=source/'src/message.c';p.write_text('#include "native-replay.h"\n'+p.read_text())
    edit('message.c','void message_add(const char *str, uint16_t type)\n{',
         'void message_add(const char *str, uint16_t type)\n{\n    combat_message(str, type);')
    edit('player-util.c','void take_hit(struct player *p, int dam, const char *kb_str)',
         'static void observed_take_hit(struct player *p, int dam, const char *kb_str)')
    p=source/'src/player-util.c';text=p.read_text()
    if '#include "native-replay.h"' not in text:text='#include "native-replay.h"\n'+text
    text+='''\nvoid take_hit(struct player *p, int dam, const char *kb_str)
{
    int before = p->chp;
    observed_take_hit(p, dam, kb_str);
    combat_damage(dam, before, p->chp, kb_str);
}
'''
    p.write_text(text)


def prepare(original,replay,timeout):
    record=replay.recordings.validate(original)
    base=cache(original,replay)
    with workflow.locked(base.with_suffix('.lock')):
        old=cached(original,replay)
        if old is not None:return old
        overlay=original/'instrumentation'
        if not overlay.is_dir():
            r=legacy.legacy_observer(original,replay)
            if not r or r['source_commit'] != record['build']['source_commit']:
                raise ValueError('Restore matching historical observer sources before combat recovery')
            overlay=Path(r['directory'])
            for name,digest in r['files_sha256'].items():
                p=(overlay/name).resolve()
                if not p.is_relative_to(overlay.resolve()) or replay.recordings.sha(p)!=digest:
                    raise ValueError('Historical observer source changed')
        build=base/'build';engine=build/'build/game/angband'
        print(f'Preparing separate combat observer for frozen source {record["build"]["source_commit"][:12]}: {base}',flush=True)
        with workflow.locked(Path('/tmp/angband-validation.lock')):
            if not (build/'complete.json').exists():
                source=build/'source';source.mkdir(parents=True,exist_ok=False)
                archive=build/'source.tar'
                subprocess.run(['git','archive','--format=tar','-o',str(archive),record['build']['source_commit']],cwd=ROOT,check=True)
                with tarfile.open(archive) as t:t.extractall(source,filter='data')
                shutil.copytree(overlay,source,dirs_exist_ok=True);instrument(source)
                env=dict(os.environ,LC_ALL='C.UTF-8',LANG='C.UTF-8',GIT_CEILING_DIRECTORIES=str(source))
                commands=[['cmake','-S',str(source),'-B',str(build/'build'),'-DSUPPORT_BORG=ON',
                    '-DSUPPORT_TEST_FRONTEND=ON','-DSUPPORT_X11_FRONTEND=ON','-DCMAKE_BUILD_TYPE=Debug'],
                    ['cmake','--build',str(build/'build'),'--target','OurExecutable','--parallel','2']]
                for name,cmd in zip(('configure','build'),commands):
                    print(name,build,flush=True)
                    with (build/(name+'.log')).open('w') as log:
                        subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
                workflow.write(build/'complete.json',{'source':record['build']['source_commit'],
                    'engine_sha256':replay.recordings.sha(engine),
                    'files_sha256':{str(p.relative_to(source)):replay.recordings.sha(p) for p in (
                        source/'src/native-replay.c',source/'src/native-replay.h',source/'src/native-combat.h',
                        source/'src/message.c',source/'src/player-util.c')}})
            receipt=workflow.read(build/'complete.json')
            if receipt['engine_sha256']!=replay.recordings.sha(engine):raise ValueError('Frozen combat engine changed')
            for name,digest in receipt['files_sha256'].items():
                if replay.recordings.sha(build/'source'/name)!=digest:raise ValueError('Frozen combat observer changed')
        out=base/('run-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
        result=replay.verify(original,out,timeout,engine=engine)
        result.update(engine_mode='separate historical read-only combat observer and wide-input compatibility',extensions=['combat-log'])
        workflow.write(out/'verification.json',result)
        if not result['verified']:raise ValueError('Combat recovery diverged; evidence: '+str(out/'verification.json'))
        if not (out/'combat.jsonl').is_file():raise ValueError('No native combat observations produced')
        workflow.write(base/'qualified.json',{'output':str(out),'original_sha256':replay.recordings.sha(original/'recording.json'),
            'combat_sha256':replay.recordings.sha(out/'combat.jsonl'),
            'verification_sha256':replay.recordings.sha(out/'verification.json')})
        return out
