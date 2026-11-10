# Native C carry ledger

`series.json` records applied runtime correction units, not reported defects.

## Carry ordinals (patches 0035-0042, milestone 4)

| Patch | Consumer | Source | Merged as |
| --- | --- | --- | --- |
| 0035 | #133 | source240 (brand-240) | `638513e91` |
| 0036 | #137 | source232 (stairtrack-232) | `4fc3c481f` |
| 0037 | #141 | source252 (acidarc-252) | `d619eec5f` |
| 0038 | #144 | source229 (outoflight-229) | `04ab89381` |
| 0039 | #148 | source212 (mapwall-212) | `f0288cca5` |
| 0040 | #157 | source81 (CBUG-0065) | `503e7a07b` |
| 0041 | #167 | source230 (stairreturn-230) | `bc8cf805f` |
| 0042 | #176 | source247 (blowname-247) | `70993393a` |

Earlier carry ordinals (0001-0034) are recorded in
`docs/measurement/IMPACT-MILESTONE2.md`, `IMPACT-MILESTONE3.md` and
`series.json`.

The first correction is the safer available emergency swap (consumer #4 /
source #82). Its three C-only source commits include two comment cleanups;
the cumulative code has one guarded lower-danger comparison. The second carry
restores combat-message reactions after knockout (consumer #7/source #14). Its
measured benefit is restored information, not a proved survival improvement.
The third carry prevents a regeneration cast during preparation scoring
(consumer #15/source #110): selected spells execute once. The authoritative
live adoption state is the issue board. The fourth carry reads temporary cold
protection for cold melee (consumer #17/source #26); its native HP/mana
counterexample remains part of the verification.

For each carry add its consumer/source issue URLs, original reviewed source
commit, applied product commit, immutable patch path and verification/evidence
link. Store a copyable C-only `.patch` here (for example `git format-patch -1
--stdout SOURCE_COMMIT`). Preserve authorship via cherry-pick -x or git am and
record adaptations explicitly. Patch copies are required in the same adoption
PR; a patch file alone never means carried. Keep unrelated fixes separate.

When upstream incorporates a correction, verify the replacement and interactions
before retiring its active patch. Preserve the historical ledger record and
patch/evidence links with the replacement commit; do not delete history or infer
closure merely from a patch file disappearing. `patch-active` is independent
of carried/fixed status. No hand-maintained live-state overview table is used.

The fifth carry includes the left ring in both lookup/activation loops
(consumer #20/source #78). Both one-loop alternatives are retained as negative
controls; ring readiness and right-hand preference stay unchanged.

The sixth carry corrects the elapsed-time and first-use conditions for CCW
hesitation (consumer #31/source #77). Recent-drink conservation can leave an
injury untreated on that call; preserve that counterexample and emergency bypass.

The seventh carry matches the complete unseen pronoun It, keeping visible
Itangast recognized (consumer #36/source #102). Four true-unseen/ogre controls
remain unchanged; measured benefit is one potion, not combat or survival.

The eighth carry excludes a projectile caster from intervening obstacles
(consumer #40/source #279). Real blockers/endpoints remain; the hill-giant
escape loses18->29HP and costs2mana, so no uniform safety claim. Independent
per-spell source64 remains an explicit alternative, not part of this patch.

The ninth carry resets projectile classification for each monster spell
(consumer #44/source #64). It preserves the source279 helper as a separate
removal unit; real-blocker storm damage59->54 costs1scroll and remains a hit.

The tenth carry bounds glyph removal after a failed creation
(consumer #48/source #118). Source evidence demonstrates a later heap write;
the unchanged evidence fixture only passed phaseB while pristine projection
zeroed the mage's bolts at the caster's own grid, an eligibility the carried
0008 fix removes. The tracked adapted scenario
(tools/glyph-tracker-scenario.c, Uldor summoner at distance 2) verifies the
real failure message, the -1 count, the defended creation and the
heap-buffer-overflow WRITE on the actual product core; all 60 prior fixture
cases stay whole-log identical. See docs/measurement/GLYPH-TRACKER.md.

The eleventh carry stops a targetless missile launch from reading the item
before the pack and firing garbage (consumer #51/source #254). The dead
b_n < 0 guard becomes a live b_k < 0 guard; real-target and simulated
controls stay unchanged.

The twelfth carry stops the Teleport Other skip list one entry past the
count (consumer #54/source #67). The stale leftover slot suppressed an
unlisted monster and inflated the cast value; the layered borg-danger.c
module equals the eleven-carry module plus the one-comparison import, and
the no-morgoth/single controls stay unchanged.

The thirteenth carry rates Dispel Life against living monsters like the
game does (consumer #57/source #248). The inverted double filter rated the
spell below doing nothing against every enemy; the OR-filter matches the
game's drain and the undead/bolt controls stay unchanged.

The fourteenth carry tests the arc angle against the scanned grid instead
of the spell target (consumer #60/source #253). An off-arc bystander no
longer inflates the arc's coverage; the in-arc control stays unchanged.

The fifteenth carry re-acquires the Borg's own grid before the munchkin
stair tests (consumer #63/source #244). The stale neighbour pointer queued
a take-stair key on plain floor; the on-stair control stays unchanged.

The sixteenth carry guards Vampire Strike on the chosen target's distance
(consumer #66/source #257). A distant bystander no longer vetoes the cast;
both-close and distant-only controls stay unchanged.

The seventeenth carry accumulates weapon slay traits across equipment
slots and derives the kill traits (consumer #69/source #239, priority
high). A weaponless light slot no longer erases the wielded weapon's
slays; the nonanimal control stays unchanged.

The eighteenth carry guards queued detection reactions with panel bounds
(consumer #72/source #290, priority high). A stale reaction after a level
change to a one-panel-high cave no longer reads and writes past the
detection arrays; the fresh-reaction control stays unchanged.

The nineteenth carry looks up the activation ids the maneuvers describe
(consumer #75/source #260). The greater acid bolt and all-monsters dispel
items are considered; the correctly-wired lesser-bolt control stays
unchanged.

The twentieth carry scopes the reserve-bolt hitpoints veto to near
monsters (consumer #78/source #258). A distant tough monster no longer
vetoes the emergency bolt for the one nearby weak monster; the
kobold-only control stays unchanged.

The twenty-first carry applies the teleport-reserve penalty once
(consumer #81/source #259). The fixed-six block that duplicated every
class reserve is removed; the out-of-band control stays unchanged.

The twenty-second carry breaks the LOS-dispel beam walk at arrival
(consumer #84/source #326, priority high). The blast scan runs when it
should, the launcher no longer leaks -1, and the orb-ball control stays
unchanged.

The twenty-third carry values the staff-holiness activation as the LOS
dispel it is (consumer #87/source #262), stacked on the losdispel
arrival break. The single-target bolt control stays unchanged.

The twenty-fourth carry scores Blind Creature's Frighten as fear, not
confusion (consumer #90/source #261). The blind maneuver values exactly
what the dedicated Frighten maneuver values; the dedicated control stays
unchanged.

The twenty-fifth carry terminates multibyte screen text within its
character limit (consumer #93/source #287). The full 81-byte text is
terminated; the 80-byte ASCII control stays unchanged.

The twenty-sixth carry releases the calculation pointer array on free so
reload cannot overwrite and leak it (consumer #96/source #325). Reload
still evaluates to 7; the single-parse control stays unchanged.

The twenty-seventh carry rejects stale melee targets on the player's own
grid (consumer #99/source #322). Nothing is queued for that stale target;
the genuinely adjacent-target control stays unchanged.

The twenty-eighth carry bounds out-of-light glow collection to the
1536-entry arrays (consumer #102/source #311). The overflowing write is
gone; the thousand-grid control stays unchanged.

The twenty-ninth carry counts an artifact's light modifier only once
(consumer #105/source #238). The Phial reports 4 rather than 8; the
flag-based Wooden Torch control stays unchanged at 2.

The thirtieth carry makes the surrounded check's trap test part of its
exclusive wall/floor chain (consumer #109/source #312). Trapped walls no
longer count twice; the plain-wall control stays unchanged.

The thirty-first carry weighs one weapon rather than the whole stack for
home-inventory blows (consumer #113/source #313). Borg and engine agree
at two blows for the ten-rapier stack; the single-rapier control is unchanged.

The thirty-second carry clears both lunal flags when the town stair-scum
bail exits (consumer #117/source #314). The full-pack control leaves both
flags set and stays byte-identical.

The thirty-third carry frees temporary operator-block backing arrays
(consumer #121/source #324). Formula value 7 and the bare-constant control
stay byte-identical; the two operator-array leaks are gone.

The thirty-fourth carry frees token-list backing arrays with calculations
(consumer #124/source #323). Functional free/control logs are unchanged;
with opblock-324 already carried, the token-only 80-byte leak is gone.

The thirty-fifth carry counts the brand-ammo need once per stack
(consumer #133/source #240). The duplicated brand-the-ammo test in
borg_notice_ammo() is deleted; the two-arrow control below the five-stack
threshold stays byte-identical at zero.

The thirty-sixth carry stops re-adding the known up staircase in stair
scum (consumer #137/source #232). The up-stair scan breaks on a match
like the down-stair scan; the fresh-discovery control stays byte-identical.

The thirty-seventh carry counts the south and east edges of ball and arc
blasts (consumer #141/source #252). The four blast-loop bounds are
inclusive; the near and empty controls stay byte-identical.

The thirty-eighth carry starts the out-of-light maneuvers when the light
is about to burn out (consumer #144/source #229). The entry test no
longer swallows its own about-to-burn-out clause; everburning lights
keep their NO_FUEL guard and the lit/everburn/dead controls stay
byte-identical.

The thirty-ninth carry takes the map pass's old-wall capture before the
grid feature is overwritten (consumer #148/source #212). Door
close/open transitions under the Borg now invalidate the stale flow,
knowledge, icky flags and stamps; the no-change control stays
byte-identical.

The fortieth carry drinks recognized Enlightenment potions in the
dungeon (consumer #157/source #81). The missing quaff call is added
after the town guard; the town, unknown-flavor, unrelated-potion and
Augmentation controls stay byte-identical.

The forty-first carry reports acting after queueing the out-of-light
stair key (consumer #167/source #230). The think loop no longer treats
the queued '<' as disowned; the lit and dead-no-stairs controls stay
byte-identical.

The forty-second carry stops the blow-effect name lookup before its NULL
end entry (consumer #176/source #247). A made-up name no longer
segfaults the lookup and resolves to MONBLOW_NONE; the in-table name
still resolves.

The forty-third carry marks the excavated vault grid dark, as its comment
says (consumer #188/source #236). The duplicated GLOW set becomes DARK;
the no-target control stays byte-identical.

The forty-fourth carry visits the Borg's own grid in the call-light
scan (consumer #196/source #231). The never-taken open-doorway case
now repairs the doorway glow mark from the game; the plain-lit-floor
control stays byte-identical.

The forty-fifth carry considers gloves as armour-swap candidates
(consumer #201/source #205). Free-action gauntlets in the pack are now
chosen when the Borg has no free action; the plain-glove and
free-action-already-worn controls stay byte-identical.

The forty-sixth carry clears object-detection panel flags on a new level
(consumer #205, adopting source219). The depth change now clears
borg_detect_obj alongside trap/door/evil; the same-level control stays
byte-identical.

The forty-seventh carry makes the Maim Foe real pass return the best
tracked score (consumer #214, adopting source256). The chooser's re-run
of the winning attack reported the last-scanned monster's score; it now
returns b_d like the simulation pass already did; the single and none
controls stay byte-identical.

The forty-eighth carry answers the endgame recall-depth prompt with 'y'
as its comment says (consumer #216, adopting source310). The maxdepth-99
branch said "Do reset Depth" and then answered 'n'; it now answers 'y'
like the generic branch; the generic and mismatch controls stay
byte-identical.

The forty-ninth carry records a flow grid as danger-checked only when the danger
check applies (consumer #212, source #404). Desperate, lunal, munchkin and digging
flows retain their movement permissions without caching unchecked grids as safe
for later normal routing. Both writers are corrected; thresholds and escape
intent are unchanged. Product native before/after and partial-fix controls are
verified; impact measurements remain separate. `FLOWCACHE-404` identifies the
native report, not an invented CBUG catalogue number.

The fiftieth consumer carry restores the dead Floors branch in the map
update (consumer #224, adopting source213). The 2023 reorg transcribed
FEAT_FLOOR as FEAT_NONE so the branch never ran; it now marks glowing
floors via square_islit() like the original CAVE_GLOW test, and the
flow-toward-light consumer sees the flagged grids again (0 to 484
targets on the evidence fixture; the perm-wall control stays
unflagged).

Source250 (consumer #200) is not a new carry: its reader correction, the
`ii <= borg_tp_other_n` to `<` bound in `borg_danger_one_kill()`, is the same
one-token change already applied by patch 0012 (source67, consumer #54). The
cherry-pick of the source commit is empty on main. It is recorded as
`also_adopts` on the 0012 entry and verified on source250's own fixture in
`docs/measurement/TP-OTHER-READER.md` (stale-hit 0 to 179, controls
byte-identical). No ordinal is consumed and no runtime source changed.

The fifty-first carry only raises the munchkin stair range when it increases
(consumer #242, adopting source245, owner decision on the source issue). The
adjustment `(clevel - 10) + (10 - depth)` is negative below character level
10, so a level-5 Borg at depth 10 had its range cut from 8 to 3 and stopped
power-climbing toward visible stairs; it is now gated on `clevel > 10`. The
unchanged fixture flips the climb decision (0 to 1). Behaviour-active in
munchkin mode below level 10; no survival claim.

The fifty-second carry resets the Borg clock gracefully at the overflow
threshold instead of aborting (consumer #245, adopting source246, owner
decision on the source issue). `borg_think_dungeon()` aborted 2900 ticks before
the reset in `borg_think()` could run; it now performs the same reset and keeps
playing, with the old check left as a failsafe. The unchanged fixture flips the
Borg from inactive (clock frozen) to active (clock 1). Not reachable in the
20000-turn cohort; no survival claim.

The fifty-third carry makes the excessive-danger level flee fire for ordinary
Borgs instead of only Morgoth-ready ones (consumer #247, adopting source156,
owner decision on the source issue): the condition was inverted relative to its
comment. Three-mode fixture flips the ordinary case (no flee to flee) and the
Morgoth case (flee to no flee); the hurt control is byte-identical. Behaviour-
active: v1 seed 29 diverges and later dies; recorded as observed, no claim.

The fifty-fourth carry compares current mana with the maximum in the recall-wait
mana branch (consumer #250, adopting source157): the old test compared current mana
with itself and never fired. The unchanged source fixture stays red on the layered
product because patch 0053 flees first; an adapted one-line fixture (Morgoth-ready)
proves fail-before/pass-after (restore 0 to 1) and the interaction is asserted.

The fifty-fifth carry heads for the nearest free staircase when desperate
(consumer #252, adopting source153): the search kept the farthest for both up and
down stairs. Three-mode fixture flips both two-staircase cases and keeps the
single-staircase control byte-identical. Behaviour-active; v1 outcomes unchanged.

The fifty-sixth carry judges each back-away grid on its own (consumer #254, adopting
source155): the monster-adjacent flag is reset per candidate and a trap skips only its
grid instead of ending the scan. Three-mode fixture flips the monster and trap cases;
the healthy control is byte-identical. Behaviour-active; v1 cohort mixed (seed 29 saved,
seed 47 lost), recorded as observed.

The fifty-seventh carry stops reading a borg.txt integer value at the first unexpected character (consumer #257, adopting source141): a malformed value made the parser spin forever. Fixture: hang (exit 2) to clean default; valid control byte-identical.

The fifty-eighth carry negates a setting only when a number follows the minus sign (consumer #258, adopting source142): a bare minus flipped the stored default (127 to -127). Fixture: -127 to 127; valid and negative controls byte-identical.

The fifty-ninth carry keeps default settings when borg.txt cannot be read or written (consumer #259, adopting source144): the configuration was NULL and the Borg crashed. Fixture: crash (exit 3) to clean default; present control byte-identical.

The sixtieth carry skips an unidentified single item in the sell count instead of
returning zero (consumer #261, adopting source134): a full pack with one such item looked
empty and the Borg dived instead of selling. Three-mode fixture flips the full-unid case
(sellable 0 to 15, stays up); the full control is byte-identical; v1 traces identical.

The sixty-first carry keeps a drained Borg from diving regardless of its earlier
direction (consumer #263, adopting source235): the guard sat behind a dead `g` gate and
now applies unconditionally. Fixture: one power-dive note to none. v1 traces identical.

The sixty-second carry starts the Resist Poison potion reward loop from zero (consumer #266, adopting source184): a stale counter left by the food loop lost the reward with low food (900 to 0). Fixture apples 0 to 900, rations byte-identical.

The sixty-third carry counts a warrior's Resist Poison potions from zero (consumer #267, adopting source185): the loop continued the Resist Cold count (900 instead of 2400). Fixture cold 900 to 2400, plain byte-identical.

The sixty-fourth carry runs the spastic-search reverse flow unoptimized (consumer #268, adopting source146): the optimized spread stopped at the Borg's own grid and never produced a move. Fixture middle and corner: moved 0 to 1; far control byte-identical.

The sixty-fifth carry runs the Sea of Runes reverse flow unoptimized (consumer #269, adopting source345): the optimized spread stopped at an existing centre rune and never selected outlying runes. Fixture center: progress 0 to 1; offcenter control byte-identical. With 0064 the v1 seed-47 death of 0056 does not occur (pair measurement).

The sixty-sixth carry reads the swap weapon's acid resistance from its acid element instead of its electricity element (consumer #270, adopting source199): a weapon resisting electricity was counted as acid-resistant. Four-mode fixture flips elec and acid; the fire and none controls are byte-identical.

The sixty-seventh carry leaves munchkin mode while poisoned or hallucinating (consumer #280, adopting source403): stair travel does not age the world clock, so the timed ailment could never wear off and the run froze. Decision-level fixture flips the ailing case (stair_directed 1 to 0); the clean control is byte-identical. The end-to-end stalls are not claimed resolved.

The sixty-eighth carry bounds the screen-text conversion by the caller's buffer size (consumer #93, adopting the revised source287 fix e7f670fa4): the carried character-count bound (0025) let wcstombs write past the caller's 1024-byte buffer on a wide terminal showing multibyte text (177 guard bytes overwritten; AddressSanitizer stack-buffer-overflow, WRITE of size 1201). The sized bound truncates at 1020 bytes and terminates; the multibyte and ASCII cases stay byte-identical.

The sixty-ninth carry tests the permanent-glow flag for floors in the map update (consumer #224, adopting the revised source213 fix c316a65b2): the carried glowtrace reading (0050, square_islit) treated every floor inside the Borg's own light radius as permanently glowing, so flow-toward-light chased targets the Borg was already lighting. A floor is now glowing only when the game flags SQUARE_GLOW; torch-lit floors take BORG_LIGHT instead; the glowing, door and unlit cases stay byte-identical.

The seventy-first carry keeps the last character of parsed pain messages (consumer #287, adopting source197): borg_get_parsed_pain allocated strlen+1 for a ' '+text+NUL entry, so four monster status endings ('can move again', 'falls under your spell', 'no longer under your control', 'shimmers for a moment') parsed short and queued no reaction. Allocation is strlen+2 now; the stun and hurt controls are byte-identical.

The seventy-third carry values a swap weapon's troll slay by its real multiplier (consumer #289, adopting source201): a flat (dam*2)/2 kept a Slay Orc swap and offered the better Slay Troll mace for sale. The troll mace is kept now; the plain-mace control is byte-identical.

The seventy-fourth carry compares with == in the don't-crush-cool-stuff drop checks (consumer #290, adopting source136): the inverted tests protected the wrong items, and a desperate drop threw away a spare sellable amulet while keeping junk. Salt Water goes, spare amulets stay; the protected-potion and level-30 controls are byte-identical.

The seventy-fifth carry keeps the skip count across the best-equipment search (consumer #294, adopting source85/CBUG-0069): the skip counter was declared inside the search loop, so one blocked change (full pack or home) made every remaining planned change get skipped and the whole best-stuff plan dropped. The counter is declared once before the loop now; a change that can still be made (wearing a cloak into an empty slot) is tried again. The roomy and nocloak controls are byte-identical.

The seventy-sixth carry starts the spare lantern scan at the first lantern (consumer #296, adopting source90/CBUG-0074): with no flask of oil the refuel scan started at borg_slot, which returns the last lantern; an empty or Everburning last lantern ended the scan, so a fueled spare earlier in the pack was never used and the wielded lantern ran dry. The scan walks the pack from slot 0 now; the single-lantern control is byte-identical.

The seventy-seventh carry counts Banishment scrolls in the home score (consumer #298, adopting source54/CBUG-0038): the scroll scan only counted Mass Banishment, so the num_genocide home reward was always zero and the Borg never kept a Banishment scroll in the home. Banishment is counted now; the Mass Banishment control is byte-identical.

The seventy-eighth carry tests current hit points, not the item count, before banishing with the artifact (consumer #305, adopting source37): the artifact defence could banish while too hurt to afford it or skip when healthy. The hurt control is byte-identical.

The seventy-ninth carry keeps the multiplier-kill timer when checking whether to rest (consumer #306, adopting source149): on the same turn as a multiplier kill the borg rested one turn it should not have. The recent control is byte-identical.

The eightieth carry avoids every shop entrance that is not the goal shop (consumer #307, adopting source125): the avoidance covered only one layout case and the borg could step onto another shop while passing it. The offrow control is byte-identical.

The eighty-first carry lights the grids beside the west edge of the lantern radius (consumer #309, adopting source40): the west block added grids two rows above and below (already covered by the north/south blocks) instead of one row, so grids one row off and two columns west were never marked lit and a monster standing there counted as never-in-light. The east control is byte-identical.

The eighty-second carry credits stat and other modifier bonuses in the item value guess (consumer #311, adopting source70): items whose worth is in their modifiers were misvalued and the lesser item was sold. The statring and speed modes flip; the nomods control is byte-identical.

The eighty-third carry removes the unreachable second amulet tier from the home score (consumer #312, adopting source47/CBUG-0031; owner decision 2026-11-08 option C): a cleanup with no behaviour change — the kit's four amulet-count controls are byte-identical before/after.

The eighty-fourth carry tests the light beam's panel-edge rule against the row on the panel (consumer #316, adopting source88/CBUG-0072): north/south beams were refused below dungeon row 20 on a 22-row panel because the rule compared the absolute dungeon row instead of the row on the panel. The scrolled and scrolled_south modes flip; the top control is byte-identical.

The eighty-fifth carry removes the dead stun test from the HURT blow danger (consumer #329, adopting source62/CBUG-0046; owner decision 2026-11-08): the never-true `z > d_dice * d_side` test and its +200 are dead code — the meaningful kick/KO fudge stays. The kit's four blow-mode controls are byte-identical before/after.

The eighty-sixth carry aims Dimension Door only at a known empty floor grid (consumer #335, adopting source21): the escape cast aimed at the lowest-danger grid in a 100x100 box without checking the borg could land there — usually unseen granite — and the game then landed it elsewhere, possibly back in the escaped room. The granite mode flips; the open control is byte-identical.

The eighty-seventh carry looks for poison and cut cures in the Alchemy shop (consumer #336, adopting source23): a poisoned or bleeding borg flowed to store index 3 — the Bookseller in 4.2, not the Temple — and bought nothing; cures are in the Alchemy shop, index 4. The poisoned and bleeding modes flip; the healthy control is byte-identical.

The eighty-eighth carry skips dead object entries in the Lunal mode take routine (consumer #338, adopting source72): the dead-entry test checked the kind record's address (never NULL) instead of the kind index, so forgotten entries at the level corner became flow targets. The dead-entry mode flips; the live-only control is byte-identical.

The eighty-ninth carry scores a spastic search candidate by its own search count (consumer #288, adopting source147, un-deferred): the visitation penalty read the north-west neighbour's count instead of the candidate's own, so the flow re-picked already-searched grids and refused fresh ones. Carried on a consumer-designed fixture for the 0064-corrected reverse flow — the source kit's choreography exercises nothing under 0064, as documented on the deferral. The mismatch mode flips (searched grid → fresh grid); the consistent control is byte-identical.

The ninetieth carry lets a foodless Borg buy Remove Hunger at the Alchemist (consumer #359, adopting source18): the no-food store filter skipped store 4, the starving check let any scroll through, and the scrolls were never counted as food — so a starving Borg with gold chose no shop at all. The starving mode flips; the general_food and fed controls are byte-identical.

The ninety-first carry zaps a Rod of Teleport Other in the tele-away defence (consumer #361, adopting source549): the defence accepted the spell, an activation and a charged wand but not the rod, so a rod-only Borg kept meleeing a dangerous monster. The rod mode flips; the wand and weak controls are byte-identical.

The ninety-second carry gives the healing-chance adjustments the direction their comments state (consumer #363, adopting source364): fighting a unique, the danger-at-current-hp case, and the risky adjustment all had flipped signs, so a borg in real danger skipped healing and a risky borg healed more. Three modes flip as recorded; the control is byte-identical.

The ninety-third carry restores the home ware when a home-buy trial is skipped (consumer #365, adopting source19): the trial quantity was taken off the ware copy before the pack-room checks and the skip paths left it reduced, so a single home weapon was seen at quantity zero and the backup-weapon step skipped it. The single mode flips; pair is a second disclosed flip on this product (self-check False→True, outcome row matches the kit); the roomy and stack controls are byte-identical.

The ninety-fourth carry counts the newest entry in the recent sale and purchase lists (consumer #367, adopting source20): the writers stored the write index as the count, so readers never checked the most recent sale or purchase — rations stored at home were taken straight back out. The rations-only mode flips; the with-recall control is byte-identical.

The ninety-fifth carry counts a Rod of Teleport Other in BI_ATPORTOTHER (consumer #369, adopting source560): the availability trait only counted wand charges and the spell, so the rod never raised borg_power and shops never bought one. The rod mode flips; the wand and mage controls are byte-identical.

The ninety-sixth carry lets every class but Mage and Rogue buy the Black Market Rod of Teleport Other (consumer #371, adopting source17): the class exception read != Mage && == Rogue, applying to Rogues only — Rogues saved for a rod they do not need and other classes fell back to the general rule. The warrior and rogue modes flip as the kit records; the mage control is byte-identical; the kit's warrior-buy informational mode diverges on this product (disclosed) because the carried sibling rod fixes let the warrior complete the purchase.

The ninety-seventh carry keeps panel scans inside the Borg's map on large terminals (consumer #373, adopting source348): three panel scans indexed past borg_grids when the terminal showed more rows or columns than a level has — a crash on tall terminals and silent out-of-bounds reads on wide ones. Verified with ASan phases: the tall modes report the global-buffer-overflow READ of size 8 (the borg_grids row pointer) and the wide modes the heap-buffer-overflow READ of size 2 (the grid byte) from their own scan function before the fix, and pass report-free after. Memory-safety carry per the 0068/0070 contract.

The ninety-eighth carry records a visible Rune of Protection on the Borg's map (consumer #375, adopting source295): the glyph flag was only set inside the disarmable-player-trap branch, so a visible rune was invisible to the Borg's map and it read a second rune onto the same grid, wasting a scroll and a turn. The rune mode flips; the floor and trap controls are byte-identical.

The ninety-ninth carry applies the Necromancer lit-square penalty on any lit square (consumer #377, adopting source296): the Borg's spell-failure estimate added the +25 penalty only for its own light, so a Necromancer in a lit room without a light cast spells that were far riskier than estimated. The lit mode flips (estimate 8% -> 33%, matching the game, spell refused); the dark and mage controls are byte-identical.

The hundredth carry takes the stairs alone when a stair escape is chosen (consumer #427, adopting source34): five escape steps tested the up staircase inside the Phase Door condition, so `borg_escape_stair()` queued the climb key `<` and the rest of the condition still queued a phase or a teleport after it - the borg did not simply climb. The staircase is now its own branch. The `upstair` and `antisummon` modes flip from a queued phase/teleport to a single climb key; `downstair`, `floor` and `climb` are controls and byte-identical.

The hundred-and-first carry skips the items the Borg marked bad when scumming in Lunal mode (consumer #429, adopting source73): the classification was computed and its "Lunal Item" notes written, but never read, so every entry that reached the take step became a target and the Borg walked to junk it had just rejected. The dagger mode flips from walking to the item to skipping it; the gold control is byte-identical. Two fixture adaptations are disclosed in the doc: the source kit's profile blob is a git error string, and the product's munchkin-by-class override is disabled for the fixture.

Correction to the hundred-and-first carry (2026-11-10, patch `0101a`): the skip applies only outside munchkin mode. Unrestricted, it also removed the items munchkin mode collects to sell, the take flow returned false more often, and the frozen cohort began oscillating climb/dive at shallow depth (seeds 11/29/47 ended 2-3 levels shallower). Restricted to the Lunal scumming path the defect was reported for, the cohort reproduces the pre-carry traces byte-for-byte.

The hundred-and-second carry judges each monster on its own in borg_flow_kill() (consumer #431, adopting source98): the per-monster skip flag was not reset, so one skipped monster suppressed every later one, and the hallway test ran inside the accumulation loops against a partial count. The `hall` mode now skips and the `leak` mode now flows; `hallctl` and `reverse` are byte-identical controls.

The hundred-and-third carry divides armour by the monster's to-hit in the melee danger estimate (consumer #437, adopting source63): the armour term was divided by one instead of by the to-hit, so the partial estimate floored at the 5% minimum for ordinary monsters and a sleeping brute was shot at; a separate unique-only branch computed a different formula for the same quantity. The partial danger now matches the full figure and the brute is not shot; the wretch control is byte-identical.

The hundred-and-fourth carry measures item pickups from the nearest up staircase (consumer #440, adopting source71/CBUG-0055): the three pickup flows each scanned the known up staircases for the nearest one, but the scan kept the farthest (`/* skip the closer ones */ if (b_j >= j) continue;`), so every leash test measured items against a distant staircase — a level-1 Warrior standing by an up staircase ignored a Flask of Oil three steps away in all three flows once a second staircase 55 steps away was known. The `take`, `scum` and `lunal` modes flip from ignoring the flask to stepping toward it; the single-staircase `control` is byte-identical.

The hundred-and-fifth carry widens the no-rest-after-prep timer so it cannot wrap (consumer #443, adopting source108/CBUG-0092): `borg.no_rest_prep` was an `int16_t` while the code stores character level × 1000, so from level 33 the value went negative and the resting checks treated the timer as expired — the Borg rested straight after casting Protection from Evil or a similar prep spell. The level-35 `pfe` mode flips from resting to refusing; the level-30 `clevel30` control is byte-identical.

The hundred-and-sixth carry keeps the current depth's preparedness reason from being overwritten (consumer #446, adopting source234): `borg_prepared()` formats every reason into one static buffer, and `borg_leave_level()` held the current depth's pointer across three later calls, so the "heading up / returning to town / climbing (too deep)" notes printed a later depth's reason and the "Collect from house" test read a later depth's text - the return-to-town-to-collect decision could be missed. The level-50, depth-99, `borg_no_deeper = 100` mode flips from walking to a staircase to collecting from home and reading Recall; the `default127` and `prepared97` controls are byte-identical.

The hundred-and-seventh carry tests constitution for the constitution-drain blow fear (consumer #448, adopting source61/CBUG-0045): the extra fear added when a con-drain blow would leave the Borg below 8 constitution read strength (`BI_CSTR`) instead of constitution (`BI_CCON`), so a low-constitution Borg was not scared of the drain and a low-strength one was. The `lowcon` and `lowstr` modes flip; the `neither` and `bothlow` controls are byte-identical.

The hundred-and-eighth carry clears the ranged danger when Crush would kill the monster (consumer #450, adopting source66/CBUG-0050): the second Crush block assigned `v1 = 0` instead of `v2 = 0`, so the ranged danger kept the adjacent monster's value and a caster or archer that should finish it with Crush did nothing. The `caster` and `archer` modes flip from no action to a killing Crush; the `melee` and `tough` controls are byte-identical.

The hundred-and-ninth carry tests for granite, not granite-or-above, in the ranged move check (consumer #452, adopting source68/CBUG-0052): the ranged simulation used `feat >= FEAT_GRANITE` while the melee branch uses `==`, and feature values are not ordered, so rubble and every feature above granite counted as impassable walls - a monster there was invisible to the ranged estimate, danger read 0 and the borg did not flee. The `rubble` mode flips from danger 0 to 208 and takes Recall; the `floor` and `granite` controls are byte-identical.

The hundred-and-tenth carry makes Shoot'N'Scoot read the danger of the adjacent monster (consumer #454, adopting source100/CBUG-0084): the scoot check asked `borg_danger_one_kill()` about `kill->pos` but passed `i`, the monster's index in a different list, so the estimate mixed one monster's position with another monster's data. The `north` mode flips from shooting and reading Phase to doing neither; the `south` and `pack` controls are byte-identical.

The hundred-and-eleventh carry finds the first empty pack slot when the pack is empty (consumer #457, adopting source60/CBUG-0044): the backward scan had no break for an empty pack, so the function returned -1 ("no room") and a starving Borg with nothing in its pack would not buy food. The `empty` mode flips from no purchase to buying food; the `oil` control is byte-identical.

The hundred-and-twelfth carry only drinks cure potions for food when actually hurt (consumer #459, adopting source80/CBUG-0064): the "consume in order, when hurting" test read `BI_CURHP <= BI_MAXHP`, always true, so a weak Borg at full health drank a Cure potion before casting Remove Hunger. The `fullhp` mode flips from quaffing to casting; the `hurt` control is byte-identical.

The hundred-and-thirteenth carry fixes the left-ring duplicate check in the best-gear search (consumer #461, adopting source86/CBUG-0070): the left-ring branch compared against the not-yet-chosen right slot and read stale data, so the last ring tried on the right was never tried on the left and a Borg that should wear two different rings could leave one slot unfilled. The `swap` mode now wears both the new and the kept ring; the `mirror` and `empty` controls are byte-identical.

The hundred-and-fourteenth carry restores the pack entry after each home swap trial (consumer #462, adopting source31/CBUG-0012): the weapon and armour trials zeroed the hole quantity instead of restoring the saved pack record, so when the hole was the Borg's current swap slot the carried backup vanished from the model and the Borg bought/stored/retrieved the wrong item. The `swap-held` mode now keeps the model matching the game; the `no-weapon-swap` and `no-candidate` controls are byte-identical.

The hundred-and-fifteenth carry resets the home-grab skip flag for each ware (consumer #464, adopting source29/CBUG-0010): `skip_it` lived outside the item loop and only ever became true, so after one sold item matched, every later home ware in the pass was skipped and useful wares stayed at Home. The `stored-first` mode flips from not grabbing the Scroll of Light to grabbing it; the `stored-last` and `no-history` controls are byte-identical.

The hundred-and-sixteenth carry restores staff and wand charges after home-sell trials (consumer #466, adopting source132/CBUG-0116): the trial took a stackable item out of the pack, storing its charge count in `charge_each`, and the restore path put the quantity back but not the charges - the model saw an empty device, so the Borg took the item out of its Home instead of storing a charged device. The `stack` mode flips from taking the Recall out to storing the device; the `stack-emptyhome`, `single` and `none` controls are byte-identical.
