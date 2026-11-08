"""Short progress reports and native character sheets from preserved run saves.

Reads the version-1 blocks written by src/savefile.c and src/save.c. Native
character formatting uses the run's frozen engine in an isolated save load,
with no Borg activation or gameplay input. It never replays from birth.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, size):
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError('Truncated native save block')
        value = self.data[self.pos:self.pos + size]
        self.pos += size
        return value

    def number(self, fmt):
        return struct.unpack('<' + fmt, self.take(struct.calcsize('<' + fmt)))[0]

    def string(self):
        end = self.data.find(b'\0', self.pos)
        if end < 0:
            raise ValueError('Unterminated native save string')
        return self.take(end - self.pos + 1)[:-1].decode('utf-8')


def saved_character(path):
    data = path.read_bytes()
    if data[:8] != b'SaveVNLA':
        raise ValueError('Unsupported native save format')
    pos, blocks = 8, {}
    while pos < len(data):
        if len(data) - pos < 28:
            raise ValueError('Truncated native save header')
        name, version, size, checksum = struct.unpack_from('<16sIII', data, pos)
        pos += 28
        payload = data[pos:pos + size]
        if len(payload) != size or sum(payload) & 0xffffffff != checksum:
            raise ValueError('Native save block checksum/size mismatch')
        name = name.rstrip(b'\0').decode('ascii')
        if name in blocks:
            raise ValueError('Duplicate native save block')
        blocks[name] = (version, payload)
        pos += size + (-size % 4)
        if pos > len(data):
            raise ValueError('Truncated native save padding')
    for name in ('player', 'misc', 'monster memory'):
        if name not in blocks or blocks[name][0] != 1:
            raise ValueError('Unsupported native character block version')
    p = Reader(blocks['player'][1])
    name, cause, history, race, shape, cls = [p.string() for _ in range(6)]
    p.take(3 + 6)  # suffix, hitdie, experience factor, age/height/weight
    stats = p.number('B')
    if not 1 <= stats <= 64:
        raise ValueError('Unsupported native stat count')
    p.take(stats * 8 + 6 + 4)  # four stat arrays, birth size/padding/gold
    p.string()  # body name
    slots = p.number('H')
    if slots > 128:
        raise ValueError('Unsupported native body size')
    for _ in range(slots):
        p.number('H'); p.string()
    p.take(4)
    gold, max_exp, exp = [p.number('I') for _ in range(3)]
    p.take(2)
    level, max_hp, hp = [p.number('h') for _ in range(3)]
    p.take(2)
    max_sp, sp = p.number('h'), p.number('h')
    p.take(2)
    max_level, max_depth = p.number('h'), p.number('h')
    p.take(2 + 2 + 2 + 2 + 1 + 1 + 2 + 2 + 2)
    timed = p.number('B'); p.take(2 * timed)
    energy, resting = p.number('I'), p.number('I')
    m = Reader(blocks['misc'][1]); m.take(12)
    dead, turn = m.number('B'), m.number('i')
    lore = Reader(blocks['monster memory'][1]); lore.take(1)
    kills = {}
    while True:
        monster = lore.string()
        if monster == 'No more monsters':
            break
        count = lore.number('H'); lore.number('H')  # this-life kills, thefts
        if monster in kills:
            raise ValueError('Duplicate native monster-memory entry')
        kills[monster] = count
    return {'name':name, 'race':race, 'class':cls, 'level':level, 'max_level':max_level,
            'max_depth':max_depth, 'gold':gold, 'experience':exp, 'max_experience':max_exp,
            'hp':hp, 'max_hp':max_hp, 'sp':sp, 'max_sp':max_sp,
            'dead':bool(dead), 'turn':turn, 'energy':energy, 'resting_turns':resting,
            'recorded_kills':sum(kills.values()), 'kills_saturated':any(n >= 32767 for n in kills.values()),
            'kills_by_race':{k:v for k,v in kills.items() if v}}


def native_dump(run, snapshot, info, target):
    """Caller owns the validation lock. Format a frozen snapshot, no new life."""
    if info['dead']:
        return None  # Do not resurrect a dead save merely to format it.
    target.mkdir(parents=True, exist_ok=False)
    for name in ('user', 'save', 'scores', 'panic', 'archive'):
        (target / name).mkdir()
    shutil.copy2(snapshot, target / 'origin.save')
    env = {k:v for k,v in os.environ.items() if not k.startswith(
        ('BORG_MEASURE_', 'BORG_RECORD_', 'BORG_REPLAY_', 'BORG_TAKEOVER_'))}
    env.update(BORG_MEASURE_SEED='1', BORG_MEASURE_CAP='2147483647',
               BORG_MEASURE_DIR=str(target), BORG_MEASURE_LOAD=str(target / 'origin.save'),
               BORG_MEASURE_NO_SAVES='1', BORG_RECORD_VISIBLE='1', LC_ALL='C.UTF-8', LANG='C.UTF-8')
    command = [str(run / 'engine'), '-mtest']
    command += [f'-d{k}={target / k}' for k in ('user','save','scores','panic','archive')]
    command += [f'-d{k}={run / "data" / v}' for k,v in (
        ('gamedata','gamedata'),('pref','customize'),('screens','screens'),('help','help'))]
    command += ['-u' + info['name']]
    # Open the standard character sheet, save it with its default safe name,
    # then stop in the UI. There is no movement, rest or Borg-start command.
    keys = 'key space\nkey C\nkey f\nkey enter\nkey C-[\nkey C-[\nquit\n'
    with (target / 'terminal.log').open('w') as log:
        process = subprocess.run(command, input=keys, text=True, cwd=target, env=env,
                                 stdout=log, stderr=subprocess.STDOUT, timeout=15)
    candidates = [p for p in (target / 'user').glob('*.txt')
                  if p.name not in ('CharOutput.txt','lore.txt','borg.txt')]
    if process.returncode or len(candidates) != 1:
        raise ValueError('Native character dump unavailable; diagnostic log retained')
    text = candidates[0].read_text()
    if 'Character Dump]' not in text or not re.search(r'\bGame\s+' + str(info['turn']) + r'\b', text):
        raise ValueError('Native character dump did not match snapshot turn')
    trace = (target / 'trace.txt').read_text()
    states = [dict(re.findall(r'(\w+)=(-?\d+)', line)) for line in trace.splitlines() if line.startswith('STATE ')]
    if not states or any(int(s['turn']) != info['turn'] or int(s['energy']) != info['energy']
                         or int(s['decisions']) != 0 for s in states):
        raise ValueError('Character formatting changed game progress')
    shutil.copy2(candidates[0], target / 'character.txt')
    return target / 'character.txt'


def create(run, result, format_character=True):
    run = run.resolve()
    report_dir = run / 'reports'
    report_dir.mkdir(exist_ok=True)
    states = result.get('states', [])
    final = states[-1] if states else {}
    report = {'schema':'borg-run-report@1', 'character':result.get('character','Unknown'),
              'outcome':result['outcome'], 'cause':result.get('cause'), 'seed':result.get('seed'),
              'source_commit':result.get('build',{}).get('source_commit'),
              'turn':final.get('turn'), 'level':final.get('level'), 'max_level':final.get('max_level'),
              'max_depth':final.get('max_depth'), 'decisions':final.get('decisions'),
              'wall_seconds':result.get('wall_seconds'), 'recorded_kills':None,
              'snapshot':None, 'native_character_dump':None}
    manifest_path = run / 'recording.json'
    files = json.loads(manifest_path.read_text()).get('files_sha256',{}) if manifest_path.exists() else {}
    snapshots = []
    for name in ('world-fingerprint.save','final.save','recent.save','start.save'):
        p = run / name
        if not p.is_file():
            continue
        try:
            if name not in files or sha(p) != files[name]:
                raise ValueError('Snapshot absent from frozen manifest or changed')
            info = saved_character(p)
            if final.get('turn') is not None and info['turn'] > final['turn']:
                raise ValueError('Snapshot is newer than recorded outcome')
            snapshots.append((info['turn'], p, info))
        except (OSError, ValueError, struct.error) as exc:
            report.setdefault('snapshot_errors',{})[name] = str(exc)
    if snapshots:
        _, snapshot, info = max(snapshots, key=lambda v:v[0])
        report.update(snapshot={'path':snapshot.name,'sha256':sha(snapshot),'turn':info['turn']},
                      recorded_kills=info['recorded_kills'], kills_saturated=info['kills_saturated'],
                      kills_by_race=info['kills_by_race'], experience=info['experience'],
                      gold=info['gold'], resting_turns=info['resting_turns'])
        if format_character and not info['dead'] and 'engine' in files:
            try:
                if sha(run / 'engine') != files['engine']:
                    raise ValueError('Frozen engine changed')
                target = report_dir / ('native-' + sha(snapshot)[:12])
                cache = target / 'character.txt'
                receipt = target / 'receipt.json'
                if cache.is_file() and receipt.exists() and json.loads(receipt.read_text()) == {
                        'snapshot_sha256':sha(snapshot),'dump_sha256':sha(cache)}:
                    dump = cache
                else:
                    if target.exists():
                        target = report_dir / (target.name + '-retry-' + str(time.time_ns()))
                    dump = native_dump(run, snapshot, info, target)
                    if dump:
                        (target / 'receipt.json').write_text(json.dumps({
                            'snapshot_sha256':sha(snapshot),'dump_sha256':sha(dump)},indent=2)+'\n')
                if dump:
                    report['native_character_dump'] = str(dump.relative_to(report_dir))
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                report['character_dump_error'] = str(exc)
    def value(key):
        v = report.get(key)
        return 'unavailable' if v is None else str(v)
    outcome = {'wall_timeout':'Alive at wall-time limit', 'turn_cap':'Alive at turn limit',
               'death':'Died', 'completion':'Completed'}.get(report['outcome'],report['outcome'])
    text = f"# {report['character']}\n\n{outcome}.\n\n| Progress | Result |\n| --- | --- |\n"
    for label, content in [('Character level / highest',value('level')+' / '+value('max_level')),
             ('Deepest dungeon level',value('max_depth')), ('Recorded monster kills',value('recorded_kills')),
             ('Experience',value('experience')),('Gold',value('gold')),('Engine turns',value('turn')),
             ('Borg decisions',value('decisions')),('Wall seconds',f"{report['wall_seconds']:.1f}" if report['wall_seconds'] is not None else 'unavailable')]:
        text += f'| {label} | {content} |\n'
    text += f"\nBuild `{value('source_commit')}`; seed `{value('seed')}`.\n"
    if report['outcome'] == 'death':
        text += f"\nCause: {report.get('cause') or 'unavailable'}.\n"
    if report['snapshot']:
        text += f"\nNative saved-character counters at turn {report['snapshot']['turn']}. "
        if report['snapshot']['turn'] != report['turn']:
            text += 'This checkpoint predates the final outcome. '
        text += 'Kills are the character\u2019s recorded this-life kills; unseen non-unique kills may not appear.\n'
    if report['native_character_dump']:
        text += f"\n[Full native Angband character dump]({report['native_character_dump']})\n"
    if report.get('character_dump_error'):
        text += '\nFull native character dump unavailable; short progress metrics are retained.\n'
    text += '\nA living limit result is not a victory or a survival-rate estimate.\n'
    (report_dir / 'summary.md').write_text(text)
    (report_dir / 'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    return report_dir / 'summary.md', report


def collection_summary(directory, plan):
    directory = directory.resolve()
    text = '# Collected games\n\n| Character report | Level | Max depth | Recorded kills | Outcome |\n| --- | --- | --- | --- | --- |\n'
    for entry in plan.get('runs', []):
        path = Path(entry['directory']) / 'reports/summary.json'
        if not path.exists():
            continue
        r = json.loads(path.read_text())
        link = os.path.relpath(path.with_suffix('.md'), directory)
        label = r['character'].replace('|', '\\|')
        value = lambda key: 'unavailable' if r.get(key) is None else str(r[key])
        text += f"| [{label}](<{link}>) | {value('level')} | {value('max_depth')} | {value('recorded_kills')} | {r['outcome']} |\n"
    text += '\nWall/turn-limit outcomes are living limited runs, not completed victories.\n'
    path = directory / 'reports.md'
    path.write_text(text)
    return path
