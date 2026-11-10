# Impact milestone 10: two improvement units, the 0099 crash correction and the deferred kit restoration since impact v9

Review package for [milestone 10](https://github.com/diegoami/better-borg-c/milestone/10).

Base: impact v9, tag `4.2.6-impact-v9` on runtime snapshot `33207fbee` (placed 2026-11-09 after
the milestone 9 review and its corrections). Head when this package was written: `25d1ce6a7`
(PR 415), 54 commits and 22 merges after the snapshot.

This cycle contains **no new bug carry**. Its merged units are two owner-directed **local
improvement units** (I-001, I-002; never proposed upstream, charter in PR 389) and one **crash
correction to an already-carried unit** (0099). Everything else merged in the same window is
governance, tooling, release/docs and death review. Those are listed as exclusions below so a
reviewer can account for every merge without reading any of them as a unit.

One item is **deferred, not delivered**: restoring the 36 regression-matrix kits that were never
tracked and are no longer present in `.worktrees/`. The owner deferred it to this milestone on
2026-11-10; it is not done in this package (see "Matrix status" and "Exact next work").

## The 3 units

| Unit | Consumer | Merged | Evidence / record | Verification |
| --- | --- | --- | --- | --- |
| I-001 one-blow lone-monster attack | #324 | `8a0c1ba09` (PR 394) | `e2f594461` (PR 395), `IMPACT-IMPROVEMENT1.md`, ledger `patches/improvements.json` | targeted life + matrix 225/225 + paired cohort |
| I-002 caution heals while fleeing | #408 | `861ecb2da` (PR 414) | `7485fc192` record, receipt `25d1ce6a7` (PR 415), `IMPACT-IMPROVEMENT2.md`, `patches/improvements.json` | `fleeheal-408` scenario + matrix 234/234 + paired cohort |
| 0099 crash correction | #377 (ledger 0099) | `c1fdc9b12` (PR 398), fix `dbc2bed77` | ledger baseline `17ada0591`, `patches/series.json` 0099 `crash_correction` | `necrolight-crash` fixture, 5 cases, fail-before/pass-after |

All three merge commits are on `main`. Hosted `native` and GitGuardian checks are green on each PR;
no check was weakened or skipped for any of them.

## Unit detail

### I-001: attack a lone adjacent monster one blow would kill (#324, merged `8a0c1ba09`)

Local-only, merged after its contract closed all four acceptance items (PR 394):

* **Hosted gate:** 965/965 + 5/5, tooling 136/136.
* **Targeted life** (seed 1907608237, `--random-birth`): `start.save` sha256 equals the recorded
  D0012 dossier start; notes identical through turn 5987; first divergence at 6017, where the
  improvement fires (the skip removes the retreat-scan RNG consumption); `KILL:the grey mold` at
  8576 and 36413; `turn_cap` alive at 320,000 turns against the recorded death by poison at 27,770.
* **Matrix:** 225/225 cases, zero failed groups, zero row changes, no declarations needed (the
  guard never fires in any fixture).
* **Paired cohort** v1 (Human Warrior, seeds 11/29/47, 20k turns, fixed birth; `37386feca` vs
  `8a0c1ba09`): 6/6 runs alive at cap on both; seeds 29 and 47 identical finals; seed 11 deeper
  (depth 5 / max 6 versus 4 / 5) at identical HP 72 and CL 7.

### I-002: `borg_caution()` heals while fleeing at survivable danger (#408, merged `861ecb2da`)

Local-only, merged after the owner's 2026-11-10 direction ("Fix 408") and its own contract:

* **Hosted gate:** 965/965 + 5/5 on PR 414; the tooling-only release PR 413 is also on the merged
  head, and the post-merge cohort was rerun on the merged head.
* **Scenario fixture** (`tools/fleeing-heal-scenario.c`, matrix group `fleeheal-408`, 4 cases):
  `flee-low` drives the production chooser at the recorded D0017 fatal state (Dwarf Ranger DL21,
  HP 7/230, SP 19/39, poison 485 turns, `goal.fleeing` set, recall read, empty safe grid, 9 CCW +
  Herbal Curing learned). Before build `ac0cc65c5`: rest-for-recall `R500<enter>`, `heal=0 rest=1`,
  the fixture fails its own after-contract. After build: the Herbal Curing cure is queued
  (`sequence=mac`, `heal=1 rest=0`). Fail-before / pass-after at the recorded state values, with
  three controls byte-identical across the builds.
* **Matrix:** 234/234 cases, zero failed groups. `flee-low` is marked `rows_free` as the declared
  intentional transition and pinned by `rows_must`; no other row changed.
* **Paired cohort** v1 (`ac0cc65c5` vs `dfecabb59`, product default config): 6/6 alive at cap on
  both; seeds 29/47 identical finals; seed 11 diverges at turn 4481 (up-stairs flow) with **zero
  heal/cure notes in either life** — the shift is the extra borg-RNG draw of `borg_heal`'s
  `randint0(100)` chance roll, not a spent consumable; final depth 4 / CL 6 / HP 54 versus the old
  life's depth 5 / CL 7 / HP 72, same max depth 6. Unfavourable on that one seed; at n=3 this is
  directional and reported as inconclusive.

**Disclosed contract deviation (I-002):** the recorded D0017 life is not replayable on current
main. 181 commits separate the recorded build `5cd2258dd` from `ac0cc65c5` (the evidence document
counted them as behaviour-active; this package does not re-verify that classification), and the
by-class munchkin default changes the mode for Warriors/Druids/Rangers; the measured driver
hardcodes its `borg.txt`, so a normal-mode rerun of the recorded trajectory was not possible. Both
paired runs finished `turn_cap` alive at 1.2M turns with zero heal/cure actions; the fatal state
itself is covered by the scenario fixture instead.

### 0099 crash correction (PR 398, fix `dbc2bed77`)

The carried `necrolight-296` patch (0099) added the game's lit-square penalty through
`square_islit(cave, borg.c)`. `borg.c` is refreshed by `borg_update_map()`, so on the first think
after a level change it still holds the previous level's position; descending to a smaller level
(dungeon 176x57 -> town 66x22, stale `borg.c` = (117,47)) puts that position outside the new
square array. `square_islit()` bounds-asserts, but the product compiles asserts out, so
`square_light()` read out of bounds — the borg-rs lane's reported SIGSEGV at the first town return
(their issue 21).

Fix: `square_in_bounds(cave, borg.c) &&` before the lit test; an out-of-bounds recorded position is
treated as unlit. Fixture `docs/audit/c-reports/necrolight-296-crash/` (matrix group
`necrolight-crash`, 5 cases): `stale-town` (the recorded geometry), `stale-far` (deterministic
anchor) and the in-bounds controls `lit` / `dark` / `mage-lit` that lock 0099's behaviour (+25 lit,
+0 dark, +0 non-Necromancer caster). Fail-before: the stale modes abort on the `square_in_bounds`
assertion in `square_islit` (cave-square.c:722) pre-fix, which is the recorded segfault in the
NDEBUG product; pass-after: stale modes read as unlit, controls unchanged. This is a correction to
an existing unit, not a new ledger ordinal.

## Matrix status at the v10 head, and the deferred kit restoration

The committed matrix records are the v9 tip run (`docs/measurement/impact-v9/regression-summary.json`,
75 groups / 225 cases, `ok: true`, `at_commit: 33207fbee`) and the per-PR runs above:

* v9 tip: 225 cases.
* after the 0099 crash correction (PR 398): +5 (`necrolight-crash`) = 230.
* after I-002 (PR 414): +4 (`fleeheal-408`) = 234, the run recorded in `IMPACT-IMPROVEMENT2.md`.

**The full matrix cannot be rerun from a clean checkout.** 36 of the 60 `GROUPS` entries point at
fixtures under `.worktrees/<carry>/artifacts/...`, which is gitignored; those kits were untracked,
are not on the `task/carry-*` branches, and were removed after the 2026-11-09 v9 review with no
recorded cleanup. Their expected rows and log hashes survive in the v9 summary. The remaining
baseline directories under `artifacts/` are generated logs and are also absent from a clean
checkout by design.

Owner decision 2026-11-10 (checkpoint 1): do not rebuild the 36 kits now; restore them in this
milestone by committing each kit under `docs/audit/c-reports/<group>/`, verifying it reproduces the
v9 rows, and pointing `tools/regression-matrix.py` at the committed paths. Two kits are already
committed in that pattern (`necrolight-296-crash`, `spasticscore-147-product`). **This is not done
in this package** and is the first item of the exact next work.

## Frozen v1 cohort: both units cohort-neutral on survival

Both units were measured on the frozen cohort v1 (Human Warrior, seeds 11/29/47, 20k turns, fixed
birth) against the build each branch started from. Both are 6/6 alive at cap before and after, so
no survival regression was observed; the two progress differences are RNG-shifted trajectories
(I-001 seed 11 deeper; I-002 seed 11 shallower with no consumable spent). Three fixed seeds are not
statistics and no population claim is made in either direction. The frozen cohort file itself is
unchanged this cycle.

## Exclusions and pending items (checked, not counted)

* **I-003 starting purchases (#410): rejected by its own declared margins** and recorded as a
  negative result, not a unit. Policy v1 deadlocked buy/sell in town (median max-depth 5 -> 3);
  v2 fixed the loop but failed cohort 2's margins (4/20 alive->dead losses and 7/20 max-depth
  losses above the declared bounds; three new CL1 deaths with the starting dagger, the predicted
  early-AC cost). Branch `task/imp-003-startbuy` is pushed; nothing merged.
* **Death reviews D0017, D0018, D0019** (PR 404, 402, 407): dossier, evaluation and redesign
  lessons only; no runtime change.
* **Governance/tooling/docs:** 381 (m9 corrections), 382 (m9 state), 383 (v9 tag record), 384
  (borg-rs proposal path), 385 (non-carried review rule), 388 (#324 diagnostic evidence and design
  lesson 1), 389 (improvement charter), 391 (issue claim convention), 393 (remove the accidentally
  committed `.worktrees` symlink), 395 (I-001 measurement record), 396 (replay divergence stop and
  watchdog limits), 397 (README), 405 (replay/branch directory naming), 413 (release packaging).
  None changes borg or game behaviour.
* **Not attempted / not claimed:** any new bug carry (none was ready in this window); a Rust or
  borg-rs change; an official Angband interaction; a survival or progress claim for either
  improvement.

## Disclosures

* I-001's targeted life diverges from the recorded life at turn 6017 by design; the recorded loop
  after that point does not occur in it.
* I-002's paired targeted rerun could not reproduce the recorded normal-mode life on current main
  (contract deviation above). Its live benefit rests on the fixture and on the cohort result, which
  is directional at n=3.
* The matrix evidence quoted per unit is the run recorded at that unit's own merge time; only the
  v9-tip summary is a committed machine-readable full run for this base, and it predates the two
  post-v9 groups. The gap is the deferred kit restoration below, not a hidden failure: each group
  added after v9 was run in full on its PR and recorded there.
* 0099 is counted once in the ledger; the crash correction is attached to that entry
  (`patches/series.json`). No entry or patch file is added: `patches/series.json` still holds its
  98 patch entries and `patches/` its 98 patch files, while the prose ordinals in
  `patches/README.md` reach "ninetieth ... ninety-ninth" for the same units. This correction
  changes neither count.

## Review

Per the owner's standing instruction, independent/external review is deferred to milestones and the
owner launches any reviewer they choose. This package is the review input. The review performed on
this pull request is an internal agent review of the package's own claims and is not represented as
the external review; its verdict and any corrections are recorded on the PR and applied here before
merge.

## Exact next work

1. Restore the 36 `.worktrees` kits under `docs/audit/c-reports/<group>/`, verify each reproduces
   its v9 rows, and point `tools/regression-matrix.py` at the committed paths (owner deferral to
   milestone 10).
2. Create the milestone 10 review issue and let the owner launch the reviewer.
3. Do not place a v10 tag until that review returns a verdict and the owner authorizes it; as with
   v8 and v9, the tag would go on the runtime snapshot, not on this package commit.
