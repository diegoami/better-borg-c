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
Arrow keys step; Space plays; g jumps to a turn; i/m show gear/monsters; Escape
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

Default: at most3 new Human Warrior/default point-buy games, each at most200000
absolute engine turns and120 native wall seconds,30 seconds without progress.
The initial uint32 seed is randomly selected once and the prospective consecutive
seed list is printed/frozen before results. Explicit seeds make the request
copyable. No arbitrary class/Borg-parameter options are supported here; effective
native configuration is recorded. Never silently simulate another configuration.
Cheat death and winner respawn are off; ordinary rules/AI unchanged.

Stops after the first natural death, any operational failure, or the listed seeds
are exhausted. No forced death, automatic cap/seed enlargement, unattended job or
retry-until-favorable loop. Cap survivors are retained as cap survivors. The
stop-at-first-death sample is collection, not an unbiased survival-rate cohort.

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
