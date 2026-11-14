# Recorder extraction, 2026-11-14

Owner task #522 removes the recording producer from this C-only consumer.
The native recorder is now the Rust crate in diegoami/angband-recorder,
pinned by borg-rs and borg-reborn-rs. No C-only recorder build remains.
`measure-native.py prepare --observe` still provides measurement and forked
checkpoint saves; `--recording` is no longer an option. Existing immutable
recordings retain their frozen executables, read-only viewers and provenance.
Their directories are not rewritten or deleted. New recorded play belongs
to the Rust consumers; curated runs belong to diegoami/borg-cemetery.

This removes tools/native-replay.c and .h, disposable recording instrumentation
and observer recording calls. It changes no engine/Borg policy, milestone tag,
canonical carry or historical evidence. The standalone project retains the
original better-borg-c adaptation credits.
