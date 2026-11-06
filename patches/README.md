# Native C carry ledger

`series.json` records applied runtime correction units, not reported defects.
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
dispel it is (consumer #86/source #262), stacked on the losdispel
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
