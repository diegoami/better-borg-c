# Flow danger cache: source404 consumer carry

Owner-authorised consumer212 adopts only source PR407 commit
b71b32c152e272886cb46bb8f253e8c4f5130711, one C module (+19/-7), on actual
48-carry main e9eb2915130dac6a83b31df1f24a0cd8c2c47cef. Applied commit
257e7b473e56d6e9cf69c8dcdbc13e9039a42b5b preserves source author/history.
Source evidence fixture89326f5216148ab47a18585236678c391bb4e559 and receipt
f15794d2f2128714988596bfa036748d63a8f407 stay in the source repository.
No source repository changes, comments or approvals are made by this carry.

`borg-flow.c` exactly matches pristine e473720 before the carry. Its two writers
set `know` while danger checking was bypassed; subsequent normal flows trusted
those entries. The correction preserves bypass movement but only caches an
actual assessment. It removes the discarded enqueue evaluation in bypass modes.
No changes to source152 stair flags, source156 flee guard or patch0002 reaction
mechanism are included. Official master checked unchanged e473720 at session start.

## Product verification

Under the shared validation lock, both complete actual consumer before/after
cores pass965/965native units and5/5frontend tests. Reproduce scenarios with:

```sh
flock /tmp/angband-validation.lock python3 tools/verify-flowcache.py \
  --before-build /absolute/path/to/flowcache-before/build/native \
  --output artifacts/fc404-carry/UNIQUE-scenarios
```

The verifier reads unchanged fixture/profile/runner bytes from the pinned source
Git objects; it never runs the source-side pristine-build workflow. It links the
fixture to actual product objects, and derives partial-fix and wipe-comparison
objects using the source's exact derivation. Actual results: before19/30 (the
expected11contract failures), after30/30, spread-only26/30, enqueue-only23/30,
wipe30/30. All ordinary safe/dangerous/blocked/emergency/cache-reuse controls and
the expired-monster limit match, and RNG checks report no changes. Honest cache
entries are retained; next normal flow pays for the skipped evaluations. Counts
are fixture observations, not whole-game timing or population benefit.

All154prior fixture cases match the established matrix. Existing losdispel
interactions and the two expected-red dispel259 cases remain asserted, not
weakened. The regression runner/raw logs remain in the retained local evidence.

First fixture attempt failed before game setup because the source runner sets
cwd to its executable directory and the new layout lacked `lib`. That attempt
is retained. The final runner uses a per-variant game directory with a link to
its actual core's runtime library; no fixture, inputs or assertions changed.

## Impact and historical death

Prospective bounds are frozen in local `artifacts/fc404-carry/plan.json` before
measurement: unchanged v1 seeds11/29/47, fixed Human Warrior/default point buy,
20000turns/120wall seconds/30stall seconds per variant; one repeat of each start.
This is a small regression cohort, not a survival-effect estimate.

A separate diagnostic uses D0008's original seed1668846659 and random-birth input
and configuration, cap200000/wall600/stall30. It is an already-observed life,
not another independent prospective sample. Original C46 build/record/save/movie
identities and owner review remain immutable. Actual measurement results will
be recorded before delivery; no claim that this carry fixes every component of
D0008, establishes a designed escape, or improves population survival.
