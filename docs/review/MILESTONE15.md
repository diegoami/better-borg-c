# Milestone 15 review: impact v14 to the 574b618c3 import

Review input for milestone 15. This document maps the diff and gives the exact checks a reviewer
can run; the prompt at the end is written for any model the owner chooses.

**This is not a self-review.** Everything here, and everything in `UPSTREAM.md`, the consumer
issues and the PR bodies, is the implementer's account. Treat it as a set of claims to verify.

## 1. The diff under review

| | |
| --- | --- |
| Base | tag `4.2.6-impact-v14` on runtime snapshot `cdfb6d477` |
| Runtime snapshot | `b684b95b4` (PR 546) |
| Release tag | `4.2.6-impact-v15` (package merge commit; `src/`, `lib/`, `CMakeLists.txt` identical to `b684b95b4`) |
| Runtime surface | `src/`: 15 files, +713/-199, all from official master `574b618c3`; `src/borg/`: `borg-trait.c` only |

```sh
git clone https://github.com/diegoami/better-borg-c.git bbc-review
cd bbc-review
git remote add angband https://github.com/angband/angband.git && git fetch angband master
git log --first-parent --oneline 4.2.6-impact-v14..b684b95b4
git diff 4.2.6-impact-v14..b684b95b4 -- src/borg/
git diff angband/master b684b95b4 -- src/borg/borg-trait.c src/borg/borg-caution.c src/borg/borg-escape.c
```

If the head has moved, name the commit you inspected.

## 2. Claims to verify

1. **The import is exactly official master.** `ec5778b92` (an ancestor of `b684b95b4`) is a merge
   whose first parent is `b0bacee06` and whose second parent is
   `574b618c3bfec595f3503a58f8e488b1c4ae3a46`. Of the 17 game files the upstream range
   `42cd156ac..574b618c3` touches, the 14 that carry no local change are byte-identical to
   `574b618c3` at `ec5778b92` (`git diff --quiet 574b618c3 ec5778b92 -- <file>`); `borg-caution.c`
   and `borg-escape.c` are unchanged by the merge (`git diff b0bacee06 ec5778b92 --` them is empty:
   the carries were byte-identical to upstream).
2. **The conflict resolution kept every other carry.** `git diff b0bacee06 ec5778b92 --
   src/borg/borg-trait.c` is one hunk, in `borg_notice_equipment()`: the carry's `|=` slay lines
   become upstream's `MAX` lines. Nothing else in the file changes (a first resolution attempt took
   the whole upstream file and was undone before commit).
3. **Retirement audit.** Rebuild the before tree (`git revert --no-commit 007bea95c b5747369b
   95387b06f` on `ec5778b92`, commit on a scratch worktree), run `tools/verify-native.py` there and
   in a `b0bacee06` worktree (and in the product tree, at any commit whose game files equal
   `ec5778b92`; the M15-F1 correction pinned the merge and relaxed this), then
   `python3 tools/verify-retire-574b618.py --before-tree <before> --carry-tree <carry> --output <dir>`.
   It must report `verified: true` with the rows in `docs/measurement/IMPACT-MILESTONE15.md` and
   `carry_after_logs_identical` true for all eight modes. The fixtures need the tracker commits
   `382acb7b9` (local), `f88fee1e3`, `3adc1b812`, `25b011863`.
4. **`MAX` vs `|=` has no decision effect today.** Every `BI_WS_*` reader is a truth test; the two
   forms are nonzero in the same cases (check `grep -n BI_WS_ src/borg/*.c`).
5. **Gate and matrix.** `flock /tmp/angband-validation.lock python3 tools/verify-native.py` ->
   966/966 unit, 5/5 frontend. `python3 tools/regression-matrix.py --build build/native --output
   artifacts/m15-check` -> 121 groups / 371 cases, `ok: true`, zero failed; every case's
   `log_sha256` and `outcome` equal `docs/measurement/impact-v14/regression-summary.json`. The 17
   kit groups need their tracker evidence commits fetched (a fresh clone lacks them).
6. **Ledger and issues.** `patches/series.json`: 142 entries, 137 patch-active; 0017, 0092 and
   0144 carry `retired_by_upstream` = `574b618c3` and `retirement_verification`;
   `upstream_import.official_head` = `574b618c3`. #69, #363 and #538 are closed with `fixed` and a
   receipt. `session.json`, `UPSTREAM.md`, `patches/README.md` and checkpoint 1 agree.
7. **Release base.** `tools/make-release.py` now bases the patch and source assets on
   `upstream_import.official_head`. Running it on the tag must produce a patch that applies to a
   fresh `574b618c3` checkout and reproduces `src/`, `lib/` and `CMakeLists.txt` of the tag
   exactly; the source asset must build and pass the gate; the two tarballs must be byte-identical
   when rebuilt.
8. **Scope honesty.** Per-mode effect recorded as not measured; no "plays better" claim; the
   source-tracker issues untouched.

## 3. Known gaps (do not count as findings unless the claim is wrong)

Per-mode effect not measured (owed to borg-zoo issues 54/87); no cohort run. ASan phases of the
original slay verifier not rerun. The slay fixture cannot distinguish `MAX` from `|=`. The seven
non-Borg official commits are covered by the gate and the matrix only. 0141/0145 remain blocked
on the source lane. D0020-D0030 assessments owed (issue 163).

## 4. Review prompt

```
Review milestone 15 of diegoami/better-borg-c: the diff from tag 4.2.6-impact-v14 to runtime snapshot
b684b95b4, and release tag 4.2.6-impact-v15. Read docs/measurement/IMPACT-MILESTONE15.md,
docs/review/MILESTONE15.md and the "Import of official master 574b618c3" section of UPSTREAM.md first.
Treat every statement in them as a claim to verify, not as evidence. Check sections 2.1-2.8 of the
review map. Reproduce what you can (the merge-vs-upstream diff, the retirement verifier, verify-native.py,
regression-matrix.py, the release patch on a fresh 574b618c3 checkout). Output: a verdict (approve /
approve with corrections / do not approve) and findings M15-F1..n, each with file:line, severity and a
concrete failure scenario or "no issue found". State which findings you reproduced and which you only read.
```
