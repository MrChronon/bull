# BULL v0.23.0.0 — BULL Core

This is transition stage T2: a typed, testable core is introduced around the
proven application without a big-bang runtime rewrite.

## What users get

- the approved bull/neural-network/benchmark logo is now the canonical brand
  master and all release icons are derived from it;
- the familiar Client, Benchmark Lab, Agent Lab and GPU Lab keep their existing
  entry points and behavior;
- existing Local LLM artifacts and temporary compatibility launchers remain
  readable as documented.

Run `Install-BULL-v0.23.0.0.cmd`, then use `BULL-v0.23.0.0.cmd` or a dedicated
Lab launcher. Models, private connections and benchmark results are not bundled.

## New integration surface

`Shared.bull_llm.core` defines typed requests, responses, inference events and
public protocols for backends, benchmark packs, runners, scorers, verifiers,
telemetry, artifact storage, report rendering and schema migrations.
`Shared.bull_llm.runtime` supplies one contract for Ollama and llama.cpp adapters
and keeps model discovery independent of the UI. Evaluation consumes native
responses without importing transport; reports consume precomputed summaries
without recalculating scores.

The new adapters currently wrap injected functions. The production client still
uses the established v0.22 execution path; later stages can move one responsibility
at a time behind the tested contracts.

## Measurement integrity

This release does not change benchmark prompts, scorers, ordering, generation,
recovery or effective runtime options. Model-native output remains distinct from
client-assisted recovery output. Existing runtime fingerprint behavior is retained;
the new canonical fingerprint helper is parity-tested against the legacy helper.

## Security and privacy

Artifact storage is rooted, size-limited, strict about non-finite JSON and uses
atomic replacement. Public defaults remain local-only. Release gates reject keys,
private connections, local runtime data and personal paths. Generated CODE is not
an OS sandbox; use a disposable VM for untrusted output.
