# Milestone 13 review: impact v12 to the 2026-11-14 carry batch

Review input for milestone 13. This document maps the diff and gives the exact checks a reviewer
can run; the prompt at the end is written for any model the owner chooses.

**This is not a self-review.** Everything here, and everything in the unit docs, the adoption
issues and the PR bodies, is the implementer's account. Treat it as a set of claims to verify.

## 1. The diff under review

| | |
| --- | --- |
| Base | tag `4.2.6-impact-v12` on runtime snapshot `4e1b912cb` (the official import) |
| Head | `9ccb2aaee` (PR 519) |
| Size | 20 first-parent merges, 501 files, +90086/-125 |
| Runtime surface | `src/`: 16 files, +155/-124 across 19 carry units |

```sh
git clone https://github.com/diegoami/better-borg-c.git bbc-review
cd bbc-review
git log --first-parent --oneline 4.2.6-impact-v12..9ccb2aaee
git log --oneline 4.2.6-impact-v12..9ccb2aaee -- src/
git diff 4.2.6-impact-v12..9ccb2aaee -- src/borg/
```

If the head has moved, name the commit you inspected. (`origin/main` may show one extra
session-state commit whose `src/` is identical.)

## 2. Claims to verify

1. **Nineteen units, one patch each.** `patches/series.json` (136 entries, 134 patch-active) has
   one entry per carry, each with source head, applied commits, patch file, evidence ref and
   verification doc; `patches/README.md` carries all nineteen window entries (the
   hundred-and-nineteenth through Carry 136); `patches/0119*`..`patches/0137*` exist
   and apply to their recorded before commits. Spot-check the mapping for 0119, 0123, 0131 and
   0137 against the adoption issues 482, 490, 506 and 518.
2. **Provenance.** Every carry's verifier asserts `before module + source diff == product module`
   (0135 and 0137 over three files; 0137's base is the stacked source parent `82fd25a54`, provided
   by the consumer's 0136). Rerun `tools/verify-wandnames38.py`, `tools/verify-stunprot589.py` and
   `tools/verify-vulnmod610.py` with the before builds they record; each must report
   `verified: true` (for wandnames-38 with the byte-identity exceptions disclosed in §2.6: the
   OUTCOME rows and the frost-only control identity hold; three phase logs differ by the disclosed
   VALUE line).
3. **Header-shift hazard.** 0135 and 0137 touch `borg-trait.h`. Check each phase of their
   verifiers compiles against its own build tree (`CMAKE_HOME_DIRECTORY`), not the working tree.
   The retained correction is `37ded9e8c`; the pre-correction failure mode is described in
   `docs/measurement/STUNPROT-589.md`.
4. **Fail-before/pass-after.** For the twelve behaviour fixes the unchanged kit fails before and
   passes after with the captured OUTCOME/STATE rows; for the seven cleanups every mode passes in
   both phases with identical outcomes. The per-unit `product-result.json` in each kit directory
   records the per-case comparison.
5. **Gate and matrix.** `flock /tmp/angband-validation.lock python3 tools/verify-native.py` ->
   965/965 unit, 5/5 frontend at the head. `python3 tools/regression-matrix.py --build
   build/native --output artifacts/m13-check` over all 115 groups / 359 cases: `ok: true`, zero
   failed cases; the 24 byte differences are exactly the four documented capture-drift groups
   (dangerfull-69, teleotier-176, wandnames-38, healamount-592) plus the six pre-existing groups.
6. **Capture-drift attribution.** For the four drift groups, the product's before and after logs
   match each other and only the named diagnostic line differs from the pristine capture
   (wandnames-38: confusion/fear VALUE −6 → −5; healamount-592: the source156 flee reason).
   Confirm no behaviour claim rests on those lines.
7. **616 duplicate claim.** `git show 28d478129` (source tracker, branch `task/coldmelee-616`)
   and `patches/0004-cold-melee-protection.patch` are the same hunk; the consumer's product
   already contains it.
8. **Ledger and honesty of scope.** `session.json`, `patches/README.md`, the adoption issues
   (482-518) and checkpoint 1 agree. No doc claims "neutral" for a configuration where the
   changed branch was not shown to execute; all 19 units record per-mode effect as not measured.

## 3. Known gaps (do not count as findings unless the claim is wrong)

Per-mode effect (unrestricted / Lunal-only / normal-only) not measured for any unit; owed to
borg-zoo issue 54. No cohort run in this window. The four capture-drift groups' matrix baselines
still point at the pristine captures (re-point owed on checkpoint 1). Sources 13 and 249 have no
released source fix; 154, 590, 591, 595 and 615 are classified but not carried (owner decision
pending); the five behaviour-flavored classifications are the implementer's, not reviewed.

## 4. Review prompt

```
Review milestone 13 of diegoami/better-borg-c: the diff from tag 4.2.6-impact-v12 to head 9ccb2aaee.
Read docs/measurement/IMPACT-MILESTONE13.md and docs/review/MILESTONE13.md first. Treat every statement
in them as a claim to verify, not as evidence. Check sections 2.1-2.8 of the review map. Reproduce what
you can (three verifiers including the header-touching and stacked ones, verify-native.py,
regression-matrix.py, the 616 duplicate diff). Output: a verdict (approve / approve with corrections /
do not approve) and findings M13-F1..n, each with file:line, severity and a concrete failure scenario
or "no issue found". State which findings you reproduced and which you only read.
```
