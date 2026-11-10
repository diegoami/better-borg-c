# Prior-fixture kits for the regression matrix

Each directory here is one fixture kit used by `tools/regression-matrix.py`
(`GROUPS`). The matrix links the kit's `scenario.c` against the given build's
core objects, runs every mode, and compares the `OUTCOME` rows to the baseline
logs kept in the kit.

## Contents

| File | Role |
| --- | --- |
| `scenario.c` | the fixture source; the matrix compiles it at run time against the build under test |
| `*.h` | companion headers a fixture includes (e.g. `text-bufsize/t287-variant.h`) |
| `profile/borg.txt` | the Borg configuration the fixture runs with (`TAG_PROFILE`) |
| `*.log` | recorded baseline runs; the matrix reads their `OUTCOME` rows and reports byte identity separately |
| `run-cases.py` | only in the source-tracker kits fetched at an evidence pin (see below) |

Linked binaries, object files, `result.json` and tarballs from the original
worktrees are **not** committed; the kits build from source.

## Provenance

* `necrolight-296-crash`, `spasticscore-147-product`: committed with their
  carries (the pattern this directory follows).
* The other 36 directories: restored 2026-11-10 from the untracked
  `.worktrees/<carry>/artifacts/...` kit directories that the v9 run read.
  Those kits were never tracked, are not on the `task/carry-*` branches, and
  disappeared from a clean checkout, so the accumulated matrix could not be
  rerun. Owner decision 2026-11-10 deferred restoring them to milestone 10;
  the files here are the same sources and baseline logs, copied unchanged, and
  `GROUPS` now points at these paths.
* `fleeheal-408`: the I-002 fixture baselines, committed in the milestone 10
  review corrections (M10-R-02) from the same kind of working tree; the
  scenario source itself is `tools/fleeing-heal-scenario.c`.

## Baselines and expectations

The committed `.log` files are the recorded baseline runs (pre-fix for
fail-before/pass-after fixtures, after-fix for the rest). The matrix compares
`OUTCOME` rows value-for-value, reports byte identity separately, and applies
the declared intentional transitions in `GROUPS` (`rows_must`, `fail`,
`rows_free`). A byte difference alone is information, not a failure.

## Verification at restoration (2026-11-10)

The 36 restored groups were rerun against the product build rebased onto
`c1a80e92c` (source identical to `25d1ce6a7`, the package head; the kit files
were working-tree files at run time and were committed unchanged as
`0263951f8`): 91 cases (the `text` group is declared skipped), **all 91 OK,
zero unexpected row differences against
`docs/measurement/impact-v9/regression-summary.json`**. The four rows that do
differ from the v9 baseline rows are the milestone 9 declared transitions
(vampire-257 `near-far`/`near-near` refusal, pinned by `rows_must`;
dispel-259 `reserve`/`clear`, declared failing with the losdispel-326 absolute
values).

## Second batch: the 22 0049-era groups (2026-11-10, after the v10 tag)

The last 22 groups whose baselines still lived in the gitignored `artifacts/` tree (swap, knockout,
preparation, cold-protection, rings, potion-timing, itangast, shot-path, brand, stairtrack,
acidarc, outoflight, mapwall, enlightenment, stairreturn, blowname, excavate, calllight, gloves,
detectcarry, maimfoe, recalldepth) are committed here in the same shape: `scenario.c`,
`profile/borg.txt` and the recorded `*.log` baselines, with `GROUPS` repointed. That closes the
dependency: all 60 local fixtures are now in the repository.

## Residual dependency

None for the local groups. The matrix needs nothing outside the clone except history: the 17
`KIT_GROUPS` fetch their fixtures at the ledger's evidence commits, so they need a full clone, not
a shallow one.
