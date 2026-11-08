# Glowtrace Floors-branch carry: verified product scenario, ready for adoption

Consumer [224](https://github.com/diegoami/better-borg-c/issues/224),
canonical source
[213](https://github.com/diegoami/neo-angband-tracker/issues/213)
(glowtrace-213). Fix applied as
`6c00db351c3edaabd708294bd9b702b07f66cb4c` (import of source PR411-head
`da9934216eb15d421220050b374c72b65b9cd680`, patch
`patches/0050-glowtrace-floors-branch.patch`).

## Defect

`borg_update_map()`'s Floors branch is dead: the 2023 reorg
mistranslated the original borg's `FEAT_FLOOR` case as `FEAT_NONE`, so
the branch's dark/glow marking never executes — a transcription slip
carried by upstream master too. The correction restores the
`FEAT_FLOOR` condition and reads the glow state via `square_islit()` —
the grid's permanent-glow flag matching the original `CAVE_GLOW` test
(the transcribed `g.lighting == LIGHTING_LIT` would have been wrong
even if reached: `LIGHTING_LIT` is `map_info`'s default for grids whose
lighting is not otherwise established, so remembered dark floors would
have been marked glowing); the unreachable torch-lit sub-branch is
dropped. Behavior-active (same family as mapwall-212): the corrected
branch flags permanently-glowing floor grids `BORG_GLOW` and the
flow-toward-light consumer sees them again; the unlit-Borg defense
checks and the rest-site ladder read the same flags. No survival or
encounter-frequency claim.

## Pins and layered provenance

Before build: retained tree `../glowtrace-before` @ `2f4d62e4f` =
current origin/main including the interleaved flowcache carry
(FLOWCACHE-404, patch 0049, borg-flow.c — merged by the recording lane
while this carry was prepared; 59 src/lib diff lines since the
recalldepth builds, all outside borg-update.c). Normal and ASan cores,
gate recorded at that commit. `borg-update.c` already carries
0039/0046, so the verifier proves that the source diff applied to the
before module equals the product module; the applied commit's diff body
is byte-identical to the source commit's diff. The source evidence
fixture at `5e6f2ddb5` is used unchanged; the receipt chain is checked
in the verifier as pin identity — the runtime fixtures
(scenario.c/borg.txt/profile) are byte-identical between the run pin
`5edc188e` and the evidence head (the head adds the receipt/replay
artifacts on top).

## Verified results (`artifacts/gt213/scenarios`, 2026-11-08)

- `main` (production `borg_update()` once, glowing arena, perm walls,
  no monsters): normal-before 0/1 — `distant_glow=0 near_glow=0
  wall_glow=0` (the `require(near)` fails); normal-after 1/1 —
  `distant_glow=1 near_glow=1 wall_glow=0`, flow-toward-light
  `glow_n=484`.
- **Cross-repo state match:** both phases' recorded STATE rows equal
  the source evidence kit's recorded values exactly, including the grid
  info bitfields (`info33` 41→43, `info1211` 57→59, `marked`/`lit`/
  `pcmem` 1/1/1 in both) — the consumer reproduction matches the source
  run value for value.
- asan-before/asan-after mirror the normal phases; the sanitized runs
  report the pre-existing init-time `borg_sort_comp_hook` overflow
  (source finding #399, separately filed) in every phase — expected, and
  asserted as such rather than suppressed.
- `result.json` records `verified: true` with all commands and hashes.

Native gate on this core at the fix commit: **965/965 unit + 5/5
frontend** numerically read; tooling **97/97** (main's tooling set grew
again with the interleaved lanes' additions). Regression matrix
(`artifacts/gt213-carry/regression.py`, local-only): **154 prior native
fixture cases** — 151 from the forty-eighth tally plus the three
recalldepth-310 cases. Results and any asserted log changes are
recorded in `regressions/result.json` and below.

## Scope and limits

Bounded map-update scenario with one glowing-arena case. It proves the
branch restoration and its consumers, not a gameplay frequency or
survival claim. Because the fix is behavior-active, the frozen v1
cohort is watched for divergence rather than assumed neutral.

## Exact next work

1. PR from `task/carry-glowtrace`, agent evidence review plus required
   hosted checks, then normal merge.
2. On merged main: prepare the measurement build
   (`tools/measure-native.py prepare --observe`), run frozen v1 seeds
   11/29/47, cap 20000, wall 120, stall 30, and compare against the
   forty-eighth lineage run — divergence expected to be possible and
   recorded as observed.
3. Mark 224 carried/open+patch-active; receipts on issue 224, source
   213 and checkpoint 1; evidence archive under `artifacts/gt213-carry/`.
4. Pending owner decision elsewhere: dontreact-14 vs carried patch 0002
   (mechanism replacement).
