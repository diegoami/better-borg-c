# Milestone 11 review: the diff from impact v10 to the v11 head

Review input for [milestone 11](https://github.com/diegoami/better-borg-c/milestone/11).
This document maps the diff and gives the exact checks a reviewer can run; the prompt at the end
is written for any model the owner chooses.

**This is not a self-review.** Everything here, and everything in the unit docs, the adoption
issues and the PR bodies, is the implementer's account. Treat it as a set of claims to verify.

**Revised after the review.** The independent review on issue 471 returned approve with
corrections (F1-F5). This map and the package were corrected accordingly; section 7 records the
dispositions. The runtime snapshot under review is unchanged (`39268ca8a`).

## 1. The diff under review

| | |
| --- | --- |
| Base | tag `4.2.6-impact-v10` on runtime snapshot `6944d88e8` (tag object `fa0f6639`) |
| Head | `39268ca8a` (PR 470, current `origin/main` when this package was written) |
| Size | 28 first-parent merges, 610 files, +77973/-171 |
| Compare view | https://github.com/diegoami/better-borg-c/compare/4.2.6-impact-v10...39268ca8a |
| Runtime surface | 18 units, 11 files, **+102/-75 lines** - the whole gameplay change |

If the head has moved since, review the commit you actually inspected and name it; the behaviour
claims are anchored to the 20 `src/` commits, not to the head.

```sh
git clone https://github.com/diegoami/better-borg-c.git bbc-review
cd bbc-review
git log --first-parent --oneline 4.2.6-impact-v10..39268ca8a
git diff --stat 4.2.6-impact-v10..39268ca8a
git log --oneline 4.2.6-impact-v10..39268ca8a -- src/    # the code that matters
```

### Where the lines are

| Area | Files | Lines | Notes |
| --- | --- | --- | --- |
| `docs/audit/c-reports/` | 535 | +71417 | 18 new kit dirs (sources, profiles, before/after logs, source receipts) |
| `tools/` | 19 | +3121/-29 | one consumer verifier per unit + their test matrix |
| `patches/` | 21 | +1968/-1 | 19 `.patch` copies, `series.json` entries, README paragraphs |
| `docs/measurement/` | 20 | +1227/-38 | 18 unit docs, this milestone package, the v11 matrix summary |
| `src/` | 11 | +102/-75 | the 18 units only |
| root/other | 3 | +80/-13 | `session.json` state, AGENTS rule text |

## 2. What the window contains

Eighteen runtime units, one per PR, and nothing else in `src/`:

| Unit | Source | PR / merge | File(s) |
| --- | --- | --- | --- |
| 0100 STAIRPHASE-34 | 34 | 428 / `c54393aa6` | `borg-escape.c` |
| 0101 LUNALTAKE-73 + 0101a | 73 | 430 / `c16c56405`, 433/434 / `9ca986616` | `borg-flow-take.c` |
| 0102 FLOWKILLHALL-98 | 98 | 436 / `281e3dd8d` | `borg-flow-kill.c` |
| 0103 HITCHANCE-63 | 63 | 438 / `d624c29db` | `borg-danger.c` |
| 0104 TAKESTAIR-71 | 71 | 441 / `4002d0308` | `borg-flow-take.c` |
| 0105 RESTPREP-108 | 108 | 444 / `423b9fc87` | `borg.h` |
| 0106 PREPREASON-234 | 234 | 447 / `293e153ec` | `borg-think-dungeon-util.c` |
| 0107 LOSECON-61 | 61 | 449 / `0b5889caf` | `borg-danger.c` |
| 0108 CRUSHV2-66 | 66 | 451 / `b663b28b0` | `borg-danger.c` |
| 0109 GRANITESIM-68 | 68 | 453 / `5f7597bb7` | `borg-danger.c` |
| 0110 SCOOTIDX-100 | 100 | 455 / `4ab32de77` | `borg-flow-kill.c` |
| 0111 EMPTYSLOT-60 | 60 | 458 / `3e7732edd` | `borg-inventory.c` |
| 0112 EATHURT-80 | 80 | 460 / `536534d2d` | `borg-item-use.c` |
| 0113 RINGSLOT-86 | 86 | 463 / `4a58046f8` | `borg-item-wear.c` |
| 0114 SWAPTRIAL-31 | 31 | 465 / `b77f5ae00` | `borg-store-buy.c` |
| 0115 HOMESKIP-29 | 29 | 467 / `2d0840571` | `borg-store-buy.c` |
| 0116 SELLCHARGES-132 | 132 | 469 / `858774476` | `borg-store-sell.c` |
| 0117 EGOSELL-133 | 133 | 470 / `39268ca8a` | `borg-store-sell.c` |

Non-runtime merges in the window, which the reviewer should confirm hide no `src/` change: the
milestone-10 tail (422 review corrections, 423 wording, 424 tag record, 425 22-kit commit), the
v11 handover (439) and state packages (442, 445, 456), plus the per-unit evidence/kit commits
inside each carry PR.

### Evidence to weigh

* `docs/measurement/IMPACT-MILESTONE11.md` - the package: units, matrix, disclosures, tag gate.
* `docs/measurement/<UNIT>.md` and `tools/verify-<unit>.py` - per-unit proof, including the
  byte-wise layering assertion and the before/after phases of the unchanged kit.
* `patches/series.json` (116 entries; the last 18 are the units above) and the 19 `.patch` files.
* `docs/measurement/impact-v11/regression-summary.json` - 95 groups / 290 cases at the head.
* The 18 adoption issues (one per unit), each with a claim and a completion receipt.

## 3. Claims to verify

Each is checkable from the clone unless marked otherwise.

* **C1 base and head identity.** `git rev-list -n1 4.2.6-impact-v10` is `6944d88e8`; the head is
  `39268ca8a`; 28 first-parent merges; 610 files / +77973/-171.
* **C2 runtime surface.** The behavioural runtime surface is the 18 units, 11 files, +102/-75.
  One governance merge also edits `src/`: PR 422 (`46057bc4a`) changes a comment in
  `borg-fight-attack.h` (+2/-1, no behaviour). `git log 4.2.6-impact-v10..HEAD -- src/` otherwise
  shows only the carry commits plus the superseded 0101 attempt (`fea1e39c2`), which is
  cumulative-reverted by `1ae61726a`.
* **C3 ledger integrity.** `patches/series.json` gains exactly 18 entries in unit order, each with
  `consumer_issue`, `source_issue`, `source_head`, `source_commits`, `applied_commits`, `patch`,
  `patch_active: true`, `evidence_ref`, `verification` and a status line; 116 entries and 117
  patch files in total (0101a is the extra file, a correction of 0101, not an ordinal).
* **C4 carry fidelity.** For each unit, the consumer verifier asserts that the source diff applied
  to the before module equals the product module, the changed scope is the one file, the applied
  commit is in `HEAD`, and the native gate at the before and at the tip is the same build. Read
  `tools/verify-<unit>.py`; the mechanism is identical for all 18.
* **C5 kit provenance.** Each kit `scenario.c` and `profile/borg.txt` is byte-identical to the
  source evidence branch, with one disclosed exception: `lunaltake-73/scenario.c` adds the
  `dagger-munchkin` mode (sets `borg.munchkin_mode` and a third expectation), documented in
  `docs/measurement/LUNALTAKE-73.md` and PR 434. The verifier re-derives the kit from the
  committed consumer pin. The source receipt is carried unchanged and is the source lane's, not
  the consumer's, run.
* **C6 matrix.** 95 groups / 290 cases, `ok: true`, no failed group; 237/250 compared cases
  byte-identical; the 13 differences are in `dispel`, `dispel259`, `fleeheal-408`, `knockout`,
  `vampire` (pre-existing declared transitions) plus `preparation`, whose two logs print
  `no_rest_prep=50000` instead of `-15536` (0105) with identical decisions.
* **C7 mode attribution.** No per-mode arm was run. Each unit records its per-mode effect as
  **not measured**, not neutral; 0101a is the only gated unit and its two-mode fixture proves the
  runtime gate. Two single-configuration (unrestricted, all modes) frozen-v1 cohort runs exist and
  are disclosed: 0100 is byte-identical before/after (neutral in that configuration, issue #427),
  0101 diverged 2-3 levels shallower and motivated 0101a (issue #429). Confirm no unit claims a
  per-mode or survival effect it did not measure.
* **C8 the 0101 correction.** The first gate used `borg_cfg[BORG_MUNCHKIN_START]` (forced true for
  Warrior/Druid/Ranger) and was inert for those classes everywhere; `1ae61726a` gates on
  `borg.munchkin_mode` and the fixture runs the same marked-bad Dagger with the mode off (skipped)
  and on (taken). The unrestricted cohort regression is disclosed in the unit doc.
* **C9 process claims.** No upstream or source-tracker posting and no Rust/borg-rs work. The v11
  tag was not placed when this map was written; it was placed afterwards on the runtime snapshot
  `39268ca8a` under explicit owner authorization (tag object `443ba5c4`), as section 7 records.
* **C10 unit gate.** Every merge ran the native gate 965/965 unit and 5/5 frontend (CI), and each
  verifier's before/tip gates are recorded in its `result.json` where one is committed. The four
  earliest kits (0100-0103) commit their before/after logs instead, which are the matrix baselines;
  the asymmetry is historical and nothing is missing from them.

## 4. Known limitations of this package

* No per-mode arm was run in this cycle; one unrestricted/default cohort was run for 0100
  (neutral, byte-identical) and one for the ungated 0101 (divergent, which motivated 0101a). The
  explicit-arm batch is owed to borg-zoo issue 54.
* Several source PRs are still open on the source tracker (`status: in-review`); carrying the
  released commit is adoption, not upstream acceptance.
* Multi-hour kit runs were not rerun for this package beyond the matrix; if you do not rerun them,
  say so instead of restating their numbers.
* The package is the implementer's account. Where it and the code disagree, the code wins.

## 5. Build and run

```sh
git clone https://github.com/diegoami/better-borg-c.git bbc-review
cd bbc-review && git checkout 39268ca8a
cmake -S . -B build/native -DSUPPORT_BORG=ON -DSUPPORT_TEST_FRONTEND=ON \
      -DSUPPORT_X11_FRONTEND=ON
cmake --build build/native --parallel 8
cmake --build build/native --target allunittests --parallel 8   # 965/965 unit + 5/5 frontend

flock /tmp/angband-validation.lock python3 tools/regression-matrix.py \
    --build build/native --output /tmp/review-matrix
```

Take `/tmp/angband-validation.lock` before any matrix run; do not run two at once. The full matrix
needs a full clone (the `KIT_GROUPS` fetch fixtures at the ledger evidence commits). The expected
summary is `docs/measurement/impact-v11/regression-summary.json`.

## 6. Review prompt

Paste this into any model the owner chooses. It is deliberately model-agnostic.

```text
Review milestone 11 of diegoami/better-borg-c: the whole diff from the impact v10 baseline
(tag 4.2.6-impact-v10, snapshot 6944d88e8) to the v11 head 39268ca8a. READ-ONLY: do not modify,
commit, push or post anything; return findings as text.

Compare view: https://github.com/diegoami/better-borg-c/compare/4.2.6-impact-v10...39268ca8a
Package: docs/measurement/IMPACT-MILESTONE11.md. Review map: docs/review/MILESTONE11.md.
This repo is a native C consumer fork of Angband with a C Borg. The cycle claims exactly 18
runtime units (18 adoption PRs, 19 patch files because 0101a is a correction of 0101) and no other
src/ change; everything else is kits, tools, evidence, state or handover. There is no independent
review yet: the implementer wrote the docs, the PRs and this map, so treat every number and every
"verified" as a hypothesis, and say which ones you checked.

Verify, in this order:
1. The runtime surface: read the 102 added and 75 removed lines in src/ (11 files). Does each unit
   do what its doc says, is the change minimal, and is there any behaviour change not covered by a
   unit or a fixture? Pay particular attention to 0101a (the mode gate), 0105 (struct field width)
   and 0103/0107/0108/0109 (the four danger-model changes, which compound).
2. The inventory claim: `git log --first-parent --oneline 4.2.6-impact-v10..39268ca8a` and
   `git diff --stat` must match the tables in the package, and no merge may hide a src/ change.
3. The ledger: 18 new entries in order with the fields listed in C3; 116 entries / 117 patch files;
   every unit `patch-active`; no entry claims upstream acceptance.
4. Per-unit fidelity: open two or three verifiers and check the layering assertion, the scope
   assertion, the before/tip gate assertions and the control byte-identity; then check whether the
   committed kit logs match what the verifier's result.json says.
5. The matrix: 95 groups / 290 cases, ok, 237/250 byte-identical; are the 13 byte differences
   exactly the declared six groups, and is `preparation` explained by 0105's timer value?
6. The honesty of the mode claims: every unit says its per-mode effect is NOT measured. Confirm no
   doc, PR or commit message claims a survival or per-mode benefit that was not measured.
7. The 0101/0101a story: does `1ae61726a` really supersede `fea1e39c2`, is the gate on the runtime
   mode, and does the fixture prove the branch executes in both configurations?
8. Process: no upstream/source-tracker posting, no Rust work, no v11 tag.

Report: verdict (approve / approve with corrections / reject), numbered findings with file:line or
command evidence, anything the package overstates, and the checks you could not run.
```

## 7. Post-review corrections

The review on issue 471 (verdict: approve with corrections) was produced at `39268ca8a` and its
findings are dispositioned here. None of them changes runtime code; the reviewed snapshot stays
`39268ca8a`.

| Finding | Disposition | Where |
| --- | --- | --- |
| F1 `0101a` patch does not apply (context from the superseded `fea1e39c2`) | **fixed**: patch regenerated against the post-0101 state; replaying 0100-0117 from `4.2.6-impact-v10` applies every patch and reproduces the head `src/` byte for byte | `patches/0101a-lunaltake-mode-gate.patch`, `patches/series.json` |
| F2 "no cohort measurement" is false | **fixed**: the two single-configuration runs are disclosed (0100 neutral, 0101 divergent) | package "What is not measured", C7 |
| F3 "only the 18 units touch `src/`" is false | **fixed**: PR 422's comment-only `borg-fight-attack.h` edit is named | package "Window", C2 |
| F4 0100 has no mode-attribution record | **fixed**: attribution section and ledger note added | `docs/measurement/STAIRPHASE-34.md`, ledger `STAIRPHASE-34` |
| F5 C5's kit-provenance rule has an unstated exception | **fixed**: the `lunaltake-73/scenario.c` `dagger-munchkin` adaptation is named | C5 |
| Minor: runtime surface says +101/-73 | **fixed**: +102/-75 | package "Window" |
| Minor: four kits (not five) lack `result.json`: 0100-0103 | **recorded**: C10 now explains that those kits commit their before/after logs, which the matrix compares; the other 14 commit `result.json` | C10 |

The review's out-of-window observations are recorded in `session.json`: official
`angband/angband` master is `42cd156ac9f9`, tracking is overdue for a deliberate
upstream-integration pass, and the trial-merge conflict in `borg-item-wear.c` reproduces at the
v10 baseline, so it is pre-existing debt rather than a v11 regression.
