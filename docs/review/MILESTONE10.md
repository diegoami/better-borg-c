# Milestone 10 review: the diff from impact v9 to the v10 head

Review input for [milestone 10](https://github.com/diegoami/better-borg-c/milestone/10).
This document is the map of the diff and the exact checks a reviewer can run; the review
prompt at the end is written for any model the owner chooses.

**This is not a self-review, and the two internal agent reviews in this cycle are not the
milestone review.** They were written by the implementing agent on the same GitHub account
(PR 416 findings M10-01..M10-03; PR 417 findings R10-04/R10-05). Treat everything they say,
and everything this document says, as a claim to verify.

## 1. The diff under review

| | |
| --- | --- |
| Base | tag `4.2.6-impact-v9` on runtime snapshot `33207fbee` (milestone 9) |
| Head | `4f837667a` (PR 418, current `origin/main` when this package was written) |
| Size | 65 commits, 25 merged PRs (first-parent), 662 files changed |
| Compare view | https://github.com/diegoami/better-borg-c/compare/4.2.6-impact-v9...4f837667a |
| Runtime surface | 3 commits, 4 files, +53/-3 lines at the reviewed head (+54/-3 after the M10-R-06 comment fix, section 8) - the whole gameplay change |

If the head has moved since, review the commit you actually inspected and name it; the
behaviour claims are anchored to the three `src/` commits, not to the head.

**Post-review head:** `6944d88e8` (the M10-R corrections, section 8). Against the reviewed
`4f837667a` it adds the I-002 kit (9 files), the I-003 record (1 file), the corrections themselves
and one comment line in `src/`; no behaviour changes.

A git tag cannot be a pull-request base, so the range is reviewed through the compare link
above rather than as a PR's own "Files changed" tab. Everything else (evidence, commands,
findings) is here.

```sh
git clone https://github.com/diegoami/better-borg-c.git bbc-review
cd bbc-review
git log --first-parent --oneline 4.2.6-impact-v9..4f837667a
git diff --stat 4.2.6-impact-v9..4f837667a
git diff 4.2.6-impact-v9..4f837667a -- src/          # the code that matters
```

### Where the lines are

| Area | Files | Lines | Notes |
| --- | --- | --- | --- |
| `docs/audit/c-reports/` | 532 | +49386 | 38 kit dirs: 36 restored (523 files), `necrolight-296-crash` (8), README |
| `docs/deaths/` | 71 | +19010 / -36 | D0017, D0018, D0019 collected cases + index + lessons |
| `docs/measurement/` | 18 | +12797 / -10 | unit evidence, milestone 9/10 packages, matrix summaries, #324 diagnostic |
| `patches/` | 3 | +1923 / -1867 | `series.json` (reformat + one amended entry), new `improvements.json`, README |
| `tools/` | 22 | +949 / -80 | matrix tool, verification, replay, death tooling |
| `src/` | 4 | +53 / -3 | the three units only |
| `docs/` (other) | 3 | +195 | release/install, adoption, verification |
| root files | 9 | +203 / -201 | README, AGENTS, PLAN, RULES, UPSTREAM, `session.json`, `.gitignore`, replay scripts |

## 2. What the window contains

Three runtime units and nothing else in `src/`:

| Unit | Commit | What it changes |
| --- | --- | --- |
| I-001, one-blow kill on a lone adjacent monster | `fe205198d` (PR 394) | `borg-fight-attack.c/.h` |
| I-002, heal while fleeing at survivable danger | `dfecabb59` (PR 414, receipt 415) | `borg-caution.c`, `borg-magic.c` |
| 0099 crash correction, stale-position bounds guard | `dbc2bed77` (PR 398) | `borg-magic.c`; fixture `necrolight-296-crash` |

I-003 (starting purchases, issue 410) is a **rejected negative result**, not a unit: its branch
`task/imp-003-startbuy` is pushed and nothing merged.

Everything else is governance, tooling, evidence, death review or state: PRs 379, 381, 382,
383, 384, 385, 388, 389, 391, 393, 395, 396, 397, 402, 404, 405, 407, 413, 416, 417, 418.
`IMPACT-MILESTONE10.md` lists them with what each does; the reviewer's job is to confirm that
list is complete and that none of them hides a behaviour change.

### Evidence to weigh

* `docs/measurement/IMPACT-MILESTONE10.md` - the package: units, cohort, exclusions, disclosures.
* `docs/measurement/IMPACT-IMPROVEMENT1.md`, `IMPACT-IMPROVEMENT2.md` - per-unit evidence.
* `docs/measurement/impact-v9/regression-summary.json` (75 groups / 225 cases) and
  `docs/measurement/impact-v10/regression-summary.json` (77 groups / 234 cases, `at_commit c1a80e92c`).
* `docs/audit/c-reports/README.md` - kit contents, provenance, residual dependency.
* `patches/series.json` (98 entries) and `patches/improvements.json` (I-001/I-002 records).
* `docs/deaths/D0017-collected`, `D0018-collected`, `D0019-collected`.

## 3. Claims to verify

Each is checkable from the clone unless marked otherwise. C8's byte-identity half is not.

* **C1 base and head identity.** `git rev-list -n1 4.2.6-impact-v9` is `33207fbee`; the head
  under review is `4f837667a`; the tag is annotated on the runtime snapshot, not on a package commit.
* **C2 runtime surface.** Only the three `src/` commits exist in the window, each maps to exactly
  one unit, and the code does what the unit text says. Read the 53 lines first; they are the
  milestone.
* **C3 ledger integrity.** `patches/series.json` has 98 entries before and after, same order;
  semantically only `NECROLIGHT-296` changed (a `crash_correction` block); the 3727-line diff is
  reformatting, not new units. `patches/improvements.json` is new and records I-001/I-002 as
  local improvement units, never upstream. No patch file was added or removed.
* **C4 0099 crash correction.** The defect is a read of a stale recorded position outside a
  smaller new level; the guard is `square_in_bounds` in the `square_islit` path; the fixture
  reproduces fail-before (assert abort pre-fix, segfault in the NDEBUG product) and pass-after,
  and the `lit`/`dark`/`mage-lit` controls are unchanged in both. It is attached to the existing
  ledger entry, not a new ordinal.
* **C5 matrix.** v9 tip 225 cases; `necrolight-crash` +5 = 230; `fleeheal-408` +4 = 234; the
  restored 36 groups rerun 91/91 OK with zero undeclared row differences; `fleeheal-408` 4/4 on its
  committed kit; 77 = 60 local + 17 `KIT_GROUPS`. The only row differences are the declared
  transitions (`vampire` `near-far`/`near-near`, `dispel259` `reserve`/`clear`, `knockout`
  `paralysis`).
* **C6 kit restoration.** In the restoration commit `0263951f8` itself: 36 kit dirs, 523 files,
  committed sources and logs only (no binaries, `.o`, `result.json`, tarballs), exactly 36
  `GROUPS` path substitutions with unchanged tags, modes and declared transitions *at that
  commit*, and no `.worktrees/` reference left. The window's other `GROUPS` changes are not part
  of the restoration: the milestone 9 declarations (`dispel`, `vampire`) landed in `8a9b5307f`,
  and `fleeheal-408`'s baseline repoint in the review corrections. A fresh clone reruns the 37
  committed kits without `artifacts/` (91 cases for the 36 restored groups plus the 4
  `fleeheal-408` cases).
* **C7 cohort claim.** Both units were measured on the frozen v1 cohort (Human Warrior, seeds
  11/29/47, 20k turns) against each branch's own start; 6/6 alive at cap before and after, so the
  claim is cohort-neutral, not "improves survival". Check the recorded lives, not the prose.
* **C8 provenance.** The 523 restored kit files are claimed byte-identical to the untracked
  originals (SHA-256). **Unverifiable from the repository**: the originals exist only on the
  owner's machine. Judge whether the docs are honest about that.
* **C9 I-003 rejection.** The negative result is recorded with its declared margins and the
  cohort that failed them; nothing from it was merged.
* **C10 disclosures.** The package discloses: I-001's targeted-life divergence, I-002's
  non-reproducing paired rerun, and that the matrix evidence quoted per unit is that unit's own
  merge-time run. Its one former gap, the 22 0049-era groups reading a gitignored tree, is closed
  post-tag (section 8).
* **C11 process claims.** No upstream or source-tracker posting, no Rust/borg-rs work, no v10
  tag (the only other tag in play is `4.2.6-impact-v9.1` on its release branch, outside the
  window), and each governance PR (384, 385, 388, 389, 391, 393) matches what the owner
  authorised.
* **C12 death records.** D0017-D0019 contain dossiers with real logs, owner feedback processed
  into actions, and no gameplay change.

## 4. Known limitations of this package

* The internal reviews (PR 416, PR 417) are non-independent; their findings were applied but not
  independently confirmed.
* The full 234-case matrix needs no tree outside the clone. It does need a full clone: the 17
  `KIT_GROUPS` fetch their fixtures at the ledger's evidence commits (a shallow clone is not
  enough). Say which groups you ran.
* Multi-hour `run-cases.py` kit groups and the cohort measurements are not cheap to rerun; if you
  do not rerun them, say so instead of restating their numbers.
* The package document is the implementer's account. Where it and the code disagree, the code wins.

## 5. Build and run

```sh
git clone https://github.com/diegoami/better-borg-c.git bbc-review
cd bbc-review && git checkout 4f837667a
cmake -S . -B build/native -DSUPPORT_BORG=ON -DSUPPORT_TEST_FRONTEND=ON \
      -DSUPPORT_X11_FRONTEND=ON
cmake --build build/native --parallel 8
cmake --build build/native --target allunittests --parallel 8   # matrix links the unit-test objects

# the 36 committed kits, list derived from the tool
python3 - <<'PY' > /tmp/restored.txt
import re
src = open('tools/regression-matrix.py').read()
block = src[src.index('GROUPS = ['):src.index('# Source-tracker kit groups')]
print('\n'.join(n for n, d in re.findall(
    r"^\s*\('([^']+)',\s*'(docs/audit/c-reports/[^']+)'", block, re.M)
    if n != 'necrolight-crash'))
PY
ONLY=$(awk '{printf " --only %s", $0}' /tmp/restored.txt)
flock /tmp/angband-validation.lock python3 tools/regression-matrix.py \
    --build build/native --output /tmp/review-matrix $ONLY
```

Take `/tmp/angband-validation.lock` before any matrix run; do not run two at once. The unit
gate is `cmake --build build/native --target allunittests`: expect 965/965 and 5/5.

## 6. Review prompt

Paste this into any model the owner chooses. It is deliberately model-agnostic.

```text
Review milestone 10 of diegoami/better-borg-c: the whole diff from the impact v9 baseline
(tag 4.2.6-impact-v9, snapshot 33207fbee) to the v10 head 4f837667a. READ-ONLY: do not modify,
commit, push or post anything; return findings as text.

Compare view: https://github.com/diegoami/better-borg-c/compare/4.2.6-impact-v9...4f837667a
Package: docs/measurement/IMPACT-MILESTONE10.md. Review map: docs/review/MILESTONE10.md.
This repo is a native C consumer fork of Angband with a C Borg. The cycle claims exactly three
runtime units - I-001 (fe205198d), I-002 (dfecabb59), the 0099 crash correction (dbc2bed77) -
and no new bug carry; everything else is governance, tooling, evidence, death review or state.
Two internal agent reviews exist (PR 416, PR 417) by the implementing agent on the same account.
They are NOT independent. Treat every number, every "verified" and every disclosure in the docs,
the PRs and those reviews as a hypothesis, and say which ones you checked.

Verify, in this order:
1. The runtime surface: read the 53 changed lines in src/ (borg-caution.c, borg-magic.c,
   borg-fight-attack.c/.h). Does each change do what its unit says, is the guard complete for the
   crash it claims to fix, and is there any behaviour change not covered by a unit or a test?
2. The inventory claim: `git log --first-parent --oneline 4.2.6-impact-v9..4f837667a` and
   `git diff --stat` must match the table in docs/review/MILESTONE10.md, and no merge may hide a
   src/ or runtime change. Every merge is accounted for in the package's exclusions list.
3. The ledger: patches/series.json keeps 98 entries in the same order, only NECROLIGHT-296 changed
   semantically, the rest of its diff is formatting, and patches/improvements.json correctly
   records the two improvement units as local-only. Nothing was proposed upstream.
4. The 0099 correction: does the fixture fail before and pass after for the recorded reason, is it
   attached to the existing ledger entry rather than a new ordinal, and are the controls unchanged?
5. The matrix: 225 -> 230 -> 234 cases; the restored-kit 91/91 claim and the 4 fleeheal-408 cases;
   the v10 summary (docs/measurement/impact-v10/regression-summary.json). Rerun what you can
   afford and say what you skipped. The whole 234-case run needs no tree outside the clone, but the
   KIT_GROUPS need a full clone for their evidence pins (commands in
   docs/review/MILESTONE10.md section 5).
6. The kit restoration: in commit 0263951f8, 36 dirs, 523 files, sources and logs only, 36 GROUPS
   path substitutions with unchanged tags/modes/transitions at that commit, no .worktrees/
   reference; the later fleeheal-408 kit and the 22 0049-era kits (section 8) complete the set, and
   a fresh clone reruns all 60 local groups without artifacts/.
7. The claims you cannot check from the repo: the 523-file byte-identity to untracked originals,
   and the cohort runs. Say so explicitly rather than accepting them.
8. The disclosures: is anything material missing - a behaviour change without a unit, a test whose
   failure is hidden by a declared transition, a claim stronger than its evidence, a governance
   change the owner may not have authorised?

Deliverable:
- Findings numbered M10-01.. with severity (blocking / major / minor / nit), location
  (file:line or commit), the claim, the evidence (command and observed output), and the fix.
- A verdict: approve / approve with corrections / reject, and what the corrections are.
- What you verified, what you could not verify and why, and what you did not run.
Do not post to GitHub unless the owner asks.
```

## 7. Where the verdict goes

The owner posts the review on the milestone review issue (issues/380 is the milestone 9
pattern) or attaches it to this package; the findings are then numbered `M10-01..` and applied or
recorded as not applied, exactly as milestone 9 did in PR 381. The tag `4.2.6-impact-v10` stays
unplaced until that verdict exists and the owner authorises it; as with v8 and v9 it would go on
the runtime snapshot, not on a package commit.

The milestone 10 review was posted on [issue 420](https://github.com/diegoami/better-borg-c/issues/420)
on 2026-11-10: **approve with corrections**, findings `M10-R-01..07`, no blocking or major ones.
All seven are applied in `6944d88e8`, and a same-issue re-review at `46057bc4a` returned
**approve**; see section 8. With that disposition in, the owner authorized the tag, and
`4.2.6-impact-v10` is placed on `6944d88e8` (annotated, 2026-11-10).

## 8. Post-review corrections

The corrections change the head from the `4f837667a` reviewed above to `6944d88e8`. None of them
touches runtime behaviour; the only `src/` change is the comment in M10-R-06.

| Finding | What changed |
| --- | --- |
| M10-R-01 | `IMPACT-IMPROVEMENT2.md`: the prevalence count is scoped to the working record, says only D0006-D0019 are committed, and records the turn-span recount (18/25 at the 5% boundary against the survey's 20/25). |
| M10-R-02 | `docs/audit/c-reports/fleeheal-408/` (8 baseline logs + profile) is committed and `GROUPS` repointed; `fleeheal-408` reruns 4/4. The residual `artifacts/` dependency drops to the 22 0049-era groups. |
| M10-R-03 | This map's C6 is scoped to the restoration commit; the later `GROUPS` changes are named. |
| M10-R-04 | The full run is rerun at `6944d88e8` and re-committed with `at_commit` naming the commit that holds the exact kit bytes it read (the summary file lands in the recording commit after it); the README states the working-tree relation and uses one build reference. |
| M10-R-05 | `4.2.6-impact-v9.1` (branch `release/4.2.6-impact-v9.1`) is named in the package exclusions. |
| M10-R-06 | The `borg_thrust_damage_one` comment now says per-round damage; comment only. |
| M10-R-07 | `docs/measurement/STARTBUY-410-REJECTED.md` is cherry-picked to main; no policy code merged. |

Reverified at the corrections head: `allunittests` 965/965; full matrix 77 groups / 234 cases,
`ok: true`, zero unexpected row differences against the v9 baselines, 183/234 byte-identical; a
fresh clone runs all 37 committed kits (95 cases).

## 9. Post-tag evidence: the last 22 kits

After `4.2.6-impact-v10` was placed, the 22 remaining 0049-era groups (swap, knockout,
preparation, cold-protection, rings, potion-timing, itangast, shot-path, brand, stairtrack,
acidarc, outoflight, mapwall, enlightenment, stairreturn, blowname, excavate, calllight, gloves,
detectcarry, maimfoe, recalldepth) had their `scenario.c`, `profile/borg.txt` and recorded baseline
logs committed under `docs/audit/c-reports/`, with `GROUPS` repointed. 22 groups, 319 files, about
2.2 MB.

Effect: **all 60 local fixtures are now in the repository**, and the full 234-case matrix runs from
a clean curl-clone with no gitignored `artifacts/` tree. The only clone requirement left is
history, for the 17 `KIT_GROUPS` evidence pins.

This is evidence-only: no code change, no baseline row regenerated, and the pinned v10 tag is
unaffected (it was placed on the reviewed runtime snapshot before this batch). Re-verified after
the batch: full matrix 77 groups / 234 cases, `ok: true`, zero unexpected row differences against
the v9 baselines, 183/234 byte-identical - the same numbers as the reviewed head.
