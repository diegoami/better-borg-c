# Local recording and verified replay (consumer134)

The owner requested full local death inspection for visible and headless games,
then selected **verified rerun plus a turn-by-turn viewer**. Future pipelines
are deferred. The separate integration lane owns the consumer bug-carry queue; this task does
not resume or override it, and introduces no tactics.

## Contract

A seed is not a complete replay recipe. Each new session freezes an exact
engine, committed runtime source/data identity, original native save or fresh
seed, initial user configuration and runtime environment/calendar context.
Logical terminal polls/events (including empty polls, peek/take and disconnect),
actual clock values, and preference/`borg.txt` bytes AT READ TIME are retained.
During replay the original game/Borg code still calculates every decision.
Only external input is supplied; game/Borg RNG is never reset at a later turn
and decisions are never substituted from the action transcript.

Every world increment and command/input boundary records actual phase/turn,
player/game/Borg RNG state and logical cells/color changes. Read-only diagnostic
gear, timed effects, Borg goals and visible/unseen monster state are separately
labeled. Native-save fingerprints at command/input boundaries use the existing
forked saver, avoiding live monster compaction. The snapshot child skips only
auxiliary CharOutput.txt generation so it cannot draw through the parent's X11
connection or consume the external-input transcript. Normal native saves still
produce their usual auxiliary output.

Serialized-world fingerprints use FNV1a64; bundle files and native save anchors
use SHA256. Verification compares ALL input/action/trace/frame streams and
starting/recent/final native save bytes, not just outcome, seed or exit status.
This is a checked observational equivalence claim, not a RAM serialization or
unqualified guarantee about undefined behavior or arbitrary future runtimes.

## Local commands

```sh
./start-borg.sh NAME --seed 29
./run-borg-headless.py NAME --turns 30000 --seed 29
./replay-borg.py RECORDING-DIRECTORY --from-turn 20340
./replay-borg.py docs/deaths/D0004-named-headless --from-turn 20340
```

Visible Borg activation stays manual. The visible wrapper preserves ordinary
save/autosave publication while isolating its frozen origin. One open descriptor
freezes an autosave inode before publishing it, avoiding native replacement
races. Different names coexist; same-name locks remain shared by both scripts.
Only heavy builds/verification/headless scenarios take the validation lock;
ordinary visible sessions do not hold it for an entire human play session.

The replay first reruns the original recorded START, then seeks in ORIGINAL
recorded frames. N in --from-turn is an absolute engine turn. From-turn does
not load a checkpoint and pretend it restores the Borg's private memory. A
session loaded from a native save can itself be reproduced from that origin;
previous sessions are linked only when a saved-state hash matches.

--verify-only emits a JSON certificate/result and no viewer; --view-only and
--dump-turn inspect original frames without a rerun claim. A failure identifies
the first mismatching stream/row/turn/field. Original bundles and named saves
are untouched. No new independent death is registered by replay.

## Qualification

Native tests use C source1b95154f65b2 (34 carries) and retain each actual
observer/binary/data/tool fingerprint. All tests use disposable saves and
isolated Xvfb displays; no test window appears on the owner's desktop.

- Fresh headless seed11 +200 and +2000: recorded and verified.
- Fresh visible seed11, ordinary birth, manual delay/Borg start/stop/save:
  recorded and verified, including complete raw trace and save bytes.
- Headless seed29, prospective+30000/wall180: natural gallant death at20445;
  complete rerun verified with all frames/actions/RNG and native save anchors.
- Visible seed29, bounded virtual-display test: natural gallant death at20445;
  complete rerun verified by the headless verifier, with the original logical
  X11 preferences, geometry, input and calendar/file transcripts.
- Loaded headless continuation retains an immutable origin and links the
  matching prior snapshot; verification is recorded in the task receipts.
- Frozen v1 non-interference controls: seeds11/29/47, cap20000/wall120/stall30,
  plain observer versus recording observer; complete traces and native
  starting/recent save bytes are compared without widening limits.
- A wrong-seed derived control is rejected as DIVERGED. Original recording
  unchanged. Changed engine/data, incomplete/legacy bundles, and state/action
  mismatches have fail-closed tooling controls.
- A PTY test exercises turn seek, original screen, gear/monster panes and exit.

D0004 and D0005 retain each mode's actual native identity, its verified repeat
and seven ORIGINAL pre-death observation windows. Their Borg notes and all23
noncheckpoint states match D0002; curator qualification groups them into that
existing encounter family rather than adding independent starting conditions.
This establishes replay, not an eligible missed heal, rescue, new C defect or
population survival benefit. Existing causal investigation34 remains open.

## Failed prototypes and limits

Early preflight hooks rejected ambiguous/mismatched source sites before running
a game. An early header missed ui_event declarations and failed compilation.
Initial visible tests revealed two genuine recording-wrapper problems: buffered
clock input across snapshot forks duplicated auxiliary timestamps, and concurrent
native autosave replacement raced publication. Both failed recordings/logs
remain retained. Unbuffered replay readers plus snapshot-only auxiliary-output
suppression fixed the clock issue; immutable descriptor reads fixed autosave
publication. Subsequent complete visible/headless reruns passed. A GUI harness
also initially selected an old process/waited behind another lane's validation;
that harness was corrected, without killing another lane.

The viewer records logical cells/colors, not font antialiasing/pixel video.
Tick observations can precede remaining processing at that engine tick; command
and input phases are explicitly distinguished. Diagnostic unknown/unseen data
is never fed into Borg inputs. Full Borg memory is reconstructed by re-executing
its recorded start; it is not loaded from a mid-run save.

Exact original binaries require their Linux ABI/runtime. Later unsupported
behavior, non-recorded external interventions or nondeterminism may diverge;
verification must report it rather than force a matching state. Legacy runs
without the recording format are not relabeled as verified movies. Future
pipelines can consume exit codes and JSON but are not installed here.

Persistent archive (primary checkout):
`/home/diego/projects/angband/better-borg-c/artifacts/recording-replay-validation/20261107T142051Z/evidence.tar.gz`

- 257,651,207 bytes; 2085 file members.
- SHA256 `ffcf4bfc60439b69ad8c7fefabe0395ec16eca1875b41f91108d1acd99a12b03`.
- Every member was read back and matched to adjacent manifest.json.
- Complete standalone original/replay bundles for D0004/D0005 are also retained
  extracted under `artifacts/recording-replay-validation/deaths/` in the primary
  checkout; dossier paths resolve there, independent of a disposable worktree.
- Canonical dossier comparison: five dossiers, TWO qualified encounter families,
  thirteen registered death process attempts (including verified repeats).

Local tooling:54 tests passed, including recording integrity, failed/legacy
bundles, native save protection, delta/diagnostic reconstruction, wrong engine,
state/action divergence, original-window export and immutable build policy.
The loaded headless +200 continuation actually ended after208 engine turns
(safe-boundary overshoot); its rerun verified and its exact parent save hash
linked to the prior recording. A final short bundle test also verified the
frozen instrumentation source overlays and all native save anchors.

Hosted checks and final commit/certificate receipts are on consumer134 and its PR; full raw runs/builds remain ignored
under the primary checkout's artifacts/recording-replay-validation/. Source
exports, original engine bytes, original/replay inputs and all rejected outcomes
are retained for recovery. Curated dossier windows/logs remain versioned.


## Recovery

Verify archive SHA256 and each member against manifest.json before use. Restore
complete canonical recording bundles as directories, then use replay-borg.py on
that restored directory; original engine/data/config/input files are retained.
Dossier resolution intentionally checks the manifest hash and reports missing
raw bundles rather than substituting today's engine. If restoring to another
location, pass the bundle directory directly. The recorded base source commit
and instrumented source overlays explain the original engine; Linux ABI/runtime
compatibility is still required. Retain original binaries rather than refreshing
recording caches in place. Rebuilding is a new engine variant until separately
qualified, never a silent historical replacement.

## Player-readable inventory

In the replay, `i` shows the pack and `e` shows equipment/quiver, using normal
slot letters, quantities, Angband item descriptions, weights, fuel, charges and
inscriptions. Unknown objects retain the character's unidentified appearances;
the old diagnostic true-kind list is available separately under `d`. Inventory
panels pause autoplay. Escape returns to the original screen; q exits.

New recording exports use native `object_desc(ODESC_PREFIX | ODESC_FULL)` with
player knowledge, never ODESC_SPOIL, and the actual pack/equipment/quiver order.
The observer restores the two everseen flags that object_desc normally sets;
it does not call interactive inventory commands, learn items, spend energy or
change Borg decisions. Delta frames retain the last native inventory snapshot.

Older immutable recordings lack those descriptions and slot/knowledge details.
A normal interactive replay can prepare a separate observation-enriched rebuild
of the ACTUAL historical source plus its FROZEN recording overlay. Only the
inventory observation is added. Qualification requires all original external
inputs/actions/clock/files, trace, frame fields including RNG/native world hashes,
and native save bytes to match. Only the newly added inventory JSON field is
excluded from that comparison; original inventory fields, if present, remain
strict. Failure retains evidence and stops without a claimed native inventory.
The original recording/engine/death identity is never overwritten. The first
preparation compiles locally and reruns the original life; later opens reuse a
hashed qualified cache under primary artifacts/death-workflow/inventory.

`--view-only` never builds or executes an engine. It can use an existing qualified
inventory cache; otherwise an older movie explicitly says inventory was not
captured and asks for a normal replay. It never guesses native names or reveals
raw diagnostic identities as the character's inventory. `--verify-only` and
`--dump-turn` retain the existing strict original-engine verification semantics.
