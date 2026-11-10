# better-borg-c

A native C Angband/Borg consumer: adoption and testing of verified bug fixes
in a playable derivative of official Angband. Clone this repository, build
it, and you get Angband with the Borg compiled in and those fixes already
applied — there is no separate Borg package or install step.

Source reports, native reproductions and reusable C fix proposals belong to
[neo-angband-tracker](https://github.com/diegoami/neo-angband-tracker/issues);
this repository owns adoption, integration and testing of those fixes. See
[docs/ADOPTION.md](docs/ADOPTION.md) for the full scope, status labels
(carried/fixed/partial) and the boundaries with the TypeScript and Rust
sibling projects, and [UPSTREAM.md](UPSTREAM.md) for the Angband baseline
and source remotes this is built from.

## Download a release

If you only want to play or build the game, take the
[latest release](https://github.com/diegoami/better-borg-c/releases/latest)
instead of cloning this repository. Each release has a Linux binary, a plain
patched Angband source package and a patch for your own angband/angband
checkout, without the tooling and evidence kept here. See
[docs/RELEASE-INSTALL.md](docs/RELEASE-INSTALL.md). The current release,
`4.2.6-impact-v9.1`, is milestone 9 plus its Necromancer crash fix.
`tools/make-release.py --ref TAG --version TAG --out DIR` rebuilds a
release's assets.

## Installing from this repository

**Prerequisites** (Debian/Ubuntu): `git python3 cmake build-essential
libx11-dev perl util-linux`. Python 3.9+ and CMake 3.7+ (a current CMake 3.x
is the tested setup).

**Build and verify**, from the repository root:

```sh
flock /tmp/angband-validation.lock python3 tools/verify-native.py
```

This configures, builds and runs Angband's own test suite as a sanity check
before you play. See [docs/VERIFICATION.md](docs/VERIFICATION.md) for what
it checks and for the CI schedule. For a plain CMake build, other front ends,
or installing system-wide instead, see
[original build documentation](docs/hacking/compiling.rst) — the resulting
binary already has the Borg built in (`ALLOW_BORG`).

## Playing

Run `./start-borg.sh BorgPlay` from the repository root for an interactive
X11 game. Omit the name to be prompted, or give another name for a different
character; existing saves resume, missing saves enter character creation.
Once in-game, press **Ctrl-Z**, then **z** to activate the Borg; any key
stops it. **Ctrl-X** saves and exits. Run `./start-borg.sh --help` for
options (including restoring a rolling save backup with `--from-backup`), or
run `./angband` directly from `build/native/game/`. Use disposable
characters — no saves, scores or profiles are imported by bootstrap.

For a Borg that plays unattended without a window, use
`./run-borg-headless.py BorgPlay --turns 10000` (`--help` for options).

See [docs/hacking/borg.rst](docs/hacking/borg.rst) for the full in-game Borg
command reference, and
[docs/measurement/REPLAY-TOOLKIT.md](docs/measurement/REPLAY-TOOLKIT.md) for
save backups/restore, headless play, recording and verified replay of past
sessions, death collection, and the rest of the tooling in this repository.

## Tools

- [`start-borg.sh`](start-borg.sh) / [`run-borg-headless.py`](run-borg-headless.py) —
  interactive and unattended play, covered above.
- [`replay-borg.py`](replay-borg.py) — verify and watch a recorded session.
- [`produce_death.py`](produce_death.py) / [`tools/record-death.py`](tools/record-death.py) —
  collect games and curate [death records](docs/deaths/README.md).

[docs/measurement/REPLAY-TOOLKIT.md](docs/measurement/REPLAY-TOOLKIT.md) is
the entry point for all of the above, with every command's full options.

## Project status and policy

[AGENTS.md](AGENTS.md), [RULES.md](RULES.md), [PLAN.md](PLAN.md) and
[session.json](session.json) govern how this repository is worked on;
[checkpoint #1](https://github.com/diegoami/better-borg-c/issues/1) and the
other GitHub issues are authoritative for live status.
