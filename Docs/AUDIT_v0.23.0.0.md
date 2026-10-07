# BULL v0.23.0.0 — аудит этапа T2

## Scope

T2 extracts stable public contracts and adapter boundaries around the current
implementation. It does not switch the production runtime and does not change
prompts, scorer logic, recovery or benchmark execution order.

## Closed findings

- runtime requests/responses are represented by immutable typed contracts;
- Ollama and llama.cpp adapters pass one shared offline contract suite;
- model discovery contains no terminal/UI dependency;
- inference progress is expressed as data events, not terminal rendering;
- evaluation contains no backend transport import;
- reports serialize precomputed summaries and cannot invoke a scorer;
- artifact writes are rooted, bounded, finite-JSON checked and atomic;
- public protocol surface is runtime-checkable and centrally exported;
- canonical fingerprints match the legacy algorithm for valid JSON;
- the approved logo master is hash-locked and release variants are derived
  deterministically without redrawing it.

## Residual risks

- the monolithic client remains the active production path; T2 contracts are the
  seam for later incremental extraction, not a completed runtime migration;
- cancellation capability is explicit but the legacy adapters currently report it
  unsupported because the existing stream API has no per-request cancel primitive;
- historical schema IDs require explicit compatibility handling;
- real hardware/WAN validation remains separate from the offline release gate;
- generated CODE execution remains outside an OS sandbox.

## Exit criteria

T2 is complete when compile, normal and forced-cp1251 regressions, BULL Core
contract/dependency tests, brand-lock verification, privacy audit, manifest hashes
and ZIP integrity pass. The established Client/Benchmark execution path must retain
its regression parity.
