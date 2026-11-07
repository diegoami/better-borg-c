#!/usr/bin/env bash
# Open the native game; the player starts the Borg manually.
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
game_dir="$repo_dir/build/native/game"

usage() {
    cat <<'EOF'
Usage: ./start-borg.sh [CHARACTER] [--from-backup[=SLOT]] [--seed SEED]

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
Both visible and headless sessions record replay data. --seed sets a new
character's seed; otherwise a random seed is recorded for visible play.
EOF
}

character=''
restore_slot=''
seed=''
while (( $# )); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --seed)
            if (( $# < 2 )); then echo '--seed requires a uint32 value.' >&2; exit 2; fi
            seed="$2"; shift
            ;;
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
if [[ -n "$seed" ]] && ! python3 -c 'import sys; n=int(sys.argv[1]); sys.exit(not 0 <= n <= 0xffffffff)' "$seed"; then
    echo 'Seed must be uint32.' >&2; exit 2
fi
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
if [[ -n "$seed" ]]; then
    exec python3 "$repo_dir/tools/start-recorded-borg.py" "$character" "$seed"
fi
exec python3 "$repo_dir/tools/start-recorded-borg.py" "$character"
