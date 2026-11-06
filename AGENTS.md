# Native C consumer session

This checkout owns diegoami/better-borg-c: adoption/testing of native C Borg and
Angband fixes. Read RULES.md, PLAN.md, UPSTREAM.md, session.json and checkpoint
#1's latest comments before work. Run `git status --short`, inspect open PRs
and source/consumer issue ownership. Work in isolated task worktrees.

Canonical C reports/proposals remain in diegoami/neo-angband-tracker; its
native-C lane is checkpoint207 and is independent. Do not edit or reset that
worktree. This repository owns linked adoption issues, not duplicate source
reports or Neo/TS translations. Workspace coordination is parent checkpoint7.

Read CONTRIBUTING.md and original technical/legal docs before editing C.
Preserve credit/licences/history; keep source comments suitable for upstream
review (no internal FORK markers/catalogue IDs/AI trailers). Scope includes verified bug carries, reproducible native execution/measurement,
frozen baseline statistics and failure analysis (owner authorised 2026-11-06).
New gameplay strategies remain outside scope. No official Angband posts, Rust polling, lab/data/OAuth access,
release/tag/publisher, cleanup, amend or force-push.

Use `flock /tmp/angband-validation.lock python3 tools/verify-native.py` for the
normal native gate; add unchanged fail-before/pass-after and negative controls
for each adopted bug. Watch/log long runs; do not kill another lane's gate.
Post actual results and exact next action to the adoption issue and checkpoint
at merge/stop. The owner explicitly started measurement and source82 adoption on 2026-11-06;
follow PLAN.md and live ownership rather than auto-selecting a new gameplay queue.

Owner instruction (2026-11-06): merge verified PRs after agent evidence review
and required checks, measure impact and keep going. Independent/external review
is deferred to a milestone covering accumulated changes and evidence. Do not
reintroduce a per-PR independent-review stop. Follow PLAN.md and RULES13.

Owner priority (2026-11-06): bugs always first, carried or not. Carry verified
fixes and investigate real defects before discretionary death analysis. When
that queue permits, follow docs/measurement/DEATH-ANALYSIS-PLAN.md: record deaths,
causes and living saves; qualify pre-death replay; raise evidence-backed issues
before changes. Original-C discoveries go to neo-angband-tracker first, then
source fix and separate consumer carry. No per-PR external-review stop.
