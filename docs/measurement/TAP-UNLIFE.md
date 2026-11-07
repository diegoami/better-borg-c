# Tap-unlife carry: BLOCKED — the defect does not reproduce on the layered product

Consumer [140](https://github.com/diegoami/better-borg-c/issues/140), canonical
source [249](https://github.com/diegoami/neo-angband-tracker/issues/249)
(tapunlife-249). Candidate fix: source PR362
`21a1b9079e612adaf8108390e5ec2379ffce33b7`, applied on
`task/carry-tapunlife` as `0e8580614a45ab832762437439e11335378df920`
(patch `patches/0037-tap-unlife-real-damage.patch`). **This carry is not
merged and must not merge on this evidence**: the unchanged source fixture
cannot demonstrate fail-before/pass-after on the thirty-six-carry product.
Status: blocked, red retained.

## Defect (pristine, per the source lane)

`borg_launch_damage_one()`'s `BORG_ATTACK_TAP_UNLIFE` case computed the
mana gain as `BI_CURSP - BI_CURSP` (always zero) and rated the undead cast
at `kill->power - sp_drain` — the target's full estimated hp — overriding
the passed average damage. Pristine-measured: the chooser targets the
healthy bat (power 47) instead of the injured one (power 10, injury 82%,
kill bonus). The correction deletes the five-line `else` block so the tap
rates at real average damage. Owner intent recorded on source #249:
damage-based rating (option a).

## What the product shows (red attempt retained, `artifacts/t249/scenarios`)

All four phases, all three modes, byte-identical logs before and after
(identical `log_sha256` values; binaries and object sets differ, and the
after build provably contains the fix — `borg-fight-attack.c.o` matches the
recorded after-build objects, product binary differs from the before
binary, and provenance "before module + source diff == product module"
holds against the before build at gate commit `faa86f83b`):

- `undead`: the chooser acts (acted=1, tap_cast=1) and targets
  `* p 3 6 6 6 5 m c a` in BOTH builds — the scenario's corrected-targeting
  require fails on both. The defect does not flip the chosen target here.
- `non-undead` and `bat` controls: pass, byte-identical (expected, but
  uninformative given the undead result).

The product's undead cursor path also differs from both pristine
recordings (`2 2 2 2 2 2` before / `6 6 6 6` after): the first step is `3`
then three `6` steps — a different route that ends adjacent to the injured
bat at (14,11) from player (11,11). Unproven hypotheses, clearly labeled:
an earlier carried change to projection/valuation (candidates 0022/0024 or
the 0008/0009 shot-path family) may already mute the healthy-bat
preference or shift the chooser's target-cursor entry, or the chooser's
2% simulation paranoia may land differently at this call position on the
layered build. No attribution is claimed.

Gates that did pass: native gate **965/965 + 5/5** at the fix commit,
tooling **41/41** — recorded but NOT carry evidence for this defect.

## Why blocked

RULES 6/17: a carry needs actual fail-before/pass-after on the product, or
a documented, asserted layered interaction that still demonstrates the
defect's real effect. Here the effect is nil on the unchanged fixture, and
no product-manifesting demonstration exists. Nothing was weakened; the red
attempt is retained in full.

## Exact next work

1. Optionally diagnose the masking (which carried change removes the
   healthy-bat preference or shifts the cursor path) and construct an
   adapted product-manifesting scenario with asserted provenance — the
   glyph-0010 pattern — before reconsidering the carry.
2. Otherwise leave the fix uncarried: source249 stays canonical; borg-rs
   already keeps the misrating faithfully for its parity contract.
3. Recheck source207 for newer demonstrations; acidarc-252's source PRs
   (#382/#383) were pending hosted checks when this carry was selected.
