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
