# Milestone 12 review: impact v11 to the official import

Review input for milestone 12. This document maps the diff and gives the exact checks a reviewer can
run; the prompt at the end is written for any model the owner chooses.

**This is not a self-review.** Everything here, and everything in the unit docs, the adoption issues
and the PR bodies, is the implementer's account. Treat it as a set of claims to verify.

## 1. The diff under review

| | |
| --- | --- |
| Base | tag `4.2.6-impact-v11` on runtime snapshot `39268ca8a` |
| Head | `4e1b912cb` (PR 478) |
| Size | 6 first-parent merges, 64 files, +9790/-164 |
| Runtime surface | `src/`: 32 files, +674/-128 (carry 0118: 1 file; official import: the rest) |

```sh
git clone https://github.com/diegoami/better-borg-c.git bbc-review
cd bbc-review
git log --first-parent --oneline 4.2.6-impact-v11..4e1b912cb
git log --oneline 4.2.6-impact-v11..4e1b912cb -- src/
git diff 4.2.6-impact-v11..4e1b912cb -- src/borg/
```

If the head has moved, name the commit you inspected.

## 2. Claims to verify

1. **0118.** `borg_new_kill()` set the grid to floor using the slot's previous race. After the patch a
   newly seen wall-walker keeps the wall. Rerun `tools/verify-newkill95.py`; check the floor control is
   byte-identical and that no other caller depended on the removed step.
2. **Import correctness.** `git diff e473720ed 42cd156ac -- src/` should be fully present in the head.
   The only conflict (`borg_backup_swap`) is the upstream form; local carries in `borg-item-wear.c`
   (left-ring selection, `skipping` hoist) survive.
3. **Retirement.** Carries 0001 and 0002 contain no logic that official master lacks. Reproduce the
   "before" tree from the recipe in `UPSTREAM.md` and rerun `tools/verify-swap.py` and
   `tools/verify-knockout.py`; confirm 5 + 1 cases fail before and pass after, controls identical.
4. **Compile-time mapping.** `-Dborg_dont_react=borg.dont_react` (verify-knockout.py,
   regression-matrix.py) cannot mask a set/read mismatch: the fixture only reads the gate once.
5. **Gate.** `flock /tmp/angband-validation.lock python3 tools/verify-native.py` -> 965/965 unit, 5/5
   frontend. `tools/regression-matrix.py` over all groups at the head.
6. **Ledger.** `patches/series.json` (117 entries, 115 active), `patches/README.md`, `UPSTREAM.md`,
   `session.json` agree with each other and with issues 4, 7, 475.
7. **Honesty of scope.** The package claims no per-mode result. Check no doc says "neutral" for a
   configuration where the changed branch was not shown to execute.

## 3. Known gaps (do not count as findings unless the claim is wrong)

Per-mode effect (unrestricted / Lunal-only / normal-only) not measured; owed to borg-zoo issue 54. No
cohort run in this window. The 7 non-Borg official commits are covered only by the native gate.

## 4. Review prompt

```
Review milestone 12 of diegoami/better-borg-c: the diff from tag 4.2.6-impact-v11 to head 4e1b912cb.
Read docs/measurement/IMPACT-MILESTONE12.md and docs/review/MILESTONE12.md first. Treat every statement
in them as a claim to verify, not as evidence. Check sections 2.1-2.7 of the review map. Reproduce what
you can (verify-newkill95.py, the before-tree recipe in UPSTREAM.md with verify-swap.py and
verify-knockout.py, verify-native.py, regression-matrix.py). Output: a verdict (approve / approve with
corrections / do not approve) and findings M12-F1..n, each with file:line, severity and a concrete
failure scenario or "no issue found". State which findings you reproduced and which you only read.
```
