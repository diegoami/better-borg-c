# Native C consumer plan

Bootstrap: preserve pristine C history at UPSTREAM.md's pin, establish independent
session/rules/checkpoint, contain inherited publishers, build and run the native
baseline, then register a verified workspace recovery pin. No gameplay changes
are part of bootstrap. Live readiness/results belong to checkpoint1.

## Owner-directed zoo stall investigation (2026-11-07/08)

Bug-first [consumer204](https://github.com/diegoami/better-borg-c/issues/204)
pre-empts queued carries: M4 and M3 munchkin seed1045 reproduce the successful
stair cycle at engine59893. Pristine loaded-state proof routes the original-C
mechanism to [source403](https://github.com/diegoami/neo-angband-tracker/issues/403).
The disabled-munchkin loaded-state control advances140 turns and recovers.
See [reproduction/evidence](docs/measurement/ZOO-STALL-1045.md).
Carry-prefix bisection finds5 passing/6 failing; complete the conditional
seed1047 no-deeper check and durable archive before the final issue/checkpoint report. No gameplay
fix or borg-zoo mutation is part of this investigation.

## Borg design, tuning proposal and evidence references

Owner-requested reference inventory, reviewed2026-11-07. Start with the
[canonical C Borg documents index](https://github.com/diegoami/neo-angband-tracker/blob/master/docs/c-borg/README.md).
These are design/evidence references, not a second live backlog. Check the linked
boards and actual product source before selecting work or interpreting a claim.

### How the C Borg works

[The C Borg: purpose and architecture (BORG_SPEC.md)](https://github.com/diegoami/neo-angband-tracker/blob/master/docs/c-borg/BORG_SPEC.md)
is the specification: perception, input/key channel, decision ladder, danger,
flow, caution, preparedness, modes and configuration. Its source reference is
original C at `e473720ed88a0f0c7ca66815cef3000eb4a38bc3`, not a description of
all later consumer carries. In particular, perception includes screen/message
observations AND direct game-state reads; do not revive the screen-only model.
Use it to understand the mechanisms behind death evidence and candidate changes.

### Redesign: a tunable, better Borg

- [Tunable Borg Plan, revision3](https://github.com/diegoami/neo-angband-tracker/blob/master/docs/c-borg/TUNABLE-BORG-PLAN.md):
  shared evaluation/roadmap for better-borg-c and borg-rs. Keep the working Borg,
  expose a justified parameter surface with defaults identical to a frozen carry
  baseline, compare profiles, and replace decision modules only on evidence.
- [Owner's private rendered copy](https://claude.ai/artifact/V3PXru2tuwtBdcUt9TMNKR):
  convenience pointer supplied by the owner; the GitHub Markdown is the
  reviewable source used for this inventory. Private-copy parity was not checked.
- [Plan review prompt](https://github.com/diegoami/neo-angband-tracker/blob/master/docs/c-borg/TUNABLE-BORG-PLAN-REVIEW-PROMPT.md):
  the rubric for a planning review, separate from an implementation task.
- [Review360](https://github.com/diegoami/neo-angband-tracker/issues/360) and
  [re-review on PR361](https://github.com/diegoami/neo-angband-tracker/pull/361#issuecomment-6706003438):
  read alongside the plan and its [revision3 response](https://github.com/diegoami/neo-angband-tracker/pull/361#issuecomment-6706050466).
  They explain the baseline, coverage, endpoint, seed-secrecy and compute
  corrections; a merged plan is not proof of implementation or measured benefit.

Important experiment constraints from revision3: pristine reference and frozen
carry baseline are different identities; default equivalence is against that
same carry set and proves only tested executions. The proposed primary endpoint
is verified victory before T or alive at T having reached D, with a declared
boundary rule, progress floor and survival tolerance. Preserve separate
identity/regression, training, validation and sealed test seeds. Test outcomes
must not leak into identity checks or policy selection. Costs/counts/builds in
the plan and reviews are historical observations, not current throughput promises.
The plan's cross-repository R0/R1 ordering is a proposal with scope/ownership
decisions; this reference task starts no Rust adoption, tuning or new strategy.

### How the claims were checked

- [Source-level check programs](https://github.com/diegoami/neo-angband-tracker/blob/master/docs/audit/c-reports/spec-checks/README.md):
  transcribed C logic on stated, sometimes synthetic inputs; these are not game
  runs and do not establish that ordinary play reaches the tested states.
- [Re-check record](https://github.com/diegoami/neo-angband-tracker/blob/master/docs/audit/c-reports/spec-checks/RECHECK.md):
  reproducible checks, corrected source interpretations, review responses and
  explicit unverified claims. Mechanical citation checks do not prove semantics.
- [Findings provenance](https://github.com/diegoami/neo-angband-tracker/blob/master/docs/audit/c-reports/spec-checks/PROVENANCE.md):
  origin and limits of findings310–316. Its re-check notes that the historical
  harness source was unavailable and those runtime statements were not reverified;
  do not treat them as validation of our current native observer/replay tools.

### Quick gains and experiment toolkit

| Source candidate | What to evaluate | Local relationship |
| --- | --- | --- |
| [368: existing borg.txt switches](https://github.com/diegoami/neo-angband-tracker/issues/368) | Screen existing settings on frozen seeds before new code | Candidate experiment, not a default change; current general runner does not expose arbitrary Borg configuration via CLI |
| [369: formula identity before tuning](https://github.com/diegoami/neo-angband-tracker/issues/369) | Compare dynamic formulas with built-in calculations, then consider text tuning | Identity and prerequisite carry/branch coverage checks come first; formulas do not replace every power/preparedness gate |
| [370: early Phase Door and cure reserve](https://github.com/diegoami/neo-angband-tracker/issues/370) | Early-dive/restock policy and its town/progress costs | Local [154](https://github.com/diegoami/better-borg-c/issues/154); distinct from reserve-priority41 and escape-choice158/159 |
| [371: character-level/depth ratio](https://github.com/diegoami/neo-angband-tracker/issues/371) | Tunable dive gate with identity at its default | Text-only route depends on369; compare survival AND progress, not depth alone |
| [376: experiment toolkit](https://github.com/diegoami/neo-angband-tracker/issues/376) | Early-death corpus, activation checks, replay, branching, shadow evaluation and paired confirmation | Reuse current dossier/replay tools; exact state branching, safe shadow evaluation and a general population experiment toolkit are not delivered by the death collector |

[All open source enhancements](https://github.com/diegoami/neo-angband-tracker/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)
is the live discovery view; do not freeze that queue in this document or create
local duplicates before checking ownership and relevance.

### Fit with this repository's processes

Use [death brainstorming and overall assessment](docs/deaths/REVIEW-TEMPLATE.md)
and the [two-stage improvement workflow](docs/measurement/DEATH-IMPROVEMENT-WORKFLOW.md)
to turn evidence into focused local investigations/enhancements, then a separately
scoped prospective implementation experiment. Existing examples: [41 stock
priority](https://github.com/diegoami/better-borg-c/issues/41), [154 early
reserves](https://github.com/diegoami/better-borg-c/issues/154), [158 theft danger](https://github.com/diegoami/better-borg-c/issues/158)
and [159 attempted walking retreat](https://github.com/diegoami/better-borg-c/issues/159).

[Native measurement](docs/measurement/README.md), [recorded replay](docs/measurement/RECORD-REPLAY.md)
and the [owner replay queue/bounded collector](docs/measurement/DEATH-QUEUE.md)
already provide evidence infrastructure. Death-only collection or a rescued
replay does not estimate a population benefit. Activation instrumentation,
branching/shadow safety, endpoint observation, shared calendar policy and
prospective profile comparisons must each be qualified before claiming toolkit376
or the redesign acceptance contract is implemented. Bugs retain priority and
source defects retain their canonical source-fix/consumer-carry route.

Next, after bootstrap handoff:
1. Review source tracker checkpoint207 and ready C proposals/evidence. Start
   with confirmed measurable harm, not every reported code anomaly. Source14
   (knockout reset) and82 (safer emergency equipment swap) have existing native
   evidence and owner-filed upstream PRs; inspect live state before adoption.
2. Create a distinct consumer issue per independent correction, linked both
   ways. Name the exact reviewed C source commit and evidence pin. Do not assume
   a proposed patch is already accepted upstream or applied here.
3. Apply one correction on an isolated task branch, preserve attribution and
   patch-removal units. Reproduce the relevant before/after/control evidence
   against the product and run the normal native gate. No survival claim from
   unit tests alone. Keep interactions explicit as carries accumulate.
4. Merge normally after agent review and required green checks; update patch ledger and
   checkpoint. Mark verified local corrections carried/open. Source tracker
   retains canonical defect/proposal ownership.
5. On upstream resolution, integrate the replacement deliberately, rebuild/test,
   remove superseded local patch only when proven replaced, then fixed/close
   the consumer. New observed regressions are new linked reports.

No feature queue, automated upstream watcher, Neo/TS/Rust work, deployment or
private-data migration is started by this plan.

## Owner-authorised measurement and first carry (2026-11-06)

1. Preserve pristine source e473720ed88a0f0c7ca66815cef3000eb4a38bc3. Inspect
   native Borg/test interfaces before extending them. Prove repeatability of a
   disposable ordinary-rules character: game RNG and Borg RNG/options matter;
   retain hashed starting saves where seed-only repetition is insufficient.
2. Build a small runner recording source/build/binary/data/config identities,
   commands and limits. Distinguish game turns, energy, Borg decisions and wall
   time; classify death, completion, cap, stall, crash and harness failure.
   Preserve every result, recent valid checkpoint and terminal evidence. Declare
   instrumentation; do not change RNG consumption, decisions or game rules.
3. Freeze a modest cohort before comparison. Time pilot runs first, publish all
   per-run machine-readable outcomes and copyable commands, including failures.
   Keep generated runs/saves/builds out of Git; durable representative evidence
   and recovery must not depend on workstation /tmp paths. No dashboard needed.
4. Adopt source82 (safer emergency swap) separately with linked issue, exact
   C-only provenance, patches/ ledger, unchanged nine-case controls against the
   product build and normal native gate. Compare identical frozen starting
   conditions, acknowledging later RNG divergence from changed decisions.
   Scenario benefit does not imply a detectable small-cohort survival benefit.
5. Continue only independent measurable bug carries, routing reusable source
   discoveries to neo-angband-tracker/checkpoint207. No new gameplay strategies.

Measurement ownership: consumer issue3; coordinator workspace7. New permission
changes the bootstrap-only scope; other standing exclusions and lifecycle remain.

## Owner-directed integration and milestone review (2026-11-06)

The owner explicitly instructed the consumer agent to merge, measure the impact
and keep going. Do not stop each verified PR waiting for independent review.
Use isolated task branches, normal additive commits and PR merges, inspect actual
numerical checks and unchanged before/after controls, then record merged source
and measurements at the adoption issue and checkpoint. Required checks remain
required; no evidence or test condition is weakened for a merge.

Accumulate independent carries with individual provenance/removal units and
measure them against frozen starting conditions. At a coherent milestone, link
every change, source/applied/merged pin, controlled result, gameplay comparison,
failed attempt and limitation in one review package. External review happens at
that milestone; it is not fabricated or required before each internal merge.
No official Angband posting or other standing exclusion is changed.

## Bugs first; death-driven issues when the bug queue permits (2026-11-06)

Bugs always take priority, carried or not: integrate ready verified fixes and
investigate concrete original/product defects before discretionary death tooling
or exploratory batches. New original-C bugs go first to neo-angband-tracker,
coordinated with source207; source fix/proposal first, then linked native consumer
carry and measurement. Do not race the source writer or silently fix only here.

When no higher-priority bug task can progress, follow
docs/measurement/DEATH-ANALYSIS-PLAN.md: record natural deaths/causes and living
saves, try validated short pre-death windows, diagnose against native code and
file evidence-backed issues before improvements. Seed replay from the original
start precedes claims of faithful checkpoint continuation. The existing frozen
cohort remains immutable; new exploration has prospective limits and full failure
accounting. New strategy suggestions remain issue proposals, not implementations.

## Durable death records and delivery (2026-11-06)

Every natural death is curated under docs/deaths with its actual source/build,
selected native logs/snapshots, evaluation, diagnosis confidence and linked
issue actions. Export from immutable run metadata with tools/record-death.py,
then aggregate with tools/aggregate-deaths.py. Preserve every attempt and label
replays/reference versions; do not inflate independent counts or overwrite old
build identity after fixes. Full runs/saves/builds stay outside Git.

Delivery is our Angband build tracking official master through deliberate
verified imports/patch retirement. UPSTREAM.md records the owner's later-stage
tracker -> C consumer -> borg-rs adoption path. It does not change the current
C-only work scope or the bugs-first priority.

## Ongoing donor review (owner-requested2026-11-06)

Weekly public C Angband/Borg inventory runs Mondays09:15 Europe/Berlin through
.github/workflows/fork-review.yml and appends to issue24. It pins official/fork
heads, last Borg activity, file differences and open official Borg PR leads;
known development branches plus bounded discovery are included. The job does
not complete semantic review: the standing task inspects real diffs and source
tracker ownership, turns useful candidates into issues/tests/carries and avoids
reinventing existing solutions. Do not call an active/different fork better
without same-game/cohort evidence. No auto-imports, tactics, heavy benchmarks,
Rust polling or official posting. Bugs always first.

## Owner death feedback outside chat

Use docs/deaths/FEEDBACK.md and the per-case GitHub investigation as the durable
discussion. Record owner comments, distinguish hypotheses/native facts, link
actions and report findings back; regenerate the aggregate without changing
old build identities or inflating replays. Current feedback: D0001 survival
stock ahead of spare gear (proposal41/stock investigation22); D0002 dangerous
crowd exposure too early (investigation34). Inspect departure stock/consumption,
restock/retreat and knowledge before entry, not just the terminal inventory.
Existing-rule bugs first, canonical source207 routing before fix/carry; broader
policy changes remain evidence-backed proposals rather than arbitrary thresholds.

Owner confirms comment processing as ongoing work: read new/edited death and
linked action comments at every active-session start and stop, record the read
receipt/follow-up on checkpoint1, and respond through the existing action/finding
process. This does not claim background execution between sessions or expand
the weekly metadata inventory into autonomous gameplay policy changes.

Owner expands death inspection to5/12/25/40/60/82/105 engine-turn offsets,
omitting10 from the new default. Preserve old windows. Add labeled earlier
event anchors when entry/stock/retreat precedes105; qualify original-start
prefixes on each death's actual historical build. See docs/deaths/window-profile-v2.json.
No additional independent lives or selectively enlarged performance cohort.

## Tenth through thirty-fourth carries merged (2026-11-07)

Consumer48/source118 (CBUG-0102) merged as b72ad8eae (PR49, import 40b002da,
patch 0010). The unchanged evidence fixture legitimately stopped passing
phaseB once the carried 0008 projection fix let the mage's bolts count; the
tracked adapted scenario (tools/glyph-tracker-scenario.c) verifies the real
failure message, the -1 count, the bounded creation and the ASan
heap-buffer-overflow WRITE on the actual product core, with all prior
fixture cases whole-log identical and the merged v1 seeds 11/29/47 unchanged
(3 cap survivors, traces identical to the nine-carry).

Consumer51/source254 (missile-254) merged as ce6435679 (PR52, import
09dd4435, patch 0011): the dead b_n < 0 guard in borg_attack_aux_launch let
a targetless probe read borg_items[-1].desc and queue a fire key from index
-1; the one-guard import verifies fail-before/pass-after with byte-identical
live-shot/simulated controls and the ASan heap-buffer-overflow READ on the
actual product core, 63 prior cases whole-log identical, merged v1 seeds
unchanged.

Consumer54/source67 (CBUG-0051) merged as cfaff7be7 (PR55, import 706fb49b,
patch 0012): the Teleport Other skip-list loop read one entry past the
count and suppressed the monster named by a stale slot from the Morgoth-depth
defense; the one-comparison import layers onto borg-danger.c (before module
+ source diff equals the product module) and verifies fail-before
(p2=208=192+16, product-accurate giant value 192) / pass-after (192) with
byte-identical no-morgoth/single controls, no sanitizer report, 66 prior
cases whole-log identical, merged v1 seeds unchanged. All three issues are
carried/open+patch-active until upstream incorporation. Full stories:
docs/measurement/GLYPH-TRACKER.md, MISSILE-NO-TARGET.md, TP-OTHER-SKIP.md
and the issues' verification comments. Consumer63/source244 (munchkin-244) merged as d28dbb16 (PR64, import
2cf521b8b, patch 0015): the munchkin stair tests read a stale neighbour
pointer after the adjacent-monster scan and queued a take-stair key on
plain floor (a no-turn keypress that can repeat indefinitely); the
five-line own-grid re-acquisition imports into an otherwise-pristine
borg-think-dungeon.c and verifies on the unchanged fixture with the
evidence's own profile preparation (phantom stair_key 62->0
fail-before/pass-after, on-stair control byte-identical), 74 prior cases
whole-log identical, merged v1 seeds unchanged.

Consumer66/source257 (vampire-257) merged as dfddcfff (PR67, import
81b15066, patch 0016): the Vampire Strike closeness guard tested the last
distance the scan examined instead of the chosen target's, so a bystander
at exactly the range limit vetoed the cast; the one-token import layers
onto borg-fight-attack.c and verifies on the unchanged fixture driving
the full production chooser (near-far acted 0->1 with real cast keys,
near-near/far controls byte-identical), 76 prior cases whole-log
identical, merged v1 seeds unchanged.

Consumer69/source239 (slay-239, priority high) merged as a88da7a06
(PR70, import 6bcdd28a, patch 0017): the equipment notice assigned the
eight slay traits per slot, so a weaponless light slot erased the wielded
weapon's slays and the kill traits were never set; the accumulating
import (borg-trait.c otherwise pristine) verifies on the unchanged
fixture (animal 17/17/20 fails before, 20/17/20 passes after; nonanimal
control byte-identical), 79 prior cases whole-log identical, merged v1
seeds unchanged.

Consumer72/source290 (detect-290, priority high, memory safety) merged as
3cd2c3237 (PR73, import c3e8f60a, patch 0018): a queued detection
self-reaction kept pre-level-change panel offsets and its four-cell mark
indexed past the resized arrays on a one-panel-high cave — a native crash
(SIGSEGV, the previously blocked harness runs) and an ASan
heap-buffer-overflow READ in borg_handle_self; the panel-bounds guard
drops stale reactions (borg-update.c otherwise pristine; the
fresh-reaction control is byte-identical across all phases), 81 prior
fixture cases whole-log identical, merged v1 seeds unchanged.

All nine issues (48/51/54/57/60/63/66/69/72) are carried/open+patch-active
until upstream incorporation. Full stories in docs/measurement/ and the
issues' verification comments. Queue: paused after consumer124 as owner requested. Resume with a source207
recheck, then brand-240/stairtrack-232 and any newer demonstrations before
low-priority 81 or discretionary death work. The owner separately requested
an accumulated bug-fix review: milestone3/issue128 collects the 27 verified
carries after milestone2 snapshot 2675d198e through runtime snapshot
702f091f6 (patches 0008-0034), with process/tooling context and review
questions in docs/measurement/IMPACT-MILESTONE3.md. Owner-led accumulated
review completed 2026-11-07: milestone2 approved and milestone3 approved
with evidence-durability/metadata findings on issues38/128. Follow-up
issue130 preserves the 25 worktree-held carry archives in primary artifacts,
corrects matrix/ledger metadata and records the final formula-memory ASan
receipt; no worktree is removed until that evidence copy is verified.
## Milestone 4 review package: eight carries since impact v3 (2026-11-07)

The owner authorized the accumulated review package. Milestone4 and
[review issue184](https://github.com/diegoami/better-borg-c/issues/184)
collect the eight verified carries after the reviewed v3 snapshot
702f091f6 (patches 0035-0042: brand-240, stairtrack-232, acidarc-252,
outoflight-229, mapwall-212, enlightenment-81, stairreturn-230,
blowname-247), pinned at runtime snapshot 70993393a, with the package in
docs/measurement/IMPACT-MILESTONE4.md. The package records the first
behavior-active carry (mapwall-212: the v1 traces legitimately diverge
from the 34-carry recording with unchanged survivor outcomes), the
blocked tapunlife-249 attempt (masker: carried patch 0022, red retained,
not counted), the separately owned source finding #399 (init-time
borg_sort_comp_hook overflow, expected in sanitized evidence), and the
concurrent-session process/tooling context (recording/replay feature and
death documentation outside the build inputs; tooling 41→71). No external
verdict is claimed; the owner launches the review.

Consumer176/source247 (blowname-247) merged as 70993393a (PR179,
import 541e03b1e, patch 0042): borg_mon_blow_effect()'s name-table loop
bounded itself with the full array length, so an unknown blow name
walked into the table's NULL sentinel entry and strcmp'd against NULL -
a segfault reachable from real monster blow names the Borg has not
mapped. The one-line sentinel-safe bound resolves in-table names and
returns MONBLOW_NONE for unknown ones. The unchanged source evidence
fixture segfaults (exit -11) before with the sanitizer naming the NULL
dereference in borg_mon_blow_effect directly (borg-fight-attack.c:93)
and passes 1/1 after on the plain and sanitizer builds, where the
pre-existing init-time borg_sort_comp_hook overflow (separately filed
source #399) still reports as expected; borg-fight-attack.c already
carries eleven patches and the applied diff body is byte-identical to
the source diff. Gate 965/965 + 5/5, tooling 71/71, and all 138 prior
matrix cases match the recorded forty-one-carry tally. Post-merge
frozen v1 measurement: seeds 11/29/47 all turn_cap alive and well with
whole-trace hashes identical to the forty-one-carry (stairreturn) run —
behavior-neutral on the cohort. Next: recheck source207 for newer
demonstrations; source #399 (init-time borg_sort_comp_hook overflow)
remains a separately owned source finding.
Consumer167/source230 (stairreturn-230) merged as bc8cf805f (PR171,
import db0d342ec, patch 0041): borg_think_dungeon_light()'s
out-of-light "Testing for stairs" branch queued borg_keypress('<') but
fell through without reporting that it acted, so the think loop treated
the stair key as disowned and kept queueing commands behind it; the
correction adds the missing return true. The unchanged source evidence
fixture verifies the burned-torch-on-stairs case acted=0 fail-before /
acted=1 with the same '<' pass-after, with the lit (timeout 2000) and
dead-no-stairs controls byte-identical and no sanitizer report;
borg-think-dungeon-util.c already carries 0032/0036/0038 and the
applied diff body is byte-identical to the source diff. Gate 965/965 +
5/5, tooling 66/66 (the suite now takes the shared validation lock
itself and must run outside a lock wrapper), and all 135 prior matrix
cases match the recorded forty-carry tally. Post-merge frozen v1
measurement: seeds 11/29/47 all turn_cap alive and well with whole-trace
hashes identical to the forty-carry (enlightenment) run —
behavior-neutral on the cohort. Next: recheck source207 for newer
demonstrations.
Consumer157/source81 (CBUG-0065, priority low) merged as 503e7a07b
(PR160, import 526906c0f, patch 0040; owner-directed after the recorded
backstop "low-priority 81" had been dropped from the handover's queue
summary): borg_use_things()'s force-item potion branch recognized
Enlightenment and guarded town use but never called the potion helper,
leaving a known potion unused in the dungeon while stairs beyond walls
stayed unknown; the correction adds the missing quaff after the town
guard. The unchanged source evidence fixture verifies the dungeon case
drinking nothing fail-before / one potion drunk with the native map
revealing the down stair pass-after, with five byte-identical controls
(town, unknown flavor, unrelated True Seeing, Augmentation
dungeon/town); borg-item-use.c already carries 0006 and the applied
diff body is byte-identical to the source diff. Gate 965/965 + 5/5,
tooling 56/56, and all 129 prior matrix cases match the recorded
thirty-nine-carry tally. Post-merge frozen v1 measurement: seeds
11/29/47 all turn_cap alive and well with whole-trace hashes identical
to the thirty-nine-carry (mapwall) run — behavior-neutral on the
cohort. Queue note: this was the last recorded backstop item; the
consumer queue now holds only the blocked tapunlife-249 attempt (#140)
pending owner direction, plus the open tapunlife masking diagnosis.
Next: recheck source207 for newer demonstrations.
Consumer148/source212 (mapwall-212) merged as f0288cca5 (PR149, import
5bd789ee0, patch 0039): borg_update_map()'s old_wall capture ran after
the grid feature was overwritten with what the game shows, so the
wall-change comparison compared the new feature against itself and
never fired; stale flow, stone-to-mud knowledge, icky flags and stamps
survived a grid changing under the Borg. The correction moves the
capture before the overwrite. The unchanged source evidence fixture
verifies door-close and door-open keeping everything stale fail-before
/ invalidating correctly pass-after (door-close resets the flow to the
new-wall 255, door-open keeps it) with the no-change control
byte-identical and no sanitizer report; borg-update.c already carries
0018 and the applied diff body is byte-identical to the source diff.
Gate 965/965 + 5/5, tooling 54/54 (the recording-feature tooling set),
and all 126 prior matrix cases match the recorded thirty-eight-carry
tally. **Behavior-active carry:** the post-merge frozen v1 measurement
legitimately diverges from the recorded traces for the first time —
seed11 and seed47 substantially (flow re-evaluations after ordinary
feature changes), seed29 barely; all three seeds still finish turn_cap
alive and well, so the measured impact is the intended re-flow after
corrected invalidation, recorded rather than asserted away. Next:
recheck source207 for newer demonstrations.
Consumer144/source229 (outoflight-229) merged as 04ab89381 (PR145,
import 54a26b3b3, patch 0038): borg_think_dungeon_light()'s entry test
`!BI_LIGHT && (BI_LIGHT <= 0 || timeout <= 3)` swallows its own
about-to-burn-out clause, leaving a lantern three turns from dark to die
with a spare torch in the pack; the corrected test
`(!BI_LIGHT || (timeout <= 3 && !NO_FUEL))` starts the maneuvers while
keeping everburning lights guarded. The unchanged source evidence
fixture verifies dying acted=0 fail-before / acted=1 keys `w e`
pass-after with lit, everburn and dead controls byte-identical and no
sanitizer report; borg-think-dungeon-util.c already carries 0032/0036
and the applied diff body is byte-identical to the source diff. Gate
965/965 + 5/5, tooling 41/41, and all 122 prior matrix cases match the
recorded thirty-seven-carry tally. Post-merge frozen v1 measurement:
seeds 11/29/47 all turn_cap alive and well with whole-trace hashes
identical to the recorded run. Next: recheck source207 for newer
demonstrations.
Consumer141/source252 (acidarc-252) merged as d619eec5f (PR142, import
2a4125e44, patch 0037): the blast loops in borg_launch_bolt_at_location()
and borg_launch_arc_at_location() excluded the south and east radius
edges (`<` instead of `<=`), so a giant exactly max_range south
contributed nothing and Acid Spray was never cast; the four inclusive
bounds count it. The unchanged source evidence fixture verifies edge
acted=0/keys=0 fail-before / acted=1/keys=17 pass-after (the recorded
Acid Spray sequence) with the near (eight grids) and empty controls
byte-identical and no sanitizer report; borg-fight-attack.c already
carries ten patches and the applied diff body is byte-identical to the
source diff. Gate 965/965 + 5/5, tooling 41/41, and all 119 prior
matrix cases match the recorded thirty-six-carry tally. Post-merge
frozen v1 measurement: seeds 11/29/47 all turn_cap alive and well with
whole-trace hashes identical to the recorded run. Two verifier-constant
mistakes were retained and corrected without touching any product
assertion. The tapunlife-249 carry attempt remains BLOCKED (red
retained, not carried; see TAP-UNLIFE.md). Next: recheck source207 for
newer demonstrations.
Consumer137/source232 (stairtrack-232, priority low) merged as 4fc3c481f
(PR138, import 8310e9cc, patch 0036): borg_think_stair_scum()'s
up-staircase "already known" scan used continue where the down-stair
scan uses break, so the staircase under the Borg was re-appended to
track_less on every visit (1 grows to 2 per visit until the array
fills); the one-keyword correction breaks on the match. The unchanged
source evidence fixture verifies known 1-to-2 fail-before / stays-1
pass-after with the fresh-discovery control byte-identical at 0-to-1
and no sanitizer report; borg-think-dungeon-util.c already carries 0032
in this same function and the applied diff is byte-identical to the
source diff. Gate 965/965 + 5/5, tooling 41/41, and all 117 prior
matrix cases match the recorded thirty-five-carry tally. Post-merge
frozen v1 measurement on the prepared merged-main build: seeds
11/29/47 all turn_cap alive and well with whole-trace hashes identical
to the recorded run. Next: recheck source207; the source348
panel-vs-DUNGEON_WID overread lead remains source-owned and not
consumer-ready; carry a newer demonstration when one is ready.
Consumer133/source240 (brand-240, priority low) merged as 638513e91
(PR135, import b30afa1a, patch 0035): the brand-the-ammo test in
borg_notice_ammo() was pasted twice with identical conditions (inside the
good-shooter block and in a tail block guarded by a `< 3` return that
only ever ran in the same state), so every qualifying stack added twenty
to the need-brand trait instead of ten; the fifteen-line tail deletion
counts it once. The unchanged source evidence fixture verifies
need_brand=20 fail-before / 10 pass-after with the two-arrow control
byte-identical at 0 and no sanitizer report; borg-trait.c already
carries 0017/0029 and the applied diff is byte-identical to the source
diff. Gate 965/965 + 5/5, tooling 41/41, and all 115 prior matrix cases
match the recorded thirty-four-carry tally. Post-merge frozen v1
measurement on the prepared merged-main build: seeds 11/29/47 all
turn_cap alive and well with whole-trace hashes identical to the
recorded thirty-four-carry run. Queue resumed by owner
direction 2026-11-07: source207 recheck found tapunlife-249 (no priority
label) and quick-scan leads #364-#367 (triage:needed) that do not
pre-empt the recorded low-priority order. Next: stairtrack-232 unless a
newer demonstration becomes ready.
Consumer124/source323 (calfree-323) merged as 5fb5d1f74 (PR125, import
dc1ea0c3, patch 0034): calculations_free() released calculation structs
without token-list backing arrays; the correction releases them. The
unchanged fixture keeps freed value 3/count 0 and constant 42/count 1
byte-identical. With opblock-324 already carried, stack-attributed
LeakSanitizer moves from 80 bytes/1 token allocation to no leaks, with
zero operator leaks in both phases; the pristine 160/2 expectation is not
copied blindly. The preceding 113 matrix cases comprise 111 passing (110
whole-log identical plus one asserted changed log) and two asserted-red
interactions; the final two calfree cases pass, tooling is 41/41 and merged
v1 seeds are unchanged. All twenty-five issues are carried/open+patch-active.
Owner requested a pause after this carry.
Consumer121/source324 (opblock-324) merged as 6a00d4408 (PR122, import
ced816c3, patch 0033): precedence adjustment freed operator-block structs
without their backing arrays; the correction releases them. The unchanged
fixture keeps value 7 and constant 42 byte-identical while LeakSanitizer
moves from 160 bytes/2 allocations in one operator-stack report block to
no leaks. The initial verifier's two-block grouping error is retained and
was corrected without changing the fixture. 111 prior cases pass, tooling
is 41/41 after PR116's named-headless tests, and merged v1 seeds are
unchanged. All twenty-four issues are carried/open+patch-active.
Consumer117/source314 (lunal-314, priority medium) merged as 4bfb44d73
(PR118, import 2e0593f6, patch 0032): the town stair-scum bail cleared
only lunal_mode and left fleeing_lunal set, producing the split state the
caution phase misreads; the correction clears the pair. The unchanged
fixture verifies 0/1->0/0 with the full-pack control byte-identical at
1/1, 109 prior cases passing and merged v1 seeds unchanged. All
twenty-three issues are carried/open+patch-active.
Consumer113/source313 (homeblows-313, priority medium) merged as
8a7eba1ad (PR114, import 668ac32c, patch 0031): the home-blows
calculation weighed a whole weapon stack rather than one weapon, giving
Borg 1 blow against the engine's 2 for ten rapiers; the correction weighs
one weapon. The unchanged production analyzer fixture verifies 1/2->2/2
with the single-rapier control byte-identical at 2/2, 107 prior cases
passing and merged v1 seeds unchanged. All twenty-two issues are
carried/open+patch-active.
Consumer109/source312 (surrounded-312, priority medium) merged as
75e92924f (PR110, import dbdb5f7f, patch 0030): trapped walls matched
both wall and trap branches and could produce a surrounded verdict with
zero monsters nearby; the trap test now belongs to the exclusive chain.
The unchanged production fixture verifies surrounded=1->0 with the
plain-wall control byte-identical, 105 prior cases passing and merged v1
seeds unchanged. All twenty-one issues are carried/open+patch-active.
Consumer105/source238 (light-238, priority medium) merged as 958f9744b
(PR107, import 497d9266, patch 0029): the equipment notice added an
item's light modifier twice, making the Phial's LIGHT[4] bi_light=8; the
correction drops the second addition. The unchanged fixture verifies 8->4
with the stock Wooden Torch byte-identical at 2, 103 prior cases passing
and merged v1 seeds unchanged. All twenty issues are
carried/open+patch-active.
Consumer102/source311 (glowoverflow-311, priority high) merged as
9aee81138 (PR103, import 3cb61705, patch 0028): the out-of-light flow
collected 1600 glowing grids into 1536-entry arrays, overflowing by 64;
the correction bounds collection. The unchanged fixture verifies 1600/64
-> 1536/0 with direct ASan global-buffer-overflow WRITE proof before and
a clean bounded flow after, the 1000-grid control byte-identical, 101
prior cases passing and merged v1 seeds unchanged. The separately noted
oversized-terminal panel-bounds lead is not claimed fixed. All nineteen
issues are carried/open+patch-active.
Consumer99/source322 (staletarget-322, priority high) merged as
29190814b (PR100, import 0d843a41, patch 0027): a tracked monster on the
player's own grid passed the distance-zero melee check and queued +5,
whose empty direction prompt stops the Borg; the correction requires
distance exactly one. The unchanged acting-chooser fixture verifies +5 ->
no action/keys with the real adjacent +2 control byte-identical, 99 prior
cases passing and merged v1 seeds unchanged. The first merge API call
returned 502 and the accidental parent-build measurement is preserved as
invalid-premerge evidence; the retry merged and measurement was rerun on
29190814b. All eighteen issues are carried/open+patch-active.
Consumer96/source325 (calcreload-325) merged as 0900c5cf4 (PR97, import
c528eb81, patch 0026): calculations_free() retained the backing pointer
array after zeroing the count, so the next parse overwrote and leaked it;
the correction releases it. The unchanged fixture verifies retained=1 ->
0 with reload value 7 throughout, a byte-identical single-parse control,
and stack-attributed LeakSanitizer 320 bytes/4 allocations -> 240/3 with
the two sibling leak paths unchanged. 97 prior cases pass and merged v1
seeds are unchanged. All seventeen issues are carried/open+patch-active.
Consumer93/source287 (text-287) merged as b68eb2223 (PR94, import
c6c51d4d, patch 0025): borg_what_text() bounded UTF-8 conversion by one
byte per wide character, leaving an 80-character row with one two-byte
character unterminated and the caller reading all 1024 stale bytes; the
conversion now uses the widest encoding for the same character count.
The unchanged fixture verifies terminated=0/strnlen=1024 ->
terminated=1/strnlen=81, with the ASCII control byte-identical at 80,
95 prior cases passing and merged v1 seeds unchanged. All sixteen issues
are carried/open+patch-active.
Consumer90/source261 (blind-261) merged as f997c8cee (PR91, import
713d9ad4, patch 0024): the blind-creature maneuver casts Frighten but
scored as confusion, so dragons suppressed only by confusion carried a
phantom 955 valuation the spell cannot deliver; the one-token import
layers onto borg-fight-attack.c and verifies with a production-derived
control expectation (the pinned -5 was pristine; the layered product
measures -4 after the losdispel leak removal): blind 955->-4 ==
frighten=-4, control byte-identical, 93 prior cases pass. Merged v1 seeds
unchanged. All fifteen issues are carried/open+patch-active.
Consumer87/source262 (staff-262) merged as aa87ca74d (PR88, import
13fe885cb, patch 0023, stacked on the carried losdispel correction): the
staff-holiness maneuver kept the bolt radius of zero and valued a single
monster on a line, though the activation is an area-of-sight dispel; the
radius correction verifies on the unchanged fixture (holy 28->60
fail-before/pass-after, single-target bolt control byte-identical at 28),
91 prior cases (89 identical plus the two documented losdispel
interactions asserted), merged v1 seeds unchanged. Queue: recheck
source207 for newer demonstrations (source-ranked 261, then
240/241/246/250/287).
Consumer84/source326 (losdispel-326, priority high) merged as 2e55c43f8
(PR85, import 0489305b, patch 0022): the radius-ten beam walk had no
arrival break, so the LOS-dispel blast scan ran only by accident and the
launcher leaked its initial -1; the three-token correction lets the blast
run and returns zero (dispel -15 -> 534 on the unchanged fixture, orb
control byte-identical). Two documented cross-carry interactions asserted
in the regression: dispel-248 undead direct=-1->0 (refusal contract
unchanged) and dispel-259 both modes +296 (the bats now valued; the
10500 doubled-penalty delta stays visible) — both prior carries' evidence
remains valid at their recorded commits. 87 of 89 prior cases whole-log
identical; merged v1 seeds unchanged. Queue: staff-262 (PR329/330) is
unblocked by this correction, then recheck source207 (source-ranked 261).
Consumer81/source259 (dispel-259) merged as 0c52dee46 (PR82, import
c9f24544, patch 0021): the teleport-reserve mana penalty was applied by
two back-to-back blocks (the fixed-six one a strict subset of every class
reserve), so it doubled; the five-line deletion layers onto
borg-fight-attack.c and verifies on the unchanged fixture (reserve
-21127->-10627 fail-before/pass-after, one 10500 block apart; out-of-band
control byte-identical at -127), 87 prior cases whole-log identical,
merged v1 seeds unchanged. All twelve issues are carried/open+patch-active.
Queue: recheck source207 for newer demonstrations (source-ranked 262/261)
— with none ready, the documented order resumes.
Consumer78/source258 (reserve-258) merged as c7f5b5758 (PR79, import
21c672a8, patch 0020): the reserve-bolt monster loop broke at the first
live monster, so the hit-points veto applied to a distant tough monster
instead of the near ones it describes; the loop correction layers onto
borg-fight-attack.c and verifies on the unchanged fixture (veto 0->40
fail-before/pass-after, kobold-only control byte-identical), 85 prior
cases whole-log identical, merged v1 seeds unchanged. All eleven issues
are carried/open+patch-active; every pair the source lane demonstrated is
again carried. Queue: recheck source207 for newer demonstrations
(source-ranked 259/262/261) — with none ready, the documented order
resumes (low-priority 81 / discretionary death work).
Consumer75/source260 (activ-260) merged as 5ea7baed6 (PR76, import
7323c8df, patch 0019): the ACID_BOLT3 and DISP_ALL maneuvers looked up the
lesser bolt's and dispel-undead's ids, so the greater-bolt and
all-monsters-dispel items were never considered; the two-token import
layers onto borg-fight-attack.c (the acid id's duplicate occurrence
targeted by case context) and verifies on the unchanged fixture (miswired
bolt3 0->52 fail-before/pass-after, lesser-bolt control byte-identical),
83 prior cases whole-log identical, merged v1 seeds unchanged.

## Death-driven enhancement evaluation (owner request2026-11-07)

Follow docs/measurement/DEATH-IMPROVEMENT-WORKFLOW.md and issue155: diagnose
deaths into evaluations/investigations/enhancement candidates, then use a distinct
scoped implementation experiment with prospective survival AND long-term progress
acceptance. Local154 links source370; it is an enhancement, not a bug carry.
This request establishes the process; it starts no gameplay implementation or
automatic batches. Bugs retain priority and existing source ownership.

Owner clarification2026-11-07: every processed death needs brainstorming and
a complete overall assessment using docs/deaths/REVIEW-TEMPLATE.md. Explicitly
consider attempted walking escape, especially after Phase Door exhaustion.
Gallant-family candidates158(theft valuation)/159(room retreat) are analysis,
not implementations; shared overall assessment lives in D0004.
