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

For an interactive X11 build, run `./angband` from `build/native/` after the
build. Use disposable characters. No saves, scores, profiles or owner data
are imported by bootstrap. See [original build documentation](docs/hacking/compiling.rst)
and [upstream README](docs/upstream-reference/README.md).

This is an independent GitHub repository with preserved C ancestry, not a
second fork-network member: the owner's existing Angband fork hosts the source
tracker. Fetch `angband` for pristine C and `source-tracker` for named proposals;
both source remotes have push disabled locally. Offer reusable corrections
through the tracker. No agent posting to angband/angband is authorised.

The only active workflow builds/tests on GitHub-hosted `ubuntu-latest` for
main/PR/manual events; it never publishes. Inherited workflows are archived
outside `.github/workflows/`. No tag/release, lab deployment or private backup
is part of setup.
