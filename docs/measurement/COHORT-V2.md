# Cohort v2: explicit mode configuration (owner decision 2026-11-10)

## Why the zoo restarts

Cohort v1 declared the character, seeds and cap, but **not the borg's settings**. `measure-native.py`
wrote only `borg_cheat_death` and `borg_respawn_winners` into `user/borg.txt`, so every run silently
inherited the compiled defaults. That matters because the defaults are not constant history:

- `borg_munchkin_by_class` defaults to true and forces `borg_munchkin_start` true for Warrior, Druid
  and Ranger for the whole game (owner change, PR 302);
- `borg_self_lunal` and `borg_lunal_mode` default to false, so Lunal mode is never entered by a
  default run even when the code under test lives on that path.

Two consequences made the v1 results **polluted for cross-commit comparison**, and one made a v1
result actively misleading:

1. runs on either side of PR 302 played different games while sharing a cohort name;
2. a run could not say which mode it exercised, so "neutral" could not be distinguished from
   "the change was not active" - 0101's first correction was gated on a class flag and the Warrior
   cohort compared the same code twice, which looked neutral and measured nothing.

**Owner decision: the zoo does all its experiments from scratch on explicit configurations.**
v1 results stay as historical records; they are not compared with v2 runs, with each other across
the PR 302 boundary, or used as evidence for mode-gated changes.

## What changed

- A cohort file may carry `"configuration": [...]`, one borg.txt setting per line.
- `measure-native.py` composes `user/borg.txt` from that arm plus the fixed controls, through
  `configuration_text()` (unit-tested), and records both the text (`configuration`) and its hash in
  every `result.json`.
- `measure-cohort.py` passes the arm through, so every seed of a cohort runs the declared settings.

## Arms

| File | Purpose | Settings |
| --- | --- | --- |
| `cohort-v2.json` | ordinary play, no scumming modes | `borg_munchkin_start=FALSE`, `borg_munchkin_by_class=FALSE`, `borg_self_lunal=FALSE`, `borg_lunal_mode=FALSE` |
| `cohort-v2-munchkin.json` | the product default for a Warrior | `borg_munchkin_by_class=TRUE`, both Lunal settings FALSE |
| `cohort-v2-lunal.json` | the Lunal scumming path, 200k-turn cap | `borg_self_lunal=TRUE`, `borg_lunal_mode=TRUE`, munchkin off |

The Lunal arm is deliberately long: the mode needs preparation 15 levels deeper and
`maxdepth >= depth + 15` (`borg-think-dungeon.c`), which a 20k-turn run to depth 6 never satisfies.
If it proves impractical, the alternative is an arm that starts from a deep save; that needs its
own decision and is not assumed here.

## Running an arm

```sh
python3 tools/measure-native.py prepare --ref <commit> --output /tmp/zoo/build --observe
flock /tmp/angband-validation.lock python3 tools/measure-cohort.py \
    --build /tmp/zoo/build --output /tmp/zoo/run --phase baseline --cohort docs/measurement/cohort-v2.json
```

## Rule

An experiment that does not state its mode configuration is not a v2 experiment. A configuration
counts as neutral only when the changed branch is shown to execute there (fixture or
instrumentation); otherwise it is recorded as **not exercised** (RULES 19, AGENTS).
