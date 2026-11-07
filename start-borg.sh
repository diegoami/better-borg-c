#!/usr/bin/env bash
# Open the native game; the player starts the Borg manually.
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
game_dir="$repo_dir/build/native/game"

usage() {
    cat <<'EOF'
Usage: ./start-borg.sh [CHARACTER] [--from-backup[=SLOT]]

Open Angband using CHARACTER's save, or create it if it does not exist.
Without a name, ask which character to use (default: BorgPlay).
Start the Borg yourself with Ctrl+Z, confirm if asked, then z.
Ctrl+X saves and exits. Saves are in build/native/game/lib/save/.
Before launch, keep five rolling copies of an existing save in
build/native/game/lib/save/backups/CHARACTER/ (save.1 is newest).

Set BORG_PLAY_FONT to override the default 28-pixel Courier font.
Offers to rebuild missing/stale local sources; does not fetch remote updates.
Different character names can run together; each save is locked while playing.
--from-backup restores slot 1; --from-backup=2 selects another slot (1..5).
The current save is preserved in a timestamped before-restore file first.
EOF
}

character=''
restore_slot=''
while (( $# )); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --from-backup) restore_slot=1 ;;
        --from-backup=*)
            restore_slot="${1#*=}"
            if [[ -z "$restore_slot" ]]; then echo 'Backup slot is required after =.' >&2; exit 2; fi
            ;;
        -*) usage >&2; exit 2 ;;
        *)
            if [[ -n "$character" ]]; then usage >&2; exit 2; fi
            character="$1"
            ;;
    esac
    shift
done
if [[ -n "$restore_slot" && ! "$restore_slot" =~ ^[1-5]$ ]]; then
    echo 'Backup slot must be 1 through 5.' >&2
    exit 2
fi
if [[ -z "$character" ]]; then
    read -r -p 'Character/save name [BorgPlay]: ' character || true
    character="${character:-BorgPlay}"
fi
if [[ "$character" == */* || "$character" == .* || "$character" == -* ]]; then
    echo 'Choose a character name without slashes or a leading dot or dash.' >&2
    exit 2
fi
if [[ -z ${DISPLAY:-} ]]; then
    echo 'An X11 display is required; run this from a WSLg or X11 terminal.' >&2
    exit 1
fi

check_build() {
    python3 - "$repo_dir" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1])
try:
    receipt = json.loads((root / 'artifacts/native/result.json').read_text())
    if not receipt.get('success') or not (root / 'build/native/game/angband').is_file():
        raise ValueError('No verified playable build found.')
    commit = receipt['commit']
    subprocess.run(['git', '-C', str(root), 'cat-file', '-e', commit + '^{commit}'],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    changed = subprocess.run(['git', '-C', str(root), 'diff', '--quiet', commit, '--',
                              'src', 'lib', 'CMakeLists.txt', 'scripts', 'm4',
                              'tools/verify-native.py'], check=False)
    if changed.returncode:
        raise ValueError('Build sources differ from verified commit ' + commit[:12] + '.')
    print('Build sources match verified commit ' + commit[:12] + '.')
except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
    print(str(exc))
    sys.exit(1)
PY
}

if ! check_build; then
    answer=''
    read -r -p 'Build and verify the local checkout now? [y/N] ' answer || true
    if [[ "$answer" == y || "$answer" == Y || "$answer" == yes ]]; then
        (cd -- "$repo_dir" && flock /tmp/angband-validation.lock python3 tools/verify-native.py)
        check_build
    elif [[ ! -x "$game_dir/angband" ]]; then
        echo 'No playable executable; build before starting the game.' >&2
        exit 1
    else
        echo 'Continuing with the existing executable.'
    fi
fi

mkdir -p -- "$game_dir/lib/save/.locks"
exec 9>"$game_dir/lib/save/.locks/$character.lock"
if ! flock -n 9; then
    echo "Character '$character' is already open through this launcher." >&2
    exit 1
fi

save_file="$game_dir/lib/save/$character"
if [[ -n "$restore_slot" ]]; then
    python3 "$repo_dir/tools/borg-saves.py" restore "$save_file" "$restore_slot"
fi
if [[ -f "$save_file" ]]; then
    backup_dir="$game_dir/lib/save/backups/$character"
    mkdir -p -- "$backup_dir"
    for (( slot=5; slot>=2; slot-- )); do
        previous="$backup_dir/save.$((slot - 1))"
        if [[ -f "$previous" ]]; then
            cp -p -- "$previous" "$backup_dir/save.$slot"
        fi
    done
    cp -p -- "$save_file" "$backup_dir/save.1"
    printf 'Backup: %s/save.1 (five copies retained)\n' "$backup_dir"
fi

export ANGBAND_X11_FONT_0="${BORG_PLAY_FONT:-${ANGBAND_X11_FONT_0:--adobe-courier-medium-r-normal--28-*-*-*-p-*-iso8859-1}}"
printf 'Save: %s/lib/save/%s\n' "$game_dir" "$character"
echo 'Start Borg: Ctrl+Z, confirm if asked, then z. Save and exit: Ctrl+X.'
cd -- "$game_dir"
exec ./angband -mx11 "-u$character" -- -n1
