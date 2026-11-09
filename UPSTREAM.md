# C source baseline

- Canonical source: https://github.com/angband/angband
- Imported pristine master: `e473720ed88a0f0c7ca66815cef3000eb4a38bc3`
- Current checked upstream master at bootstrap: the same commit.
- Source reports/proposals: https://github.com/diegoami/neo-angband-tracker
- Source C reference: `c-borg-reference`, not that fork's Neo `master`.
- Consumer checkpoint: https://github.com/diegoami/better-borg-c/issues/1

The bootstrap preserves Angband ancestry and all runtime source/data. Its
changes are session documentation, build-verification tooling and contained CI.
Original README and inherited workflows are preserved in docs/upstream-reference;
licences, contributors and original technical docs are retained in place.
There are no gameplay patches at bootstrap. See patches/series.json for carries.

Use named read-only source remotes. Fetching a newer upstream does not itself
change the product baseline; record deliberate integrations and patch retirements
in a normal PR. No automatic version chase, publication or upstream submission.

## Delivery and official tracking (owner decision,2026-11-06)

Deliver our Angband build with the integrated Borg. The current C Borg is not
a drop-in module for an arbitrary stock executable. Keep official angband/angband
as the game base rather than evolving an unrelated engine fork.

Check/fetch the official master head through the named push-disabled angband
remote at each active integration cycle and before importing/delivering game
changes. Record exact official/product pins and the check receipt on checkpoint1.
The2026-11-06 check still returns e473720ed88a0f0c7ca66815cef3000eb4a38bc3;
there is no upstream source advance to import at that observation. Broad review
may remain a deliberate weekly activity; head tracking is part of normal work,
not an unattended watcher or automatic merge/release.

When upstream moves, integrate deliberately through a normal PR with native
gates, applicable controlled scenarios, compatibility review and patch-retirement
audit. Retire a local correction only after its upstream replacement is actually
incorporated/rebuilt/verified. Keep historical measurement/death source/build/data
identities immutable; a new product version does not rewrite old records.

## Later Rust adoption path

The owner confirmed a second-stage path: canonical native C tracker reports and
fixes -> verified C consumer here -> borg-rs adoption. The Rust worker owns that
stage. It may target behavior parity with a pinned corrected consumer version,
or implement individual verified fixes directly in Rust with linked provenance
and the same native scenarios/controls. Preserve the original pristine C/Rust
parity baseline separately; known C bugs must not disappear from that contract
without an explicit target change. C-only patches are not automatically present
in a Rust implementation when those C Borg files are excluded from linking.

Improvements (owner decision, 2026-11-09): behavior/strategy improvements are
local to this fork, implemented as labelled improvement units; they are never
proposed to the source tracker or official Angband, and never represented as
carries. Only verified bug fixes take the upstream/carry routing.

Escape hatch (owner decision, 2026-11-09): a bug that does not seem fixable in
C can be proposed to borg-rs even without a C fix, because it may be more
feasible in Rust. Record the proposal on the canonical source-tracker issue
with the C infeasibility evidence and the verified C fixtures/scenarios a Rust
fix could reuse, cross-linked from the consumer investigation. Proposals are
outbound write-ups only; the C lane still does not poll or fetch borg-rs,
dispatch Rust work, or alter the parity contract without an explicit target
change.

The existing borg-rs project already builds a Rust static library and its engine
integration selects BORG_IMPL=c or rust using the native input seam/FFI. A future
adoption here would bring that integration into the same official-tracking C
engine, pinning engine/data/options/ABI and verifying both implementations. This
repository remains C-only now; this is the agreed later-stage contract, not a
claim that Rust is already integrated or permission for proactive Rust polling.

Interface references inspected only at the owner's request:
- https://github.com/diegoami/borg-rs/blob/main/borg-rs/Cargo.toml
- https://github.com/diegoami/borg-rs/blob/main/angband/CMakeLists.txt
- https://github.com/diegoami/borg-rs/blob/main/docs/REVIEW.md

### Targeted Borg-fork survey at the owner's request

On2026-11-06, agoodman00/angband is the maintained Borg-focused development
fork found in the targeted C survey. Its published borg1 and do_not_use heads
both equal e473720ed, also official master at the check. It is not currently
a separate ahead-of-official behavior reference. APW's public VBorg/ZBorg posts
contain useful historical fixes, but verified updates found were2018–2019 for
older Angband3.4.1/Zangband2.4.0. AngbandPlus describes a variant archive. These
are candidate donor histories, not proof of superior performance on current
Angband. Route a reusable defect/fix through canonical tracker evidence and
consumer controls; do not merge an old fork wholesale or assume equal rules.

- https://github.com/agoodman00/angband/branches
- https://www.innovapain.com/borg/
- https://github.com/NickMcConnell/AngbandPlus/blob/master/README
