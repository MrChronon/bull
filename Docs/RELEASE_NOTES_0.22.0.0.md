# BULL v0.22.0.0 — BULL Bridge

This is the first branded BULL release and the second stage of the approved
transition plan. It keeps the proven pre-BULL v0.21 behavior while establishing
the product identity and compatibility boundary needed for later architecture work.

## For users

Run `Install-BULL-v0.22.0.0.cmd`, then use `BULL-v0.22.0.0.cmd` or the dedicated
Lab launchers. Existing historical automation can use the included aliases
temporarily. No model, private connection or benchmark result is included.

The new bull-head mark combines neural-network nodes and benchmark bars. Bright
teal/cyan accents remain compatible with the current terminal interface, while
light and monochrome variants support documentation and future UI surfaces.

## For integrations

New code may import schema, profile, telemetry and backend contracts through
`Shared.bull_llm`. The historical compatibility facade remains supported.
Existing artifact schema IDs are deliberately not renamed. A read-only compatibility
reader recognizes the versions in `BULL_COMPATIBILITY_MATRIX.md` without modifying
the source or implicitly enabling checkpoint resume.

## Measurement integrity

This release does not change benchmark prompts, scorers, ordering, generation,
recovery or runtime options. Comparisons with v0.21 therefore remain meaningful
subject to the same hardware/runtime controls documented in the user guide.

## Security

Public defaults remain local-only. Release gates exclude runtime data and scan for
personal topology, credentials and private keys. Generated CODE is still not an OS
sandbox; use a disposable VM for untrusted output.

Known limitation: BULL is used with the qualifier “BULL Benchmark Lab” because
the unqualified name is already used by unrelated software and research projects.
