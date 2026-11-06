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
review (no internal FORK markers/catalogue IDs/AI trailers). Bugs only under
current scope. No official Angband posts, Rust polling, lab/data/OAuth access,
release/tag/publisher, cleanup, amend or force-push.

Use `flock /tmp/angband-validation.lock python3 tools/verify-native.py` for the
normal native gate; add unchanged fail-before/pass-after and negative controls
for each adopted bug. Watch/log long runs; do not kill another lane's gate.
Post actual results and exact next action to the adoption issue and checkpoint
at merge/stop. Do not auto-start a gameplay queue from a bootstrap checkpoint.
