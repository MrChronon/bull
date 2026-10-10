# BULL v0.23.0.0 — changelog

## Added

- `bull_llm.core` typed request, response, event and result contracts;
- public `BackendAdapter`, `BenchmarkPack`, `Runner`, `Scorer`, `Verifier`,
  `TelemetryProvider`, `ArtifactStore`, `ReportRenderer` and `SchemaMigration` protocols;
- shared Ollama/llama.cpp function-port adapters and UI-free model discovery;
- transport-free native evaluation and non-rescoring JSON report renderer;
- rooted, bounded and atomic JSON artifact store;
- BULL Core offline contract/dependency tests;
- approved canonical logo lock with SHA-256 and deterministic crop/resize derivation.

## Changed

- release identity and filenames advance to v0.23.0.0;
- the approved detailed bull mark replaces the provisional geometric mark;
- public documentation describes T2 module boundaries and migration status;
- release gates require BULL Core modules, tests and canonical brand assets.

## Intentionally unchanged

- benchmark prompts and expected results;
- scorer implementations and score semantics;
- runtime ordering, generation, recovery and resume behavior;
- legacy schema IDs/versions and v0.22 artifact compatibility;
- public local-only connection defaults.
