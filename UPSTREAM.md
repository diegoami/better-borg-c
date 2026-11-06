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
