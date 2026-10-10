# PK1.2 — Engine Boundary

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| Engine catalog | Static runner/scorer/verifier allowlists, validated definitions and exact pack provenance |
| Pack data | Prompts, references, constraints, output instructions, scorer configuration and generation budgets |
| Diagnostic fixtures | Frozen regression and historical-audit contracts; never runnable catalog fallback |
| Client adapter | One explicitly selected installed version; legacy loose tasks are a separate workflow |

`Shared/bull_llm/evaluation/catalog.py` imports no client, transport or test
content. Its policy cannot be extended by a pack declaration. An empty registry
is valid. Duplicate case IDs are rejected, including collisions between versions;
the client cannot silently choose or overwrite one. Preview definitions are deep
copies, not mutable shared pack objects.

## Preserved contracts

The 12 CHAT Core definitions and all existing pack files/hashes are unchanged.
Four other existing tasks are in `bull_extended_core@1.0.0`. For all 16 tasks,
regression compares definition, effective prompt, reference and execution hashes.
It also checks 15 complete scorer-result hashes against the existing gold answers.
No prompt, reference, scorer algorithm or generation budget is revised here.

The `builtin_benchmarks()` compatibility facade reads a diagnostic fixture only
for regression and historical audit. `load_benchmarks()` does not call it and
never uses it to fill an empty library. Selecting an unavailable test produces
`BENCHMARK_CASE_NOT_AVAILABLE` before the model API is contacted.

Pack files are data-only; this does not sandbox the engine's existing code tests.
Retention/Python checks still require code-execution permission and a disposable
VM for untrusted output. Installing a pack cannot enable that permission.

## Verification and remaining work

PK1.2 gate: 439/439; PK1.3 gate: 465/465. Engine-boundary tests cover empty and independent
catalogs, fixed capabilities, diagnostic independence, saved summaries, historical
audits, duplicate rejection and mutable-preview isolation. The CHAT pack builder
reads frozen data, not an imported client module.

PK1.3 connects `%LOCALAPPDATA%/BULL/BenchmarkPacks`, optional base/user ZIP
installation, explicit version selection and a whole-pack/subset preview.
Published source directories and diagnostic fixtures do not populate the runtime
library. Legacy regression tests receive an explicit reference catalog instead.
See the [library guide](PACK_LIBRARY_GUIDE.md).
Historical named-suite weights remain compatibility policy. v0.29.0.1 uses
single-pack comparisons and complete hash-checked private snapshots in checkpoints
and evidence. Resume needs no installed copy for new snapshots and cannot silently
substitute content. Share-safe summaries retain only allowlisted hashes and coverage.
PK1.5 originally passed 518 checks. The local follow-up of 10 October passes
668/668; the extraction gold remains unchanged. See the current
[development guide](DEVELOPMENT.md) for release gates and open live acceptance.
