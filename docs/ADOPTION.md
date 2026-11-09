# Adoption scope and status labels

This repository starts from Angband master
`e473720ed88a0f0c7ca66815cef3000eb4a38bc3`, preserving its history, credit,
licence, game and Borg sources. Bootstrap adds no gameplay fix; see
[UPSTREAM.md](../UPSTREAM.md) for the full baseline record.

Source reports, native reproductions and reusable C fix proposals belong to
[neo-angband-tracker](https://github.com/diegoami/neo-angband-tracker/issues).
This repository owns adoption, integration and testing of those fixes in a
playable C derivative. Each adoption has its own issue linked to the source.
It does not replace the source tracker or take over its native-C session.

## Status labels

- **carried**: corrected and verified here, but not yet resolved upstream;
  the adoption issue stays open.
- **fixed**: resolved upstream and incorporated, rebuilt and verified here;
  close the adoption issue.
- **partial** / **not-carried**: name the actual missing work. A patch file or
  proposal alone is not a carry. `patch-active` tracks maintained backports
  separately from issue closure.

## Project boundaries

Faithful TypeScript port repairs stay in neo-angband-borg-mod-tracker. Mandos
independently translates C fixes into TypeScript; borg-rs independently handles
Rust and reports directly to the source board. This product has no Neo engine,
TypeScript, Rust or private lab ownership. Current scope is bugs, not new strategy.

## Project documents

Read [AGENTS.md](../AGENTS.md), [RULES.md](../RULES.md), [PLAN.md](../PLAN.md),
[session.json](../session.json) and the latest comments on
[checkpoint #1](https://github.com/diegoami/better-borg-c/issues/1).
[UPSTREAM.md](../UPSTREAM.md) records the baseline; [patches/README.md](../patches/README.md)
explains the carry ledger. Issues are authoritative for live status.
