# Native C carry ledger

`series.json` records applied runtime correction units, not reported defects.
Bootstrap has none. The authoritative live adoption state is the issue board.

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
