# better-borg-c

A native C Angband/Borg consumer for verified bug fixes. This repository starts
from Angband master `e473720ed88a0f0c7ca66815cef3000eb4a38bc3`, preserving its
history, credit, licence, game and Borg sources. Bootstrap adds no gameplay fix.

Source reports, native reproductions and reusable C fix proposals belong to
[neo-angband-tracker](https://github.com/diegoami/neo-angband-tracker/issues).
This repository owns adoption, integration and testing of those fixes in a
playable C derivative. Each adoption has its own issue linked to the source.
It does not replace the source tracker or take over its native-C session.

- **carried**: corrected and verified here, but not yet resolved upstream;
  the adoption issue stays open.
- **fixed**: resolved upstream and incorporated, rebuilt and verified here;
  close the adoption issue.
- **partial** / **not-carried**: name the actual missing work. A patch file or
  proposal alone is not a carry. `patch-active` tracks maintained backports
  separately from issue closure.

Faithful TypeScript port repairs stay in neo-angband-borg-mod-tracker. Mandos
independently translates C fixes into TypeScript; borg-rs independently handles
Rust and reports directly to the source board. This product has no Neo engine,
TypeScript, Rust or private lab ownership. Current scope is bugs, not new strategy.

Read [AGENTS.md](AGENTS.md), [RULES.md](RULES.md), [PLAN.md](PLAN.md),
[session.json](session.json) and the latest comments on
[checkpoint #1](https://github.com/diegoami/better-borg-c/issues/1).
[UPSTREAM.md](UPSTREAM.md) records the baseline; [patches/README.md](patches/README.md)
explains the ledger. Issues are authoritative for live status.

## Build and check

On Debian/Ubuntu install `git python3 cmake build-essential libx11-dev perl
util-linux`. Use Python3.9+ and CMake3.7+ (a current CMake3.x is the tested setup).
From this repository:

```sh
flock /tmp/angband-validation.lock python3 tools/verify-native.py
```

This configures Borg and the test frontend, builds with two jobs and runs
Angband's `alltests` target (including `allunittests`). It checks the numerical
unit/frontend summaries as well as exit codes: the original unit runner can
return zero after a failed assertion. Logs and hashed results go to ignored
`artifacts/native/`. These baseline checks do not establish Borg survival;
each adoption also needs the source bug's legal scenario and controls.

For an interactive X11 build, run `./start-borg.sh BorgPlay` from the repository
root after building. Omit the name to be prompted, or give another name to use
another character. Existing saves resume; missing saves enter character creation.
The launcher uses a readable 28-pixel Courier font (`BORG_PLAY_FONT` overrides it)
and one window. Start the Borg manually with Ctrl+Z, confirm if asked, then `z`.
Ctrl+X saves and exits; saves live in `build/native/game/lib/save/`.
Before each launch of an existing save, the script keeps five rolling backups
under `build/native/game/lib/save/backups/CHARACTER/`; `save.1` is newest.
It stops if a backup fails. Run
`./start-borg.sh --help` for details. You can also run `./angband` directly from
`build/native/game/`. Use disposable characters. No saves, scores, profiles or owner data
are imported by bootstrap. See [original build documentation](docs/hacking/compiling.rst)
and [upstream README](docs/upstream-reference/README.md).

The launcher compares the native verification receipt with the local build
sources and offers the normal locked build/test gate when missing or stale.
Declining keeps the existing executable, if available. It does not pull remote
changes. Different character names may run concurrently; a per-character lock
prevents two launches through this script from opening the same save.

To return to a pre-death backup, run `./start-borg.sh BorgPlay --from-backup`.
Slot 1 is the newest; use `--from-backup=2` for slot 2 (through 5). This explicitly
restores the selected snapshot, whether or not the current character is dead.
The current save is preserved as a timestamped `before-restore-*.save` beside
the rolling copies before replacement. A missing backup stops the launch.

For bounded play without a window:

```sh
./run-borg-headless.py BorgPlay --turns 10000
./run-borg-headless.py BorgPlay --turns 10000 --from-backup
```

This loads the named save, activates the native Borg and plays **additional
engine turns** from its starting turn. A missing save creates a Human Warrior
with ordinary point buy (`--seed` sets a new character's RNG, default 1).
It saves at the first command boundary at or after the target, so long actions
can overshoot; the actual count is reported. Saves go to the same
`build/native/game/lib/save/NAME` directory as the visible launcher, with the
same five backups and character lock. Headless `--from-backup=2` also selects
slot 2. Different names can coexist; heavy headless builds/runs serialize on
the shared validation lock.

The first headless launch prepares a cached observer build from the checkout's
committed source; later launches reuse it while source/observer identity matches.
Tracked runtime edits must be committed first. Full traces, input/final/living
saves, native maps and hashed build/results remain under `artifacts/headless/`.
The normal GUI binary is unchanged. Loaded saves restore the character/dungeon
and game RNG, but not complete Borg memory, so continuation is not guaranteed
to reproduce uninterrupted decisions. A backup restart is a replay branch,
not another independent life for survival statistics.

Headless play disables continuous resurrection and stops on natural death,
victory or the turn target. A normal finish atomically publishes its final save;
a timeout, stall, crash or failed save leaves the previous named save untouched
(an explicitly requested backup restore still takes effect). `--timeout` and
`--stall-timeout` bound wall time/no-progress, separately from engine turns.
A dead final save remains dead. On natural death, the runner puts the most
recent living checkpoint in rolling backup slot 1, so
`--from-backup` can resume from before death. New characters also retain their
starting save as a backup. These checkpoint restores reset Borg memory.
Natural deaths export an unassessed dossier
under `docs/deaths/`, link the discussion in issue111 (`--death-issue` overrides
it), and regenerate the registry. Replay qualification, assessment and causal
investigation remain pending agent work under the death protocol; automatic
export does not establish a bug or a completed investigation.

This is an independent GitHub repository with preserved C ancestry, not a
second fork-network member: the owner's existing Angband fork hosts the source
tracker. Fetch `angband` for pristine C and `source-tracker` for named proposals;
both source remotes have push disabled locally. Offer reusable corrections
through the tracker. No agent posting to angband/angband is authorised.

Native verification runs on GitHub-hosted `ubuntu-latest` for main/PR/manual
events. The explicitly owner-requested donor inventory also runs weekly on
Mondays09:15 Europe/Berlin and by manual dispatch, reporting to
[ongoing issue24](https://github.com/diegoami/better-borg-c/issues/24). It reads
public C source metadata and queues semantic review; it never executes/imports
fork code or proves better play from activity. Bugs still take priority.

[Death records](docs/deaths/README.md) pin actual build/version, native recording,
evaluation/diagnosis confidence and issue actions, with replay-safe aggregation.
Full runs/saves/builds stay outside Git. [UPSTREAM.md](UPSTREAM.md) records our
integrated-build delivery and later, separately owned Rust adoption path.

Neither active workflow publishes. Inherited workflows remain archived outside
`.github/workflows/`. No tag/release, lab deployment or private backup is part
of setup. GitHub schedules are best-effort and may be delayed/disabled after
public-repository inactivity; ongoing issue24 records run receipts and follow-up.
