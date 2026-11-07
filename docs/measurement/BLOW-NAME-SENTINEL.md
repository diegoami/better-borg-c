# Blow-name-sentinel carry: verified product scenario, ready for adoption

Consumer [176](https://github.com/diegoami/better-borg-c/issues/176), canonical
source [247](https://github.com/diegoami/neo-angband-tracker/issues/247)
(blowname-247). Fix applied as
`64046743679e0925ae6698b458a7bbf9dfa6cb19` (import of source PR397
`541e03b1e6e0bed42e0b71ec520cb6ced8f29d65`, patch
`patches/0042-blow-name-sentinel.patch`).

## Defect

`borg_mon_blow_effect()`'s name-table loop bounded itself with the full
array length, so a blow name absent from the table walked into the table's
`{ NULL, MONBLOW_NONE }` sentinel entry and `strcmp`'d against NULL. The
source receipt records a **segfault (exit 139)** when the lookup is called
with a made-up blow name — reachable from real monster blow names the Borg
has not mapped. The correction makes the bound sentinel-safe
(`i + 1 < sizeof(monblow) / sizeof(monblow[0])`), keeping in-table
resolution (HURT → MONBLOW_HURT) and returning MONBLOW_NONE (0) for
unknown names. Memory-safety defect (crash class); no survival claim.

## Pins and layered provenance

Before build: forty-one-carry `fb16560054b44899c50b8aec5ce1a2b0e35c0533`
(retained tree `../stairreturn`, normal and ASan cores, gate recorded at
that commit, source-identical to merged main `7e9fb325f` over
src/lib/CMakeLists.txt/cmake — the replay-spells feature merge changed
nothing under the build inputs). `borg-fight-attack.c` already carries
0011/0013/0014/0016/0019/0020/0021/0022/0023/0024/0037, so the verifier
proves that the source diff applied to the before module equals the
product module; the applied commit's diff body is byte-identical to the
source commit's diff. The source evidence fixture at `eea8f6e1` is used
unchanged.

## Verified results (`artifacts/b247/scenarios`, 2026-11-07)

- normal-before: **exit -11 (SIGSEGV)** — the made-up name
  `MADE_UP_BLOW_NAME` crashes the lookup before the suite can finish
  (buffered output is lost with the crash).
- normal-after: exit 0, suite 1/1 passed — `KNOWN value=1` (HURT still
  resolves) and `UNKNOWN value=0` (MONBLOW_NONE for the made-up name).
- asan-before (compiled with `-fsanitize-recover=address`, run with
  `halt_on_error=0`, exactly as the source receipt records): the sanitizer
  names the crash directly — `SEGV on unknown address 0x000000000000` in
  `borg_mon_blow_effect` (borg-fight-attack.c:93, the strcmp against the
  NULL sentinel) — alongside the pre-existing init-time
  `borg_sort_comp_hook` heap-buffer-overflow reports.
- asan-after: suite 1/1 passed, both lookups correct; the log still
  contains the two pre-existing init-time `borg_sort_comp_hook` overflow
  reports — that is the separately filed source finding #399, present on
  every sanitized `borg_init` of this pin, and its continued presence here
  is expected rather than suspicious.
- `result.json` records `verified: true` with all commands and hashes.

Retained first attempt: `scenarios-attempt1-asan-config` — the fixture's
own ASan phases originally used plain options without recover, so both
sanitized runs halted at the pre-existing init overflow before reaching
the lookup; adopted the source receipt's recorded configuration and
corrected one impossible assertion (demanding buffered output from a
crashed run). No product assertion was weakened; the crash itself is the
fail-before on the plain build.

Native gate on this core at the fix commit: **965/965 unit + 5/5 frontend**
numerically read; tooling **71/71** (the current main tooling set).
Regression matrix (`artifacts/b247-carry/regression.py`, local-only): all
**138 prior native fixture cases** match the recorded forty-one-carry
tally — 135 whole-log identical (including the stairreturn-230 cases),
the dispel-248 undead case passing with its asserted losdispel log
change, and the two dispel-259 cases asserted-red at the pinned
post-losdispel values.

## Scope and limits

Direct native lookup calls with an in-table name and a made-up name; no
game simulation runs. It proves the sentinel-safety of the lookup and its
crash, not a gameplay frequency or survival claim.

## Exact next work

1. PR from `task/carry-blowname`, agent evidence review plus required
   hosted checks, then normal merge.
2. On merged main: prepare the measurement build
   (`tools/measure-native.py prepare --observe`), run frozen v1 seeds
   11/29/47, cap 20000, wall 120, stall 30, and compare against the
   forty-carry (mapwall-lineage) run — expected behavior-neutral unless
   the Borg encounters an unmapped blow name during the cohort.
3. Mark 176 carried/open+patch-active; receipts on issue 176, source 247
   and checkpoint 1; evidence archive under `artifacts/b247-carry/`.
4. Recheck source207 for newer demonstrations; tapunlife-249 remains
   blocked (see `TAP-UNLIFE.md`); source #399 (init-time
   `borg_sort_comp_hook` overflow) is a separately owned source finding
   that needs call-site identification, native reproduction and a source
   fix before any carry.
