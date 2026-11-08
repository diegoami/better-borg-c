# Paused adoption (owner instruction 2026-11-08): reverse-flow pair, verified, not merged

The owner stopped the carry loop and paused adoption while this pair was verified but not yet
packaged. Nothing here is merged, no PR is open, no issue is labelled carried. Branch
`task/carry-revflow` (cherry-picks `dafc4bd45` and `e66b1dca2` on `origin/main` `afdd7921d`) holds the
work; resume by opening a PR from it after the steps below.

| patch (unmerged) | consumer | source | applied | source commit |
| --- | --- | --- | --- | --- |
| 0064 spastic | [268](https://github.com/diegoami/better-borg-c/issues/268) | [146](https://github.com/diegoami/neo-angband-tracker/issues/146) | `dafc4bd45` | `f97311e5d52de4dda8d75058114c52acbdac2674` |
| 0065 glyphflow | [269](https://github.com/diegoami/better-borg-c/issues/269) | [345](https://github.com/diegoami/neo-angband-tracker/issues/345) | `e66b1dca2` | `f618381294dcf5bff1f0bc95f0fbe259412a53b9` |

## What was verified

Unchanged source fixtures, each against its own before-build (rows equal the source rows value for value):
spastic `middle` and `corner` 0/1 to 1/1 (`moved` 0 to 1), `far` control byte-identical; glyphflow
`center` 0/1 to 1/1 (`progress` 0 to 1), `offcenter` control byte-identical. Native gate on the tip
`e66b1dca2`: 965/965 unit + 5/5 frontend. Verifiers: `tools/verify-spastic.py`, `tools/verify-glyphflow.py`
(artifacts under `artifacts/spastic`, `artifacts/glyphflow`, ignored by Git, kept in the `carry-work` worktree).

## Frozen v1 cohort (behaviour-active), measured on the pair as a unit

Before `afdd7921d`, after `e66b1dca2`; seeds 11/29/47, cap 20000. All three traces diverge.
Seed 11 alive at the cap both; seed 29 alive both (level 5 HP 58 before, level 3 HP 49 after); seed 47
**dies to a cave spider at turn 11780 before and is alive at the cap after**. Three seeds are not statistics;
no claim either way. Archive `artifacts/rf-measurement.tar.gz` in the `measure-rf` worktree (sha256
`7e3b93430879fbf7c759f3b998c49b4bb3d7a73c3d73e445f519f72517870119`, 55373794 bytes, 95 members; ignored by Git).

## Not done (to resume)

1. Series entries, README ledger lines and measurement documents for 0064/0065 (use
   `docs/measurement/CONFIG-PARSER.md` as the stacked-pair template); fold the merge commit of the
   milestone 6 package into nothing (already recorded).
2. Commit patch files `patches/0064-spastic-reverse-flow-unoptimized.patch` and
   `patches/0065-glyph-reverse-flow-unoptimized.patch` (generated, present in the worktree).
3. PR, hosted checks, merge, labels, source receipts, checkpoint.
4. Also ready and unstarted: swapacid-199. Not carriable: prepreason-234 (fixture pending), staircycle-403
   (awaits 204), tapunlife-249 (masked).
5. Milestone 6 review: the package (#273, PR 272) exists but external review has not happened; the tag
   `4.2.6-impact-v6` has not been created (owner decision after review).
