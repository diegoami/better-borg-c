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

Delivery is our Angband build tracking official angband/angband. Check official
master during active integration; use normal verified upstream-import PRs and
patch-retirement audits, preserving old baselines/death versions. See UPSTREAM.md
for the separately owned later borg-rs adoption path; no Rust implementation now.
Every natural death must be recorded under docs/deaths with its actual version/
build, curated native logs/snapshots, evaluation/diagnosis/actions and index.
Use tools/record-death.py and tools/aggregate-deaths.py; repeated replays are not
new independent deaths. Full raw runs/saves/builds remain outside Git. Bugs first.

Weekly donor inventory is explicitly scheduled by the owner: fork-review.yml,
Mondays09:15 Europe/Berlin, ongoing issue24. Consult its latest pinned leads
before discretionary redesign; semantic review and verified bug carries remain
agent work. Metadata is not a performance claim; no automatic imports.

Owner death feedback is durable on each case's linked GitHub investigation.
Follow docs/deaths/FEEDBACK.md: record chat comments there, maintain feedback/
actions in the assessment, distinguish observations from proof, reply with
findings and regenerate the aggregate. Owner priorities include survival stock
over spare gear (proposal41) and investigating premature crowd exposure (34).
Actual pack capacity/consumption/knowledge/retreat must be checked; bugs first.
