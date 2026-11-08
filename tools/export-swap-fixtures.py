#!/usr/bin/env python3
"""Export real CBUG-0066 native decision facts, without a copied chooser.

Run under /tmp/angband-validation.lock. The original fixture is unchanged
except its existing output-path relocation. GNU link wrappers observe one
original call each; the source C runtimes, headers and helpers are pinned.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BEFORE = 'e473720ed88a0f0c7ca66815cef3000eb4a38bc3'
AFTER = '39986cc52f3f70727ada24b6def5de98d0bd36c8'
CORRECTION = 'ebcd255ba9064fc44a35d693f42f9df3dc00bd88'
EVIDENCE = '1b67370d0dc56d9b7ef34e5356e63d21a7095545'
FIXTURE = 'docs/audit/c-reports/CBUG-0066/expanded/scenario.c'
CONFIG = 'docs/audit/c-reports/CBUG-0066/borg.txt'
FIXTURE_SHA = 'b26f955689acaf552545019189ade029e82344a0c508d9c77d5b1581015a70b6'
WEAR = 'src/borg/borg-item-wear.c'
WEAR_SHA = {BEFORE: 'a7f1427419a3f2b3c7810aa7761d9c31d13e632633ccdb6f86998c1d4ad02bd9',
            AFTER: '7f6d4eb2e5e33139f23786a2cf51031418f5d3c214a78eb1723aa203c1acb750'}
MODES = ('armour-better', 'weapon-better', 'fire-armour', 'electric-weapon',
         'both-helpful', 'armour-only', 'weapon-only', 'tie', 'no-benefit')
CONTROLS = {'armour-only', 'weapon-only', 'tie', 'no-benefit'}
LINK_WRAPS = ('borg_backup_swap', 'borg_danger', 'borg_keypress')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf8')


def write(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def run(command, log, cwd, env):
    print('Running:', ' '.join(map(str, command)), flush=True)
    with log.open('wb') as saved:
        completed = subprocess.run(command, cwd=cwd, env=env, stdout=saved,
                                   stderr=subprocess.STDOUT, timeout=900)
    if completed.returncode:
        raise RuntimeError(f'Command failed ({completed.returncode}); see {log}')


def tree_files(ref, paths):
    output = git('ls-tree', '-r', '--name-only', ref, '--', *paths).decode().splitlines()
    return {name: sha(git('show', ref + ':' + name)) for name in output}


def prepare(out, phase, ref, jobs):
    directory = out / phase
    directory.mkdir()
    source, build = directory / 'source', directory / 'build'
    source.mkdir()
    archive = directory / 'source.tar'
    subprocess.run(['git', 'archive', '--format=tar', '-o', str(archive), ref], cwd=ROOT, check=True)
    with tarfile.open(archive) as saved:
        saved.extractall(source, filter='data')
    # Build identity and isolated profile only; no runtime source edit.
    cmake = source / 'CMakeLists.txt'
    original_cmake = cmake.read_bytes()
    cmake.write_text(cmake.read_text() + '\nadd_compile_definitions(PRIVATE_USER_PATH="' +
                     str(directory / 'private-user') + '")\n')
    (source / 'version').write_text(ref)
    env = dict(os.environ, LC_ALL='C.UTF-8', LANG='C.UTF-8', GIT_CEILING_DIRECTORIES=str(source))
    env.pop('FORCE_PATH', None)
    env.pop('VERBOSE', None)
    commands = [
        ['cmake', '-S', str(source), '-B', str(build), '-DSUPPORT_BORG=ON',
         '-DSUPPORT_TEST_FRONTEND=ON', '-DSUPPORT_X11_FRONTEND=ON',
         '-DCMAKE_BUILD_TYPE=Debug', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'],
        ['cmake', '--build', str(build), '--target', 'OurExecutable', 'OurUnitTestLib',
         '--parallel', str(jobs)],
    ]
    for number, command in enumerate(commands):
        run(command, directory / f'build-{number}.log', ROOT, env)
    objects = sorted((build / 'CMakeFiles/OurCoreLib.dir').rglob('*.o'))
    helpers = sorted((build / 'CMakeFiles/OurUnitTestLib.dir').rglob('*.o'))
    if len(objects) < 150 or not helpers:
        raise RuntimeError('Incomplete pinned native core/helper objects')
    headers = {str(p.relative_to(source)): sha(p.read_bytes()) for p in sorted((source / 'src').rglob('*.h'))}
    facts = {'runtimeCommit': ref, 'runtimeSourceTree': tree_files(ref, ['src', 'lib', 'CMakeLists.txt']),
             'headersSha256': headers, 'coreObjectsSha256': {str(p.relative_to(build)): sha(p.read_bytes()) for p in objects},
             'helperObjectsSha256': {str(p.relative_to(build)): sha(p.read_bytes()) for p in helpers},
             'helperSourcesSha256': {str(p.relative_to(source)): sha(p.read_bytes()) for p in
                                     (source / 'src/tests/unit-test.c', source / 'src/tests/test-utils.c')},
             'originalCMakeSha256': sha(original_cmake), 'preparedCMakeSha256': sha(cmake.read_bytes()),
             'compileCommandsSha256': sha((build / 'compile_commands.json').read_bytes()),
             'metadataOnlyPreparation': ['CMake PRIVATE_USER_PATH', 'version build identity'],
             'source': str(source), 'build': str(build), 'fixtureWorkingDirectory': str(source), 'commands': commands}
    write(directory / 'build.json', facts)
    return source, build, objects, helpers, env, facts


def parse_observed(text, mode):
    rows = [json.loads(line[4:]) for line in text.splitlines() if line.startswith('POC ')]
    entry = [row for row in rows if row['kind'] == 'entry']
    result = [row for row in rows if row['kind'] == 'result']
    evaluated = [row for row in rows if row['kind'] == 'evaluation']
    if len(entry) != 1 or len(result) != 1:
        raise ValueError(f'{mode}: expected one real selector entry/result')
    inputs, bindings, final = entry[0]['inputs'], entry[0]['bindings'], result[0]
    expected_roles = [role for role in ('armour', 'weapon') if inputs['candidates'][role] is not None]
    if [row['role'] for row in evaluated] != expected_roles or final['evaluationCount'] != len(expected_roles):
        raise ValueError(f'{mode}: actual evaluator call order/count differs from available candidates')
    for number, row in enumerate(evaluated):
        if row['ordinal'] != number:
            raise ValueError('Unexpected native evaluator ordinal')
        if row['nativeArmourIndex'] != bindings['armourIndex'] or row['nativeWeaponIndex'] != bindings['weaponIndex']:
            raise ValueError('Actual selector reselected a backup; the claimed boundary is not equivalent')
        inputs['candidates'][row['role']]['evaluation'] = row['answer']
    trial = re.search(r'^DANGER armour=(-?\d+) weapon=(-?\d+)$', text, re.M)
    decision = re.search(r'^DECISION swapped=(\d+) command=(\d+) letter=(\d+) pack_index=(-?\d+)$', text, re.M)
    outcome = re.search(r'^OUTCOME hp_before=(\d+) hp_after=(-?\d+) hp_lost=(\d+)$', text, re.M)
    if trial is None or decision is None or outcome is None or 'finished:' not in text:
        raise ValueError(f'{mode}: original unchanged fixture did not complete')
    for role, raw in zip(('armour', 'weapon'), map(int, trial.groups())):
        candidate = inputs['candidates'][role]
        if (candidate is None and raw != -1) or (candidate is not None and candidate['evaluation']['rawDanger'] != raw):
            raise ValueError('Actual in-selector result differs from the original trial observation')
    swapped, command, letter, index = map(int, decision.groups())
    if bool(swapped) != final['swapped'] or index != final['nativeIndex']:
        raise ValueError('Observer differs from actual fixture key consumption')
    if swapped:
        if final['keys'] != [command, letter] or final['keyCount'] != 2 or command != ord('w'):
            raise ValueError('Observer changed or failed to capture the real queued command')
        selected = re.search(r'^SELECTED cold_shield=(\d+) fire_weapon=(\d+)$', text, re.M)
        if selected is None:
            raise ValueError('Missing original actual-object selection')
        selected_role = 'armour' if selected.groups() == ('1', '0') else 'weapon' if selected.groups() == ('0', '1') else 'INVALID'
        if selected_role != final['role'] or selected_role not in expected_roles:
            raise ValueError('Actual object choice and observer semantic role disagree')
        action = {'kind': 'wield', 'role': selected_role}
    else:
        if final['keys'] or final['keyCount'] != 0 or command or letter or final['role'] != 'none':
            raise ValueError('Unexpected command on a no-swap result')
        action = {'kind': 'none'}
    validate_inputs(inputs)
    return {'id': mode, 'observedInputs': inputs, 'observedAction': action,
            'inputSha256': sha(canonical(inputs)), 'evidence': {
                'bindings': bindings, 'evaluations': evaluated, 'actualSelector': final,
                'originalTrialDangers': dict(zip(('armour', 'weapon'), map(int, trial.groups()))),
                'nativeOnlyHp': dict(zip(('before', 'after', 'lost'), map(int, outcome.groups()))),
                'originalFixturePassed': 'finished: 1/1 passed' in text}}


def validate_inputs(inputs):
    def integer(value, minimum=0, maximum=None):
        if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
            raise ValueError(f'Invalid actual integer: {value!r}')
    def boolean(value):
        if type(value) is not bool:
            raise ValueError('Native boolean was not normalized explicitly')
    integer(inputs['currentDanger']); integer(inputs['avoidance'], 1)
    gates = inputs['gates']
    if gates['usesSwaps'] is not True or gates['maxDepth'] != 50:
        raise ValueError('Original fixture eligibility context changed')
    if inputs['currentDanger'] <= inputs['avoidance'] // 3:
        raise ValueError('Original caller-danger requirement is not met')
    for key in ('usesSwaps', 'hungry', 'weak', 'nearbyUnique'):
        boolean(gates[key])
    integer(gates['panelCount']); boolean(inputs['randarts'])
    for value in inputs['baseCritical'].values(): integer(value, 0, 1)
    for candidate in inputs['candidates'].values():
        if candidate is None: continue
        item = candidate['item']
        if item['category'] not in ('SWORD', 'SHIELD'): raise ValueError('Unsupported original item category')
        integer(item['quantity'], 1)
        for key in ('identified', 'artifact', 'cursed', 'uncursable'): boolean(item[key])
        integer(candidate['evaluation']['rawDanger'])
        for key, value in candidate['evaluation']['critical'].items():
            integer(value, 0, None if key == 'sav' else 1)


def export(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    exporter_bytes = Path(__file__).read_bytes()
    (out / 'executed-exporter.py').write_bytes(exporter_bytes)
    fixture_bytes = git('show', EVIDENCE + ':' + FIXTURE)
    if sha(fixture_bytes) != FIXTURE_SHA:
        raise ValueError('Original immutable fixture hash changed')
    if git('diff', '--name-only', BEFORE, AFTER, '--', 'src', 'lib', 'CMakeLists.txt').decode().splitlines() != [WEAR]:
        raise ValueError('Runtime pair includes changes beyond the single C82 correction')
    for ref in (BEFORE, AFTER):
        if sha(git('show', ref + ':' + WEAR)) != WEAR_SHA[ref]:
            raise ValueError('Native decision implementation changed')
    (out / 'original-scenario.c').write_bytes(fixture_bytes)
    fixture = out / 'scenario.c'
    fixture.write_bytes(fixture_bytes.replace(b'/tmp/native-c-66-expanded', str(out).encode()))
    profile = out / 'profile'
    for directory in (profile, *(profile / x for x in ('save', 'scores', 'panic', 'archive'))): directory.mkdir()
    (profile / 'borg.txt').write_bytes(git('show', EVIDENCE + ':' + CONFIG))
    observer = out / 'observer.c'
    observer.write_bytes((ROOT / 'tools/native-swap-fixture-observer.c').read_bytes())
    manifest = {'schema': 'angband/native-fixture-export@1', 'mechanism': 'CBUG-0066', 'complete': False,
                'toolingCommit': git('rev-parse', 'HEAD').decode().strip(),
                'toolingDirty': bool(git('status', '--porcelain', '--untracked-files=normal').strip()),
                'fixtureCommit': EVIDENCE, 'fixturePath': FIXTURE,
                'originalFixtureSha256': FIXTURE_SHA, 'relocatedFixtureSha256': sha(fixture.read_bytes()),
                'fixtureRelocationOnly': True, 'observerSha256': sha(observer.read_bytes()),
                'exporterSha256': sha(exporter_bytes),
                'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
                'correctionSourceCommit': CORRECTION, 'phases': {}}
    write(out / 'export.json', manifest)
    results = {}
    prepared = {}
    for phase, ref, fix_state in (('before', BEFORE, 'inherited'), ('after', AFTER, 'corrected')):
        source, build, objects, helpers, env, facts = prepare(out, phase, ref, args.jobs)
        prepared[phase] = facts
        rows = []
        for observed in (False, True):
            label = 'observed' if observed else 'plain'
            binary = out / phase / label
            command = ['cc', '-std=c99', '-g', '-DALLOW_BORG', '-I' + str(source / 'src'),
                       '-I' + str(source / 'src/tests'), str(fixture)]
            if observed: command += [str(observer)]
            command += list(map(str, objects + helpers)) + ['-lm']
            if observed: command += ['-Wl,--wrap=' + name for name in LINK_WRAPS]
            command += ['-o', str(binary)]
            run(command, out / phase / (label + '-link.log'), ROOT, env)
            for mode in MODES:
                process = subprocess.run([str(binary), '-v'], cwd=source,
                    env=dict(env, CBUG0066_MODE=mode), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
                raw = process.stdout
                (out / phase / f'{label}-{mode}.log').write_bytes(raw)
                clean = ANSI.sub('', raw.decode())
                if process.returncode != 0 or 'finished:' not in clean:
                    raise RuntimeError(f'{phase}/{label}/{mode}: actual native fixture failed to complete')
                if observed:
                    plain = (out / phase / f'plain-{mode}.log').read_bytes()
                    stripped = b''.join(line for line in raw.splitlines(keepends=True) if not line.startswith(b'POC '))
                    if stripped != plain:
                        raise ValueError(f'{phase}/{mode}: observer changed original fixture output')
                    row = parse_observed(clean, mode)
                    row['evidence'].update({'plainLogSha256': sha((out / phase / f'plain-{mode}.log').read_bytes()),
                                            'observedLogSha256': sha(raw), 'observerStrippedOutputEqualsPlain': True})
                    rows.append(row)
                    print(phase, mode, row['observedAction'], row['observedInputs']['currentDanger'], flush=True)
        provenance = {**facts, 'toolingCommit': manifest['toolingCommit'],
                      'toolingDirty': manifest['toolingDirty'], 'exporterSha256': manifest['exporterSha256'],
                      'fixtureCommit': EVIDENCE, 'originalFixtureSha256': FIXTURE_SHA,
                      'relocatedFixtureSha256': sha(fixture.read_bytes()), 'observerSha256': sha(observer.read_bytes()),
                      'linkWraps': list(LINK_WRAPS), 'compiler': manifest['compiler'],
                      'observerDoesNotAddEvaluations': 'one __real call per link wrapper; exact in-selector count/order; original trial scores match',
                      'observerNonInterference': 'all nine original output/key/HP/assertion traces byte-identical after stripping POC lines'}
        result = {'schema': 'angband/borg-fixture-results@1', 'mechanism': 'CBUG-0066',
                  'boundary': 'backup-swap/post-evaluation', 'variant': {'id': 'native-before' if phase == 'before' else 'native-fixed',
                      'language': 'c', 'fixState': fix_state, 'provenance': provenance}, 'cases': rows}
        results[phase] = result
        write(out / ('native-before.json' if phase == 'before' else 'native-fixed.json'), result)
        manifest['phases'][phase] = {'resultSha256': sha(canonical(result)), 'build': facts}
        write(out / 'export.json', manifest)
    if prepared['before']['headersSha256'] != prepared['after']['headersSha256']:
        raise ValueError('Pinned runtime headers differ; no ABI equivalence claim allowed')
    if prepared['before']['helperSourcesSha256'] != prepared['after']['helperSourcesSha256']:
        raise ValueError('Pinned unit helper sources differ')
    corpus_rows = []
    changed = []
    for before, after in zip(results['before']['cases'], results['after']['cases']):
        mode = before['id']
        if before['observedInputs'] != after['observedInputs']:
            raise ValueError(f'{mode}: native before/fixed decision inputs diverged')
        if not after['evidence']['originalFixturePassed']:
            raise ValueError(f'{mode}: original fixed assertion did not pass')
        differs = before['observedAction'] != after['observedAction']
        if mode in CONTROLS:
            if differs or not before['evidence']['originalFixturePassed']:
                raise ValueError('Original unchanged control changed or failed')
        else:
            if not differs or before['evidence']['originalFixturePassed']:
                raise ValueError('Original protective correction not reproduced')
            changed.append(mode)
        corpus_rows.append({'id': mode, 'inputs': before['observedInputs'],
                            'expected': {'inherited': before['observedAction'], 'corrected': after['observedAction']}})
    if len(changed) != 5: raise ValueError('Expected five changed protective cases')
    corpus = {'schema': 'angband/borg-fixture-corpus@1', 'mechanism': 'CBUG-0066',
              'boundary': 'backup-swap/post-evaluation', 'provenance': {
                  'fixtureCommit': EVIDENCE, 'fixtureSha256': FIXTURE_SHA, 'beforeRuntime': BEFORE,
                  'fixedRuntime': AFTER, 'sourceCorrection': CORRECTION,
                  'nativeBeforeResultSha256': sha(canonical(results['before'])),
                  'nativeFixedResultSha256': sha(canonical(results['after'])),
                  'scope': 'Recorded native decision facts; no shared-world/damage/Neo-danger equivalence claim'},
              'cases': corpus_rows}
    write(out / 'cases.json', corpus)
    manifest.update(complete=True, changedCases=changed, unchangedControls=sorted(CONTROLS),
                    corpusSha256=sha(canonical(corpus)), matchingHeadersAndHelperSources=True)
    write(out / 'export.json', manifest)
    print('Verified nine native input pairs, five changes, four unchanged controls.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--jobs', default=2, type=int)
    args = parser.parse_args()
    if args.jobs < 1: parser.error('--jobs must be positive')
    export(args)


if __name__ == '__main__': main()
