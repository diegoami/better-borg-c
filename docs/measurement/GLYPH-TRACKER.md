# Glyph tracker carry: verification in progress

Owner-requested stop/handover, 2026-11-06. Consumer [48](https://github.com/diegoami/better-borg-c/issues/48), canonical source [118](https://github.com/diegoami/neo-angband-tracker/issues/118). **Not merged, not yet carried, product scenario unverified.**

## Pins and priority

Main is `19870e97d89afa4b302bdd9d27337ed617c97554`, containing nine verified carries. Its last runtime measurement pin is `cf53f9b195d297f9f8b1fb61df3b6c1aff7311c6`; wider-window PR47 changes documentation/evidence. Official Angband master was checked this session and remains immutable baseline `e473720ed88a0f0c7ca66815cef3000eb4a38bc3`.

This high-priority memory-safety defect pre-empted the Enlightenment source81 candidate. Source evidence demonstrates a real failed Rune scroll message making the tracked glyph count negative, followed by a later creation writing before the heap arrays. Import source PR283 commit `ec172531ec38fdd3ac2783d21e3faf6dc1e2b3f3`, cherry-picked with provenance as `40b002da088ac48e7c1322aca2159e22c593fd73`. Source195 is consolidated into118. The fixed message module SHA256 is `3189a4b646b8f7db4df82c88302acba015a4333332c995b8f367f7062cbafd69`.

Unchanged fixture/profile pin `f1f53106526412cfe44fa01c73d00e7dbf4dbeed`, path `docs/audit/c-reports/CBUG-0102/`; source evidence head `fb2e547397c85855be53ba1bf80eeb413a96f125`, source PR284. Credit: borg-rs lead, Diego native validation/proposal. Do not modify the independent source worktree.

## Actual product attempt and unresolved failure

Task worktree `.worktrees/glyph-tracker`, branch `task/carry-glyph-tracker`. At applied commit40b002da the normal native gate passed **965/965 units and5/5 frontend**, recorded in `artifacts/native/result.json`; full ASan core/helper build also completed. Neither proves the scenario passes. Tooling tests and prior60 native fixture cases have not been run for this carry.

`tools/verify-glyph-tracker.py` is unfinished. Its first run exited1 at the assertion requiring the corrected normal `stairs` case to pass. All12 processes were captured before assertion failure; `artifacts/glyph/scenarios/result.json` correctly says `verified:false`. Do not delete/overwrite this attempt or weaken its assertions to obtain green.

Observed normal and ASan behavior:

- All three modes (`stairs`, `clear-floor`, `pairing`) exit0 but report0/1 passed. The native test executable's exit status alone is insufficient.
- `stairs` really uses an open doorway, not stairs. The actual engine emits “There is no clear floor on which to cast the spell.” Native message scraping makes phaseA count−1 before versus0 after.
- In phaseB both builds report danger266/266, avoidance180, and `DECISION phaseB acted=0 keys=0`; both fail `requirement 'defended'`. Thus no later glyph creation and **no target ASan write report in this product attempt**.
- `clear-floor` reports phaseB308/266 and also declines; `pairing` likewise. Both controls' full normal logs are byte-identical before/after, but both fail their required action, so they are not passing controls.

Hypothesis to investigate, not established: previously carried caster-origin/per-spell danger corrections affect source fixture eligibility. Inspect existing guards and compare with source evidence. Preserve the original fixture and avoid synthetic negative counts/messages or arbitrary threshold changes. Any separately adapted product scenario must explain its applicability and retain the original failed attempt.

The fixture declares interventions: phaseB grants another known Rune scroll and relocates the actor to clear floor; this is a bounded native producer/parser scenario, not autonomous reachability or a natural death/frequency claim. ASan uses `detect_leaks=0:intercept_strcmp=0`, matching source proof to avoid an unrelated name-initialization interceptor report; disclose this scope. The target heap write is compiler-instrumented. Do not claim a dedicated full-list natural scenario.

## Reproduction and evidence recovery

From the repository root, inspect the failed attempt without executing a new batch:

```sh
cd .worktrees/glyph-tracker
cat artifacts/glyph/scenarios/normal-after-stairs.log
cat artifacts/glyph/scenarios/normal-after-clear-floor.log
cat artifacts/glyph/scenarios/normal-after-pairing.log
tail -35 artifacts/glyph/scenarios.log
```

Original command (already executed; output directory must remain intact):

```sh
flock /tmp/angband-validation.lock python3 tools/verify-glyph-tracker.py \
  --before-build ../per-spell/build/native \
  --output artifacts/glyph/scenarios
```

Use a new output directory for a justified rerun. Before normal core is the retained per-spell product build; the runner proves its recorded source/build inputs match logical before19870. Before ASan replaces only the message object in the fully instrumented after core with a separately instrumented original message object. All link commands, object/binary hashes and stdout are recorded in result.json. Normal sources/objects were not modified for that comparison.

Ignored archive `artifacts/glyph-stop/glyph-unverified-evidence.tar.gz` contains28 log/JSON/fixture/profile members,95,685bytes, SHA256 `f8e110e0659be22ce90d595cefaba1b92a25e9861d4e560d5356c2edee6fd196`. Adjacent `manifest.json`, `SHA256SUMS` and `RECOVERY.md` describe archive/per-member verification; archive contents were read back and checked. This is a local non-/tmp recovery copy, **not an off-machine backup**. Binaries/objects remain in the task worktree; full build trees/runs/saves remain outside Git. No owned long job is running at handover.

## Exact next work

1. Read latest consumer1/source207/parent7 and live issue48 ownership; inspect this branch and failed logs before editing. Recheck official master during resumed integration.
2. Trace why actual product phaseB refuses the action. Resolve scenario applicability honestly, preserving original failure and controls; demonstrate actual product fail-before/pass-after and target ASan write before/absence after, without changing game rules.
3. Verify patch round trip, tooling tests, and all60 prior native fixture cases against the new core, comparing source279 controls with the nine-carry logs (the prior per-spell carry intentionally changed one mixed-storm result). Normal gate already passes at40b; repeat only if new changes/check requirements justify it.
4. Publish a normal adoption PR; agent evidence review and required checks, then normal merge. No per-PR independent review stop. Only then mark48 carried/open+patch-active and measure actual merged build against unchanged v1 seeds11/29/47, cap20000/wall120/stall30. Keep every failure and all outcomes; starting pairs do not imply identical later encounters.
5. Record actual results/limits/next action on48, source118 and checkpoints1/7. Recheck newly ready source67 medium-priority skip-list correction before low-priority81 or discretionary death work; inspect live readiness rather than assuming it remains ready.

Death feedback check at stop found no new owner feedback on22/34/41 beyond own receipts6686739352/6686739875/6686740236. Existing two cases/two starts/eight death attempts retain original builds. Default replay offsets remain5/12/25/40/60/82/105, omit10; historical10/15/20 remain evidence. Mandos was given a copyable prompt in chat, not messaged. Milestone2/package38 remains an immutable earlier snapshot with later linked follow-ups; external review has not happened.
