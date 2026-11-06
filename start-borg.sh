#!/usr/bin/env bash
# Open the native game; the player starts the Borg manually.
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
game_dir="$repo_dir/build/native/game"

usage() {
    cat <<'EOF'
Usage: ./start-borg.sh [CHARACTER]

Open Angband using CHARACTER's save, or create it if it does not exist.
Without a name, ask which character to use (default: BorgPlay).
Start the Borg yourself with Ctrl+Z, confirm if asked, then z.
Ctrl+X saves and exits. Saves are in build/native/game/lib/save/.

Set BORG_PLAY_FONT to override the default 28-pixel Courier font.
EOF
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
    usage
    exit 0
fi
if (( $# > 1 )); then
    usage >&2
    exit 2
fi

character="${1:-}"
if [[ -z "$character" ]]; then
    read -r -p 'Character/save name [BorgPlay]: ' character || true
    character="${character:-BorgPlay}"
fi
if [[ "$character" == */* || "$character" == .* || "$character" == -* ]]; then
    echo 'Choose a character name without slashes or a leading dot or dash.' >&2
    exit 2
fi
if [[ ! -x "$game_dir/angband" ]]; then
    echo 'Build first: flock /tmp/angband-validation.lock python3 tools/verify-native.py' >&2
    exit 1
fi
if [[ -z ${DISPLAY:-} ]]; then
    echo 'An X11 display is required; run this from a WSLg or X11 terminal.' >&2
    exit 1
fi

export ANGBAND_X11_FONT_0="${BORG_PLAY_FONT:-${ANGBAND_X11_FONT_0:--adobe-courier-medium-r-normal--28-*-*-*-p-*-iso8859-1}}"
printf 'Save: %s/lib/save/%s\n' "$game_dir" "$character"
echo 'Start Borg: Ctrl+Z, confirm if asked, then z. Save and exit: Ctrl+X.'
cd -- "$game_dir"
exec ./angband -mx11 "-u$character" -- -n1
