# Rules

1. Native C consumer only. Canonical source defects/proposals live in
   diegoami/neo-angband-tracker; adoption/build/product issues live here.
   Link both ways, retain source credit/CBUG IDs and exact immutable commits.
2. Current issue status/active blockers and triage precede fixes. Broad upstream
   review is weekly manual, not a per-session sweep or daemon. Targeted checks
   for active adoption, duplicate avoidance and closure are appropriate.
3. Preserve one writer per task. Check source checkpoint207 and open PRs before
   claiming work. Use isolated task worktrees and normal additive commits/PRs;
   never amend, force-push, reset active sessions or move/delete published tags.
4. Start from the recorded C baseline and integrate deliberately. Never merge
   Neo TypeScript master or documentation-bearing workbench/c-borg wholesale.
   Import reviewed C-only proposal commits/patches with provenance; inspect the
   cumulative diff and interactions. Tracker proposals stay reusable upstream.
5. An adoption issue is `carried` only after the fix is applied here, built and
   verified; it remains OPEN until upstream resolves it and we incorporate,
   rebuild and verify that correction. Then label `fixed`, remove `carried`,
   close. `partial`/`not-carried` name actual missing work. `patch-active` is
   independent: do not remove a backport before its replacement is verified.
   Source issues never acquire these consumer labels. An accepted upstream
   correction closes the original after normal fork import/checks; a real
   recurrence is a NEW linked bug, not a speculative hold on the original.
6. For every adopted fix, record a self-contained Verification section in its
   issue and PR: practical harm, precise source/build pins, copyable commands,
   unchanged before/after/control conditions, actual output and honest limits.
   Source reasoning alone is not gameplay proof. Check numerical test summaries,
   not merely exit status. No assertion/seed/cap/timeout weakening for green.
7. Use the shared /tmp/angband-validation.lock for heavy local builds/scenarios.
   Watch/log progress. Required exact-head hosted full checks can satisfy normal
   gates; do not invent a duplicate local full prerequisite after green. Keep
   unresolved red evidence and profile differences explicit.
8. Keep patches/series.json and patches/README.md current with each adoption or
   removal. Retain source commits/evidence links; live state belongs to issues.
   Baseline updates need a normal PR, applicable scenario checks, the complete
   native gate and a patch-retirement audit. No blind all-bugs cherry-pick.
9. No official angband/angband posts/comments/PRs by the agent under the standing
   pause. Reports/proposals stay in our tracker; the owner decides external
   submissions. This product is not another source-board maintainer.
10. No proactive borg-rs fetch/polling or Rust work. It reports directly on the
    source board. Mandos owns its independent C-to-TS translation; the faithful
    port does not adopt C behavioral departures as parity fixes.
11. Preserve saves/profiles/lab/data and other sessions. Use disposable native
    scenarios. No deployment, OAuth/private backup, publisher/release/tag,
    directory retirement or unattended job is authorised by bootstrap.
12. Current scope includes bug fixes/adoption, reproducible native measurement,
    frozen baseline statistics and failure analysis; no new gameplay strategies. New
    product-specific defects belong here; reusable C discoveries route to the
    source tracker first. Record checkpoint at each merge or stop.

13. Owner-directed integration (2026-11-06): the consumer agent merges verified
    PRs after its evidence review and required green checks, measures impact and
    continues independent carries. Do not wait for independent review per PR.
    Assemble a linked change/evidence milestone for later external review; never
    represent that external review as already done. Other gates still apply.
