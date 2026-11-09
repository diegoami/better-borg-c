#!/usr/bin/env python3
"""Build the release assets for one better-borg-c ref: a patch for an upstream
checkout, a patched plain-Angband source package and a Linux x86_64 binary."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GAME_PATHS = ['src', 'lib', 'CMakeLists.txt', 'configure.ac', 'Makefile.src']


def git(*args, cwd=ROOT, text=True):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=text).stdout


def run(cmd, cwd, log):
    with open(log, 'a') as handle:
        handle.write('$ ' + ' '.join(map(str, cmd)) + '\n')
        handle.flush()
        subprocess.run(cmd, cwd=cwd, check=True, stdout=handle, stderr=subprocess.STDOUT)


def deterministic_tar(src_dir, out_path, mtime):
    """tar.gz with sorted entries, fixed mtime and neutral ownership."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.PAX_FORMAT) as tar:
        def add(path):
            info = tar.gettarinfo(str(path), arcname=str(path.relative_to(src_dir.parent)))
            info.mtime, info.uid, info.gid, info.uname, info.gname = mtime, 0, 0, '', ''
            if info.isfile():
                with open(path, 'rb') as handle:
                    tar.addfile(info, handle)
            else:
                tar.addfile(info)
        add(src_dir)
        for path in sorted(src_dir.rglob('*')):
            add(path)
    with open(out_path, 'wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=mtime) as gz:
            gz.write(buffer.getvalue())


def export_tree(ref, dest):
    dest.mkdir(parents=True)
    archive = subprocess.run(['git', 'archive', '--format=tar', ref], cwd=ROOT, check=True,
                             capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(dest, filter='tar')


def source_tree(base, ref, dest):
    """Upstream base with the release's game files overlaid; nothing else."""
    export_tree(base, dest)
    changes = git('diff', '--name-status', '--no-renames', base, ref, '--', *GAME_PATHS)
    for line in changes.splitlines():
        status, path = line.split('\t', 1)
        target = dest / path
        if status == 'D':
            target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.run(['git', 'show', f'{ref}:{path}'], cwd=ROOT, check=True,
                                          capture_output=True).stdout)
        mode = git('ls-tree', ref, '--', path).split()[0]
        target.chmod(0o755 if mode == '100755' else 0o644)
    return changes


def ledger(ref):
    series = json.loads(git('show', f'{ref}:patches/series.json'))
    rows = ['| Unit | Patch | Consumer issue | Source issue |', '| --- | --- | --- | --- |']
    for unit in series['patches']:
        if unit.get('patch_active'):
            rows.append(f"| {unit['id']} | `{Path(unit['patch']).name}` | {unit.get('consumer_issue', '')} "
                        f"| {unit.get('source_issue', '')} |")
    return series, '\n'.join(rows) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', required=True, help='release tag or commit')
    parser.add_argument('--version', required=True, help='release version, e.g. 4.2.6-impact-v9.1')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    parser.add_argument('--skip-binary', action='store_true')
    args = parser.parse_args()

    ref = git('rev-parse', args.ref).strip()
    series, table = ledger(ref)
    base = series['baseline']
    mtime = int(git('show', '-s', '--format=%ct', ref).strip())
    install = git('show', f'{ref}:docs/RELEASE-INSTALL.md')
    notes = (f"better-borg-c {args.version}\n\nRelease commit: {ref}\n"
             f"Upstream base (angband/angband): {base}\n\n")
    args.out.mkdir(parents=True, exist_ok=True)
    log = args.out / 'build.log'
    log.write_text('')
    work = Path(tempfile.mkdtemp(prefix='bbc-release-'))
    assets = []

    diff = subprocess.run(['git', 'diff', '--binary', '--full-index', '--no-renames', base, ref, '--',
                           *GAME_PATHS], cwd=ROOT, check=True, capture_output=True).stdout

    patch_dir = work / f'better-borg-c-{args.version}-patch'
    (patch_dir / 'provenance' / 'patches').mkdir(parents=True)
    (patch_dir / f'better-borg-c-{args.version}.diff').write_bytes(diff)
    (patch_dir / 'apply.sh').write_text(APPLY.format(base=base, version=args.version))
    (patch_dir / 'apply.sh').chmod(0o755)
    (patch_dir / 'INSTALL.md').write_text(install)
    (patch_dir / 'RELEASE.txt').write_text(notes)
    (patch_dir / 'provenance' / 'series.json').write_text(json.dumps(series, indent=2) + '\n')
    (patch_dir / 'provenance' / 'UNITS.md').write_text(PROVENANCE + table)
    for unit in series['patches']:
        if unit.get('patch_active'):
            name = Path(unit['patch']).name
            (patch_dir / 'provenance' / 'patches' / name).write_bytes(
                subprocess.run(['git', 'show', f"{ref}:{unit['patch']}"], cwd=ROOT, check=True,
                               capture_output=True).stdout)
    assets.append(args.out / f'{patch_dir.name}.tar.gz')
    deterministic_tar(patch_dir, assets[-1], mtime)

    src_dir = work / f'better-borg-c-{args.version}-src'
    source_tree(base, ref, src_dir)
    (src_dir / 'BETTER-BORG-INSTALL.md').write_text(install)
    (src_dir / 'BETTER-BORG-RELEASE.txt').write_text(notes)
    (src_dir / 'BETTER-BORG-UNITS.md').write_text(PROVENANCE + table)
    assets.append(args.out / f'{src_dir.name}.tar.gz')
    deterministic_tar(src_dir, assets[-1], mtime)

    if not args.skip_binary:
        build = work / 'build'
        prefix = work / f'better-borg-c-{args.version}-linux-x86_64'
        run(['cmake', '-S', src_dir, '-B', build, '-DCMAKE_BUILD_TYPE=Release', '-DSUPPORT_BORG=ON',
             '-DSUPPORT_X11_FRONTEND=ON', '-DSC_INSTALL=ON', f'-DCMAKE_INSTALL_PREFIX={prefix}'], work, log)
        run(['cmake', '--build', build, '--parallel', str(args.jobs)], work, log)
        run(['cmake', '--install', build], work, log)
        user = next(prefix.rglob('lib/user'), None) or (prefix / 'lib' / 'user')
        user.mkdir(parents=True, exist_ok=True)
        shutil.copy(src_dir / 'src' / 'borg' / 'borg.txt', user / 'borg.txt')
        shutil.copy(src_dir / 'docs' / 'copying.rst', prefix / 'COPYING.rst')
        (prefix / 'INSTALL.md').write_text(install)
        (prefix / 'RELEASE.txt').write_text(notes + 'Source: the -src asset of this release.\n')
        assets.append(args.out / f'{prefix.name}.tar.gz')
        deterministic_tar(prefix, assets[-1], mtime)

    sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in assets)
    (args.out / 'SHA256SUMS').write_text(sums)
    print(sums, end='')
    print(f'work directory kept for inspection: {work}')


APPLY = """#!/bin/sh
# Apply better-borg-c {version} to an angband/angband checkout at {base}.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
target=${{1:-.}}
cd "$target"
head=$(git rev-parse HEAD)
if [ "$head" != "{base}" ]; then
    echo "warning: this checkout is at $head, not the tested base {base}" >&2
    echo "         (git checkout {base} to match the release exactly)" >&2
fi
git apply --check "$here/better-borg-c-{version}.diff"
git apply "$here/better-borg-c-{version}.diff"
echo "applied better-borg-c {version}; build as described in INSTALL.md"
"""

PROVENANCE = """# Carried units

The cumulative diff is authoritative. It equals the active carried patches
listed below, applied in order to the upstream base, plus two later changes
that are not separate patch files: the munchkin-start-by-class default
(better-borg-c PR #302, `borg_munchkin_by_class` in borg.txt) and the crash
correction to 0099 (PR #398). The individual patches are kept for provenance
and review; each links its consumer and source issue.

"""

if __name__ == '__main__':
    main()
