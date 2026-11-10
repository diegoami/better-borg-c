# source73: Lunal-mode take skips the items it marked bad (patch 0101)

Consumer adoption of [source 73](https://github.com/diegoami/neo-angband-tracker/issues/73)
(CBUG-0057), fix `45423c1c8` (source PR 515, evidence PR 514), kit
`docs/audit/c-reports/lunaltake-73` at fixture commit `aed37ebbb`.

## Defect

`borg_flow_take_lunal()` classifies every visible item with `item_bad`, writing its "Lunal Item"
notes, but the result was never read: every entry that reached the take step became a target. The
borg walked to and picked up items it had just decided were not worth taking - turns and pack space
spent on junk, including in the Lunal/munchkin scumming path.

## Fix

Skip the entry when the classification says bad, before the grid is chosen:

```c
/* Skip items the Borg does not want */
if (item_bad)
    continue;
```

Source fix `45423c1c8` -> applied `e14eb464a` (`cherry-pick -x`); patch
`patches/0101-lunaltake-skip-bad.patch`; scope `src/borg/borg-flow-take.c` only.

## Verification

Before commit `c54393aa6`, tip `e14eb464a`, kit unchanged except the two documented profile
adaptations below (`tools/verify-lunaltake73.py`). Native gates green at the before commit and the
tip (965/965 unit, 5/5 frontend); byte-wise provenance; `src`/`lib`/build scope is the one file.

| Mode | Before | After |
| --- | --- | --- |
| `dagger` | **fails** 0/1: a visible Dagger the classification marks bad is still walked to (`rc=1`, `walks_to_item=1`) | passes 1/1: it is skipped (`rc=0`, `walks_to_item=0`) |
| `gold` | passes, control: gold is still taken | passes, **byte-identical** log |

### Fixture adaptations (disclosed)

1. **Broken source profile.** The evidence kit's `profile/borg.txt` (and its top-level `borg.txt`)
   is a one-line git error, `fatal: invalid object name 'origin/task/cfghang-141-evidence'` - the
   source lane committed an error message where the profile belongs, so its run used defaults. The
   product kit uses the standard Borg kit profile.
2. **Product munchkin-by-class override.** The product enables `borg_munchkin_start` for Warrior,
   Druid and Ranger by class (owner change PR 302), and in that mode every item with value >= 1 is
   "good", so the fixture's Dagger would be taken regardless of the fix. The profile therefore sets
   `borg_munchkin_by_class = FALSE`, which keeps the classification under test. Both phases use the
   same profile, so the flip measures the fix, not the profile.

Matrix group `lunaltake-73` (2 cases) uses the product `after-*.log` rows as its baseline and
passes 2/2. Tooling: 144 tests.

## Ledger and credit

`patches/series.json` `LUNALTAKE-73`, patch-active; consumer issue #429. Source defect, fix and
native fixture by Diego Amicabile (native proposal/evidence); carried unchanged apart from the two
disclosed profile adaptations.


## Correction: the skip applies to Lunal mode only (2026-11-10)

The carried source fix skipped **every** item marked bad, in both modes that call
`borg_flow_take_lunal()`. The frozen v1 cohort then moved: seeds 11/29/47 all finished
**2-3 levels shallower** and two of them spent much of the last third of the run oscillating
dive/climb at shallow depth (`# Munchkin Mode.  Power Climb (needing to sell).`,
`# Fleeing level. Munchkin Mode.`). In munchkin mode the borg deliberately collects what it can
sell - the value test already clears `item_bad` for saleable items - so the skip mostly removed
the items that kept the take flow busy; with nothing to take, control fell into the climb branch
and the loop followed. Selling is disabled in the cohort (`birth_no_selling`), so the climb could
never pay off.

The correction keeps the skip on the Lunal scumming path the defect was reported for and leaves
munchkin-mode collection alone: `if (item_bad && !borg_cfg[BORG_MUNCHKIN_START]) continue;`
(patch `0101a`, commit `fea1e39c2`).

### Mode-attribution (owner rule 2026-11-10)

| Configuration | Frozen v1 cohort (seeds 11/29/47, 20k turns) |
| --- | --- |
| **All modes** (merged 0101, ungated) | end depth **1 / 4 / 2** (pre-carry 4 / 6 / 5); traces diverge |
| **Lunal only** (non-munchkin, `0101a`) | end depth **4 / 6 / 5**; traces **byte-identical** to the pre-carry run |
| **Munchkin only** (complement, measured) | end depth **1 / 4 / 2**; traces **byte-identical to the all-modes run**, so the whole shift is attributable to munchkin mode |
| **Normal only** | unreachable by construction: the function is called only from the Lunal and Munchkin thinkers (`borg-think-dungeon.c` lines 224 and 584); normal exploration uses `borg_flow_take()` |

The two configurations partition the effect exactly: Lunal-only reproduces the pre-carry traces, munchkin-only reproduces the all-modes traces. All three seeds reach max depth 6 in every run; survival is 3/3 alive at cap in all configurations.
The kit still passes in both phases with munchkin off (the Lunal behaviour it was written for),
and its gold control is byte-identical.
