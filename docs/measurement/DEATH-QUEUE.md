# Next owner replay and bounded death collection

Owner clarification: `replay_next_death` opens a death the owner has not reviewed.
It does not automatically diagnose, brainstorm or close technical investigations.

From the repository root:

```sh
./replay_next_death.py --list
./replay_next_death.py
./replay_next_death.py --from-turn 20300
./replay_next_death.py --mark-reviewed D0006
```

Plain replay verifies the original rerun before opening the existing viewer.
Arrow keys step; Space plays; g jumps to a turn; i/e show inventory/equipment, m monsters; Escape
returns from panels and q quits. Focus the terminal/game region to receive keys.
Closing the viewer leaves review status unchanged. Mark reviewed explicitly when
finished; `--mark-unreviewed D0006` reverses that local receipt. `--case D0004`
opens a particular case even if reviewed; `--view-only` explicitly skips rerun
verification and `--verify-only` checks without opening the viewer. `--list --json`
exports the local queue. These commands make no GitHub posts.

Queue selection uses oldest dossier order, groups only the registry's verified
encounter-family mappings, and skips reviewed families and unavailable recordings.
Dossier manifest hashes are checked; replay-borg.py validates the full recording
before use. Missing/corrupt bundles and legacy seed-only dossiers stay visible in
`--list`, not silently marked reviewed. An empty available queue exits0 and says
so; it does not manufacture a game or infer a movie from a seed.

The committed `docs/deaths/owner-reviews.json` seeds the confirmed owner review of
the gallant/D0004 family. Explicit commands write atomic local overrides under
the PRIMARY checkout's `artifacts/death-workflow/owner-reviews.json`, protected by
a lock. All task worktrees share those local receipts. Owner review is independent
of assessment/action status:158/159 remain open despite owner viewing the death.
Historical comments on D0001 do not establish that its full replay was reviewed;
it has no complete recorded movie. D0002/D0003 legacy evidence and D0004/D0005
recordings are one qualified family, not four new choices.

## Collect a new replayable death

```sh
./produce_death.py
./produce_death.py --games 3 --seed 1001 --turns 200000
./produce_death.py --seeds 1001 1002 1003 --turns 300000 --timeout 120
```

Default: at most3 new random-race/class, default point-buy games, each at most200000
absolute engine turns and120 native wall seconds,30 seconds without progress.
The initial uint32 seed is randomly selected once and the prospective consecutive
seed list is printed/frozen before results. Explicit seeds make the request
copyable. No arbitrary class/Borg-parameter options are supported here; effective
native configuration is recorded. Never silently simulate another configuration.
Cheat death and winner respawn are off; ordinary rules/AI unchanged.

To look for an early death, a wall timeout or turn cap moves on to the next
fresh seeded character with the same limits. Stops after the first natural death,
a crash/stall/recording error, or exhaustion of the listed seeds. Timed-out runs
and their evidence remain recorded as wall_timeout, not deaths. No forced death,
automatic cap/seed enlargement or unattended job. Cap survivors are retained as
cap survivors. Use --games to choose a larger bounded attempt budget. The
stop-at-first-death sample is collection, not an unbiased survival-rate cohort.

At startup the command prints the requested source commit/subject and the actual
build it will run. A complete matching cache is reused automatically, including
across documentation/launcher-only commits when game/Borg sources, build inputs,
carry ledger, observer tools, binary and data still match. Provenance retains
the actual build commit; collection.json records requested and actual commits
separately. It does not pull Git changes or switch the checkout.

When a new build/update is required, the interactive offer is:
`Build/update this version before starting games? [Y/n]`. This happens before
acquiring the shared native lock or creating a collection. Declining cancels
without games. Noninteractive callers must pass `--yes` to accept a required
build; `--no-build` requires an existing matching cache. `--check-build` prints
version/cache status and exits without building, locking or running games
(exit0 matching, exit1 missing). A corrupt/incomplete exact cache is preserved
and rejected rather than overwritten. Selection is rechecked under the lock
before the build/run; no prompt holds the lock.

`--ref COMMIT` pins committed runtime source (defaultHEAD). Dirty runtime edits
are not exported. A matching full-recording observer build is cached under the
primary `artifacts/death-workflow/builds`; incomplete/changed cache entries fail
honestly. `--build PATH --ref COMMIT` reuses a supplied compatible recording build
with identical source/tool identities. First build/configure and waiting for the
shared validation lock are separate from native per-game wall limits; progress
and build logs remain visible. Failed builds are retained, not auto-retried.

All games use isolated run directories below PRIMARY `artifacts/death-workflow`;
no personal named save, backups, user settings or desktop sessions are loaded or
published. `--output PATH` must be a new directory under primary artifacts.
`collection.json` freezes the source/seeds/limits/stop rule and retains every
attempt/outcome/error, result hashes, full recording and relevant terminal stats.

A natural death invokes tools/record-death.py under the shared registry lock and
regenerates tools/aggregate-deaths.py. New `docs/deaths/Dnnnn-collected` evidence
starts UNASSESSED, uses its actual build, and enters the owner's replay queue.
`--death-issue URL` overrides the default collection discussion163; a focused
investigation should be linked during curation. Export/recording errors are
failures with preserved raw evidence, not successful completed death protocol.
Dossiers are working-tree changes requiring normal curation/commit/PR review.

After owner replay, the agent still checks feedback, qualifies replay, completes
REVIEW-TEMPLATE.md brainstorming/overall assessment and files evidence-backed
candidate investigations. A queue script never claims that analysis is complete.
Bugs remain first; collection is a direct bounded request, not an automatic queue
that pre-empts active defect work. Survival/progress experiments use the separate
DEATH-IMPROVEMENT-WORKFLOW.md process, not this first-death collector.

## Verification for this delivery

Ten focused controls cover verified-family grouping, legacy/missing/changed
recordings, viewer exit leaving owner status unchanged, reversible local review
overrides, seed-mode validation, refusal of a nonrecording build, first-death
stop/export, bounded all-cap completion, stall failure and failed-export evidence.
Existing tooling controls remain required alongside the hosted native gate.

Native smoke: actual source682143f79eeb, seed1001, one game/cap200/timeout30,
result turn_cap at200/20HP, no death or extra seed attempted. Full standalone
recording and collection manifest retained under primary
`artifacts/death-workflow/smoke-cap-1001`. This is a bounded-run check, not mortality
or death-export integration evidence; that export path uses existing tested
record-death.py plus the focused collector controls.

Queue handoff: D0004 historical original C34 recording rerun VERIFIED via
`--case D0004 --verify-only`; receipt in primary
`artifacts/death-workflow/replays/20261107T171050.115944Z/verification.json`.
Owner review ledger and historical dossiers were unchanged; no desktop window,
new natural death or personal character publication. Default queue honestly
reported no unseen available movie.

## Random characters for new exploration games

Owner request: fresh `produce_death.py` games now default to native random race
AND class. `--birth fixed` selects the old Human Warrior profile explicitly.
The native birth menus receive `*`, so the recorded game seed determines both
choices through ordinary game RNG; point buy remains the game's class-specific
default. The prospective seed list, effective input and actual native CHARACTER
are retained. A game is not described as Human Warrior merely because it used
the exploration runner.

Fresh `run-borg-headless.py NAME --turns N` characters use the same random-birth
policy and a randomly chosen seed when --seed is omitted. Explicit --seed is
reproducible, and --birth fixed remains available. Loaded saves retain their
character; visible manual birth still follows the player's choices. Frozen
ordinary measurement cohorts retain their original fixed birth unless explicitly
run with the new --random-birth option. Historical cases and baselines are not
rewritten by this new exploration default.

For a manual attempt at an alternative decision, use
`./play-from-replay.py DOSSIER --from-turn N`. It verifies the historical prefix
and loads a separate native save with the Borg off. First use offers a separate
historical helper build; existing replay engines remain frozen. See
[manual takeover and resume](RECORD-REPLAY.md#play-a-manual-alternative-from-a-recorded-turn).

## Watch or take over a collected survivor

Each completed attempt now prints `Watch:` and `Play yourself:` commands and
stores them in its `collection.json` entry. The commands apply to deaths and
living survivors alike. A timed-out movie uses `--view-only` for watching;
manual play verifies its selected prefix first. Crashed/error recordings may
have a watch-only command but are not offered for takeover.

Retrieve commands for an existing collection without builds or new games:

```sh
./produce_death.py --commands artifacts/death-workflow/collections/TIMESTAMP
```

`--timeout SECONDS` already sets the native **wall-time limit per character**
(default120seconds), separate from build/lock waiting. `--stall-timeout SECONDS`
(default30) limits an unchanged engine turn; `--turns` sets the engine-turn cap.
For example, search up to20fresh characters, allowing each60seconds:

```sh
./produce_death.py --games 20 --timeout 60
```

Wall/turn limits continue to the next declared seed. Three living timeouts are
not three completed200000-turn games or evidence that progress is good; the
engine clock can advance during unproductive town/stair cycles. All outcomes
and recordings remain preserved, and no limits or seeds grow automatically.
