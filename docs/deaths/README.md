# Native death records

Bugs always take priority. Each natural death gets a curated dossier with its actual source/build, logs, evaluation, diagnosis and linked actions. Full runs/saves/builds stay outside Git. Replays append to the case; later fixes never overwrite its identity.

Dossiers: 2; distinct starting conditions: 2; recorded death process attempts: 8 (including repeats/reference variants). This registry is not a survival-rate estimate.

| Case | Actual source | Seed | Raw cause | Death turn | Diagnosis |
| --- | --- | --- | --- | --- | --- |
| [D0001](D0001-stegocentipede/report.md) | `337e50eb6c73` | 11 | a stegocentipede | 174862 | original C behavior; defect not established |
| [D0002](D0002-gallant/report.md) | `45eac63bd9f7` | 29 | a gallant | 20445 | original C behavior; final healing ineligible under recorded danger, defect not established |

## Aggregated actions

- [Observe actual existing speed-defense eligibility and p1/p2 in the pre-fight state](https://github.com/diegoami/better-borg-c/issues/22) — investigate before changing policy; cases D0001.
- [Trace last Home/town decisions and escape-stock constraints](https://github.com/diegoami/better-borg-c/issues/22) — investigate before changing policy; cases D0001.
- [Compare pristine upstream versus carried build](https://github.com/diegoami/better-borg-c/issues/22) — completed: identical death/trace; does not establish a defect; cases D0001.
- [Observe existing heal eligibility/call order and fleeing flag before the fatal melee](https://github.com/diegoami/better-borg-c/issues/34) — investigate before changing policy; cases D0002.
- [Trace why Phase Door was exhausted and whether earlier escape was legally available](https://github.com/diegoami/better-borg-c/issues/34) — investigate before changing policy; cases D0002.
- [Compare pristine upstream versus carried build](https://github.com/diegoami/better-borg-c/issues/34) — completed: pristine/five-carry identical trace; same death on six-carry; no defect established; cases D0002.

Recurring mechanisms are grouped by canonical issue, not by number of replays. Investigations are hypotheses until native causal proof; original-C bugs route to neo-angband-tracker before source fix and consumer carry.

Create records with tools/record-death.py, curate assessment.json/report.md, then run tools/aggregate-deaths.py. Every report pins its actual build even after main changes.
