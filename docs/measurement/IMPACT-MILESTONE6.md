# Impact milestone 6: 13 carries and one overlap since impact v5 (patches 0051-0063)

Review package for [milestone 6](https://github.com/diegoami/better-borg-c/milestone/6): the 13
verified C bug carries after the milestone5 runtime snapshot `5384f12ed` (50 carries), patches
0051-0063 (consumer issues 242, 245, 247, 250, 252, 254, 257, 258, 259, 261, 263, 266, 267), plus
the source250 adoption that needed no new patch (consumer 200). Runtime snapshot after the last
carry's merge: `b3c825c97c8aef18b252a7fb7d9b7dceef83d586` (PR 271); measured tip `b3c825c97c8aef18b252a7fb7d9b7dceef83d586`
(docs-only commits after the snapshot). Every carry is merged, labelled carried/open+patch-active,
and receipted on its source issue.

## The 13 carries and the overlap

| Patch | Source (issue, commit @ pristine base `e473720ed`) | Applied | Merged | Consumer | Evidence pin | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| 0051 stairrange | [245](https://github.com/diegoami/neo-angband-tracker/issues/245) `c16b3e9d1` | `30bc61d37` | `ae64c39cb` | #242 | `3c9a75e20` | `STAIR-RANGE.md` |
| 0052 clockreset | [246](https://github.com/diegoami/neo-angband-tracker/issues/246) `7cc0ebbd2` | `49f9c19df` | `120ca9916` | #245 | `85ff22540` | `CLOCK-RESET.md` |
| 0053 dangerflee | [156](https://github.com/diegoami/neo-angband-tracker/issues/156) `007d45483` | `26811540d` | `9cb711cd2` | #247 | `809e556b3` | `DANGER-FLEE.md` |
| 0054 recallmana | [157](https://github.com/diegoami/neo-angband-tracker/issues/157) `57d0df063` | `8a604133a` | `b2c9db479` | #250 | `b6bd252e1` | `RECALL-MANA.md` |
| 0055 deskstair | [153](https://github.com/diegoami/neo-angband-tracker/issues/153) `627681006` | `4a88e67f9` | `f0e10ee12` | #252 | `366fd1b08` | `DESPERATE-STAIRS.md` |
| 0056 backaway | [155](https://github.com/diegoami/neo-angband-tracker/issues/155) `df5361ad5` | `86d01e947` | `20d7d4e62` | #254 | `fa0293e58` | `BACK-AWAY.md` |
| 0057 cfghang | [141](https://github.com/diegoami/neo-angband-tracker/issues/141) `45dfc9b1f` | `052129ae5` | `d4f9bb5c9` | #257 | `a3164a61b` | `CONFIG-PARSER.md` |
| 0058 cfgminus | [142](https://github.com/diegoami/neo-angband-tracker/issues/142) `6bc43e71a` | `0ceeaadbb` | `d4f9bb5c9` | #258 | `18f79a3cc` | `CONFIG-PARSER.md` |
| 0059 cfgmissing | [144](https://github.com/diegoami/neo-angband-tracker/issues/144) `8cbee6944` | `e8a50ea9f` | `d4f9bb5c9` | #259 | `1ff9ca1e5` | `CONFIG-PARSER.md` |
| 0060 countsell | [134](https://github.com/diegoami/neo-angband-tracker/issues/134) `026a42d3f` | `93cbfbda0` | `828d5eec2` | #261 | `68b23b2a1` | `COUNT-SELL.md` |
| 0061 drainedive | [235](https://github.com/diegoami/neo-angband-tracker/issues/235) `6d909bf52` | `eb89278d7` | `31e71f087` | #263 | `557c85260` | `DRAINED-DIVE.md` |
| 0062 respois | [184](https://github.com/diegoami/neo-angband-tracker/issues/184) `5e8d4c5e6` | `089acfae4` | `b3c825c97` | #266 | `af01d73cc` | `RESIST-POISON.md` |
| 0063 respoiswar | [185](https://github.com/diegoami/neo-angband-tracker/issues/185) `c056daabf` | `b81495995` | `b3c825c97` | #267 | `6f130a4ee` | `RESIST-POISON.md` |
| overlap (no patch) | [250](https://github.com/diegoami/neo-angband-tracker/issues/250) `e890819a6` | already in 0012 | `eea2eee96` | #200 | `6f6710ccc` | `TP-OTHER-READER.md` |

Every carry is a `cherry-pick -x` of one reviewed C-only source commit. Three carry an owner decision
recorded on the source issue (245, 246 and 156, each "option 1"); for the others no owner decision comment
was found on the source issue, so they are carried under the standing owner rule (RULES 13: merge verified
PRs after agent evidence review), not on a per-fix approval.

## Verification contract (what is and is not the same as milestone 5)

1. **Unchanged source fixture, normal phases only.** Each carry ran the source evidence fixture
   unchanged (runtime files byte-identical to the source run pin, asserted) on a before and an after
   build of the same tree, fail-before/pass-after on the observable, with the source's byte-identical
   controls. **No AddressSanitizer phase was run in this milestone** (milestone 5 ran four phases);
   none of these defects is a memory error the sanitizer could observe; the hang fixed by 0057 and the
   crash fixed by 0059 show as non-zero exit codes in their fixtures. The source finding #399 overflow was therefore not exercised.
2. **Rows equal the source's recorded rows value for value** for every carry. One exception is
   disclosed below (0054).
3. **Provenance** is proven per module: before module + source diff == product module, or, for patches
   that stack on an earlier patch in the same function (0058, 0059, 0063), the source change merged with
   `git merge-file` onto the before module. Each verifier also asserts that the carried file is the only
   `src`/`lib`/build-file difference from its before commit.
4. **Native gate 965/965 unit + 5/5 frontend** on every fix commit or stacked tip, read numerically;
   identical hosted numerics on every PR. Tooling tests 121 on every PR (milestone 5 ended at 97).
5. **Not done:** the accumulated prior-fixture regression matrix was **not rerun** this milestone (it was
   rerun per carry in milestone 5); the stacked PRs (cfg trio, respois pair) ran the native gate once on
   the tip, not per patch.

## Layered interaction disclosed (0054 vs 0053)

The unchanged source fixture for 0054 (recall-wait mana) stays red on the product, before and after, with
identical logs: since 0053 an ordinary Borg in excessive danger flees via desperate stairs before it reaches
the recall-wait line. This is asserted in the verifier. Fail-before/pass-after is shown on an adapted
fixture that changes exactly one source line (`ready_morgoth` 0 to 1); its rows equal the source's pristine
rows. The corrected line is reachable only when the flee branch is skipped. The source lane was told.

## Frozen v1 cohort: per-patch and cumulative

Per-patch (seeds 11/29/47, cap 20000, wall 120, stall 30, observer builds of before and after):

* identical traces on all three seeds: 0051, 0060, 0061; **not run on the cohort:** 0052 (the threshold is
  out of reach of a 20000-turn cap), 0054 (the cohort Warriors have no mana), 0057-0059 (valid default
  configuration) and 0062/0063 (not measured; a shopping divergence is possible and not excluded).
* **0053 (excessive-danger flee) changed an outcome:** seed 29 diverges and later dies to a cutpurse at
  game turn 15149 (was alive at the cap). Divergence starts at the corrected branch fleeing a floating eye.
  Investigation: [#249](https://github.com/diegoami/better-borg-c/issues/249).
* 0055 (nearest desperate staircase): seeds 29 and 47 traces diverge, outcomes unchanged.
* **0056 (back-away per grid) changed two outcomes:** seed 29 is saved (alive at the cap), seed 47 is lost
  (dies to a cave spider at turn 11780). Investigation: [#255](https://github.com/diegoami/better-borg-c/issues/255).

**Cumulative v5 to tip** (`b3c825c97c8aef18b252a7fb7d9b7dceef83d586` against `5384f12ed`, observer builds, same parameters; archive
`artifacts/m6-measurement.tar.gz`, sha256 `f5bd1833c7371b06ca147d0fb778412918557dc3ea7dfd88848ab7e8d6e66374`, 55151447 bytes, 95 members, build/source trees and saves
excluded; ignored by Git, kept locally):

| seed | v5 | tip | traces |
| --- | --- | --- | --- |
| 11 | alive at cap, level 3 | alive at cap, level 3 | diverge |
| 29 | alive at cap, level 4 | alive at cap, level 5 | diverge |
| 47 | alive at cap, level 3 | **death by a cave spider, turn 11780** | diverge |

All three traces diverge from the v5 lineage. **Two of three seeds are alive at the tip against three of
three at v5.** The loss of seed 47 is attributed by the per-patch runs to 0056 (seed 47 was alive immediately
before it and dies immediately after); seed 29's intermediate death under 0053 is repaired by 0056. Three
fixed seeds are not statistics: no survival, progress or population claim is made in either direction, and
the cohort lineage restarts at this tip.

## Exclusions and pending items (checked, not counted)

* **Ready, not yet carried:** spastic-146, glyphflow-345 and swapacid-199 (verified fixtures; next milestone).
* **prepreason-234** is not carried: the source states its native fixture is still pending.
* **staircycle-403** awaits the consumer 204 correction boundary; **tapunlife-249** stays masked by patch 0022
  (diagnosis in `TAP-UNLIFE.md`, consumer 140); **dontreact-14** is unchanged from the milestone 5 note.
* Related but separate: issues [249](https://github.com/diegoami/better-borg-c/issues/249) and
  [255](https://github.com/diegoami/better-borg-c/issues/255) (cohort deaths, diagnosis only);
  [235](https://github.com/diegoami/better-borg-c/issues/235) (D0009 starvation) is unrelated to these carries.

## Full-disclosure index: retained errors and corrections

Nothing was weakened for green. Disclosed mistakes: (1) the first source250 attempt was an empty
cherry-pick, found and proven as an overlap rather than force-applied; (2) a verifier reused a build left at
the fixed state as its "before" tree (0062), the assertion rejected it and the tree was rebuilt (recorded in
`RESIST-POISON.md`); (3) a generator wrote `MODES = ('main')` (a string, not a tuple) and the verifier
failed on it before any claim was made; (4) the stepwise cfg run failed its provenance step for 0058 because
the plain source diff does not apply on top of 0057, and the three-way-merge proof replaced it; (5) a stray
test call created a malformed duplicate issue ([#265](https://github.com/diegoami/better-borg-c/issues/265),
closed as not planned) and the body of [#269](https://github.com/diegoami/better-borg-c/issues/269) first
quoted a wrong source hash, corrected with a comment; (6) one PR command was rejected by the shell for a
heredoc and rerun from files, with nothing partially applied. Per-carry evidence archives under `artifacts/`
are ignored by Git and kept locally; every consumer issue records pins, commands, output and limits.

## Exact next work

1. Merge this document; receipt on the package issue and checkpoint 1.
2. External review of this milestone is deferred to the owner's chosen point (RULES 13); this document does
   not represent review as done.
3. Next carries: spastic-146 and glyphflow-345 (reverse-flow pair), swapacid-199; recheck the source board;
   diagnose 249 and 255 before any strategy change.
