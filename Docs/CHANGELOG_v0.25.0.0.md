# Changelog — BULL v0.25.0.0

## Added

- `Shared/bull_llm/evidence.py` with record, summary, provenance, privacy-audit
  and copy-only migration contracts.
- JSON schemas for `bull-benchmark-record@1` and
  `bull-benchmark-summary@1`.
- Private and share-safe evidence artifacts for completed benchmark suites.
- Prompt/pack/scorer/verifier hashes and separated runtime fingerprints.
- Confidence-interval, latency-distribution and context-curve sections in the
  autonomous HTML report; category heatmaps remain available.
- Nine focused evidence regression tests.

## Changed

- Terminal and HTML reports consume the same normalized summary metrics.
- Checkpoint finalization verifies the two new evidence outputs.
- Client source hashing is cached during a process to avoid repeated reads for
  every benchmark record.
- Agent streaming now classifies a response closed by its own deadline timer as
  a timeout instead of a connection reset, removing a scheduler-dependent race.
- Active launchers, installers and app entrypoints use v0.25.0.0 names.

## Compatibility

- Legacy artifacts remain readable.
- Existing raw JSON/CSV, summary JSON/CSV, checkpoint and tested profiles are
  still emitted.
- CHAT prompts, scorers, recovery behavior and inference options are unchanged.

## Verification

- `Run-Tests.ps1`: 358/358.
- Public release audit, cp1251 startup, manifest and ZIP verification are release
  gates.
