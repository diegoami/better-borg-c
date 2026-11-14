# Milestone 14 review: impact v13 to the 2026-11-14 evening batch

Review input for milestone 14. This document maps the diff and gives the exact checks a reviewer
can run; the prompt at the end is written for any model the owner chooses.

**This is not a self-review.** Everything here, and everything in the unit docs, the adoption
issues and the PR bodies, is the implementer's account. Treat it as a set of claims to verify.

## 1. The diff under review

| | |
| --- | --- |
| Base | tag `4.2.6-impact-v13` on runtime snapshot `9ccb2aaee` |
| Head | `cdfb6d477` (PR 539; `origin/main` may show session/docs commits after, `src/` identical) |
| Size | 11 first-parent merges, 453 files, +96385/-703 |
| Runtime surface | `src/`: 5 files, +37/-17 — one file per carried unit |

```sh
git clone https://github.com/diegoami/better-borg-c.git bbc-review
cd bbc-review
git log --first-parent --oneline 4.2.6-impact-v13..cdfb6d477
git log --oneline 4.2.6-impact-v13..cdfb6d477 -- src/
git diff 4.2.6-impact-v13..cdfb6d477 -- src/borg/
```

If the head has moved, name the commit you inspected.

## 2. Claims to verify

1. **Six units, one patch each.** `patches/series.json` (142 entries, 140 patch-active) has one
   entry per carry with source head, applied commits, patch file, evidence ref and verification
   doc; `patches/README.md` carries all six window entries (Carry 137-142); the patches apply to
   their recorded before commits. Spot-check the mapping for 0138, 0139, 0142 and 0144 against
   adoption issues 523, 525, 534 and 538.
2. **Provenance.** Each unit's verifier asserts `before module + source diff == product module`
   (0139/0144 over the layered `borg-escape.c`, 0138 over `borg-caution.c`, 0140 over
   `borg-danger.c`, 0142 over `borg-messages.c`, 0143 over `borg-fight-defend.c` with no
   offset). Rerun any two verifiers with the before builds recorded in their unit docs; each
   must report `verified: true`. For 0142/0144 (the suggested pair) all kit logs are
   byte-identical to the source captures; deepdescent-590 (0139) is the one kit whose product
   logs differ from the pristine captures — by the disclosed source156 TRACK line only (see
   §2.5 and the unit doc).
3. **Fail-before/pass-after.** All six kits fail before and pass after with the captured
   OUTCOME/STATE rows; each kit's `product-result.json` records the per-case comparison.
4. **The two rejections are real and isolated.**
   - 0141 (source595, phase distances): applying `37acca6c1` (tracker `task/phasemodel-595`) to
     the head and running the accumulated matrix must fail the cold-protection, shot-path and
     per-spell groups (distance/cast/hp_lost row changes) while the kit's own modes pass.
   - 0145 (source629, dive gates): applying `cdd36650d` (tracker `task/divegate-629`) and running
     the deskstair-153 group must fail `twodown` (`desperate_stairs` 1 -> 0) while `onestair`/
     `twostairs` pass; rerunning the same group against the pre-fix build passes all three.
   - The diagnoses posted on tracker #595 and #629 match these reproductions.
5. **Gate and matrix.** `flock /tmp/angband-validation.lock python3 tools/verify-native.py` ->
   965/965 unit, 5/5 frontend at the head. `python3 tools/regression-matrix.py --build
   build/native --output artifacts/m14-check` over all 121 groups / 371 cases: `ok: true`, zero
   failed cases; the differing cases are the 12 declared intentional transitions plus the 3
   disclosed `No Teleport` TRACK lines (losecon-61 lowcon/bothlow, deepdescent-590 control —
   one line each, decisions unchanged), and the six former drift groups are byte-identical
   after the PR 532 re-point. 40 tracker-pinned kit cases carry no committed local baseline.
6. **Fixture portability holds.** The swap and knockout fixtures take the profile root from
   `CBUG0066_PROFILE` / `CBUG0002_PROFILE` with a relative fallback (M13-F1 correction, PR 531);
   no `/home/` absolute path remains in any fixture compiled by the matrix. The knockout
   `PROFILE` diagnostic prints the basename (PR 532).
7. **Ledger and honesty of scope.** `session.json`, `patches/README.md`, the adoption issues
   (523/525/527/534/536/538) and checkpoint 1 agree. Every window unit records per-mode effect as
   **not measured** (0143 as nil by construction); no "neutral" claim for an unexecuted
   configuration. D0020-D0030 are labelled unassessed in their own metadata and in the registry;
   no diagnosis or claim is drawn from them.

## 3. Known gaps (do not count as findings unless the claim is wrong)

Per-mode effect not measured for any unit; owed to borg-zoo issue 87. No cohort run in this
window. 0141 and 0145 are not carried (blocked on source-lane corrections); their kit-level
passes and matrix-level rejections are both documented. D0020-D0030 assessments owed (issue 163).
The `No Teleport`/flee-reason byte-diff groups were re-pointed where they pre-dated this window;
the two gaining lines from 0144 join the next re-point sweep.

## 4. Review prompt

```
Review milestone 14 of diegoami/better-borg-c: the diff from tag 4.2.6-impact-v13 to head cdfb6d477.
Read docs/measurement/IMPACT-MILESTONE14.md and docs/review/MILESTONE14.md first. Treat every statement
in them as a claim to verify, not as evidence. Check sections 2.1-2.7 of the review map. Reproduce what
you can (at least two unit verifiers, the 0145 deskstair isolation, the 0141 matrix rejection,
verify-native.py, regression-matrix.py). Output: a verdict (approve / approve with corrections /
do not approve) and findings M14-F1..n, each with file:line, severity and a concrete failure scenario
or "no issue found". State which findings you reproduced and which you only read.
```
