# Milestone 12: one carry and the official import since impact v11

Package for the milestone-12 review. It records what the cycle contains, where the evidence is,
and what is **not** measured. The review map (`docs/review/MILESTONE12.md`) holds the reviewer's
checks and prompt.

**This is not a self-review.** Everything here is the implementer's account; the review issue is
where an independent verdict goes.

## Window

| | |
| --- | --- |
| Base | tag `4.2.6-impact-v11` on runtime snapshot `39268ca8a` |
| Head | `4e1b912cb` (PR 478, `origin/main` when this package was written) |
| Size | 6 first-parent merges, 64 files changed, +9790/-164 |
| Compare view | https://github.com/diegoami/better-borg-c/compare/4.2.6-impact-v11...4e1b912cb |
| Runtime surface | 32 files, +674/-128: one carry (`borg-flow-kill.c`, -18) and the official import |

The window also contains the milestone-11 package, its review corrections and the tag record
(PRs 472-474) and the v11 state PR (477). None of those touch `src/`.

## The two changes

| Change | Source | PR / merge | What it does |
| --- | --- | --- | --- |
| 0118 NEWKILL-95 | tracker 95 (CBUG-0079) | 476 / `a39d23d8f` | `borg_new_kill()` no longer forces a newly seen wall-walker's grid to floor (the race was read from the slot before the new race was stored) |
| Official import | `angband/angband` `42cd156ac` | 478 / `4e1b912cb` | merges 12 official commits past `e473720ed` (5 Borg, 7 non-Borg); retires carries 0001 and 0002 |

### 0118 NEWKILL-95

One `cherry-pick -x` of the reviewed C-only source commit `1a220cb2d`, the unchanged kit at
`docs/audit/c-reports/newkill-95/`, `tools/verify-newkill95.py`, `docs/measurement/NEWKILL-95.md`.
On the unchanged fixture the wall mode keeps the granite under the wall-walker and queues no shot;
the floor control is byte-identical. The code is shared sighting logic with no mode gate.

### Official import (PR 478)

* One merge conflict, in `borg_backup_swap`, resolved to the upstream form. The other local carries
  in `borg-item-wear.c` are untouched. Upstream moved `borg_dont_react` into `borg.dont_react`, so
  `generate_keypress` in `borg.c` reads the field again.
* **Retired carries:** 0001 (CBUG-0066 safer swap, upstream `bc67c099e`) and 0002 (CBUG-0002
  knockout gate, upstream `9d062a64d`, `8c75bdccb`, `42cd156ac`). `patch_active` is false in
  `patches/series.json`; the patch files are kept.
* **Evidence:** unchanged tracker fixtures `1b67370d` (swap: 5 fail-before/pass-after, 4 controls
  byte-identical, 79 -> 26 HP and 113 -> 59 HP) and `3de1e312` (knockout: kill reactions 0 -> 1,
  suppression 1 -> 0, 3 controls byte-identical). "Before" is the import head with the five upstream
  Borg commits reverted (recipe in `UPSTREAM.md`). The knockout fixture reads the removed global, so
  `tools/verify-knockout.py` and `tools/regression-matrix.py` map it at compile time; the fixture file
  is unchanged.
* An independent PR review (a review on PR 478) returned request-changes on one tooling
  blocker (the regression-matrix knockout group did not compile) plus accuracy/ledger gaps M2-M6; all
  were applied in `8de6ed459` before merge. M7 (close consumer issues 4 and 7 as `fixed`) is done.
* Native gate on the merge and the hosted `native` check on the merge head: green
  (965/965 unit, 5/5 frontend).

Ledger: `patches/series.json` has 117 entries, 115 `patch-active`.

## What is not measured (and is owed)

**The per-mode arms were not run by this repo; the zoo's normal and class-rule arms are recorded below.** The owner's 2026-11-10 rule requires each reachable mode configuration
(unrestricted, munchkin/Lunal only, normal only) to be tested before a per-mode claim.

* 0118 is shared sighting code. Its effect is measured only together with the import, in the normal and class-rule configurations (see the zoo section); alone, and in Lunal-only and unrestricted, it is **not measured**.
* The import's merged hunks (upstream's `b_p1`/`b_p2 = 9999` initialisation and removed early return in
  `borg_backup_swap`, the single-gate knockout reaction) are measured only together with 0118 in the two
  zoo configurations; Lunal-only and unrestricted are **not measured**. The fixtures show equivalence on
  constructed scenarios only.
* The 7 non-Borg official commits (rest handling, `TERM_XTRA_CLEAR`, object-file ordering, Windows
  open dialog) are exercised only by the native gate.
* No frozen-v1 cohort run was made for this window (the zoo class-grid arms are below).

The batch measurement with explicit arms belongs to `diegoami/borg-zoo` issue 54 (separate repo and
session). Until it runs, the claim of this milestone is **"the defect is fixed, the retired carries
are covered by upstream, and every native gate is green"**, not "the Borg plays better".

## Zoo measurement (classes-v12, 2026-11-13)

Measured by `diegoami/borg-zoo` (experiment `experiments/classes-v12.json`, specimen
`4.2.6-bbc-m12` at `4e1b912cb`, 115 carries; results on the zoo's `results` branch under
`results/classes-v12/`). Runs: `43353949090-1` (`normal`, every mode pinned off) and
`43353951603-1` (`munchkin-class`, the class rule). Each is the 1800-cell class grid, cap
100000 turns, 0 missing cells, 0 config errors. This repo only reads those results.

| Arm | Cells | Death | Turn cap | Other | Mean max depth | Mean max level |
| --- | --- | --- | --- | --- | --- | --- |
| v12 normal | 1800 | 524 | 1276 | 0 | 2.38 | 4.12 |
| v12 munchkin-class | 1800 | 470 | 1329 | 1 stalled | 3.17 | 4.85 |

Paired against the zoo's `classes-v11` run (`42890625267-1`, specimen `4.2.6-bbc-m11`), which
only has 900 usable cells per profile (the other 1800 are missing); pairing is on (class, race,
seed) over those 900 cells:

| Profile | Identical traces | Deaths v12 / v11 | Alive to dead / dead to alive | Mean max depth v12 / v11 |
| --- | --- | --- | --- | --- |
| normal | 816 / 900 | 279 / 279 | 3 / 3 | 2.43 / 2.42 |
| munchkin-class | 845 / 900 | 242 / 245 | 1 / 4 | 3.20 / 3.20 |

What this does and does not show:

* In **both** the normal and the class-rule configuration the v12 build executes differently from
  v11 (84 and 55 diverging traces), so the changed code is reached there; the effect on deaths,
  depth and level over those 900 cells is within a few cells and shows no regression and no gain.
* It does **not** separate 0118 from the official import (retiring 0001/0002 included): v11 to v12
  changes both at once. An ablation (0118 alone, import alone) is the only way to attribute the
  divergences.
* **Lunal-only and unrestricted (all modes on)** were not run. The class-rule arm is not the same
  as a pure Lunal arm. Those configurations remain unmeasured.
* The 900-cell pairing is half the grid; the v12 arms are complete but v11 is not.

## Disclosures

* A build from pristine `e473720ed` objects cannot run against the new `lib/gamedata`
  (`player_timed.txt` flag format), so the retirement "before" tree is the merged tree with upstream's
  Borg hunks reversed, not a pristine build.
* The comparison against pristine is therefore of the Borg hunks only; the 7 non-Borg commits are in
  both phases.
* The tracker fixture commits are not in this repository; they were fetched by SHA from
  `neo-angband-tracker`.
* Source-side status: the source fix for 0118 is a reviewed commit on a source PR; carrying it here is
  adoption, not an upstream acceptance claim. No source-tracker or official posting, no borg-rs work.
