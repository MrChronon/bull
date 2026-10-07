# BULL v0.22.0.0 — переходный аудит

## Scope

T1 changes branding, public entry points, documentation and compatibility APIs.
Benchmark prompts, scorers and runtime pipeline are out of scope and unchanged.
The full v0.21 performance/security audit remains in `AUDIT_v0.21.0.0.md`.

## Findings closed in T1

- new and legacy product names have explicit one-way launcher mappings;
- compatibility aliases visibly warn before delegation;
- `bull_llm` reuses, rather than forks, proven shared implementations;
- legacy JSON readers are size-limited, UTF-8, finite-number checked and read-only;
- unknown schema/version pairs fail closed;
- current SVG assets have no script, external URL or embedded personal metadata;
- release filenames, docs, manifest and ZIP root use one v0.22 identity;
- factory network settings remain local and contain no selected remote connection.

## Residual risks

- historical schema IDs were scheduled for a BULL namespace migration;
  versioned migration and is intentionally avoided here;
- legacy CODE execution remains outside an OS sandbox;
- visual trademark/legal clearance is not provided by a technical audit;
- old-name aliases are transitional and should be removed only after v1 policy review.

## Exit criteria

T1 is complete when compile, all offline regressions, forced cp1251, public privacy
audit, brand-asset checks, manifest verification and ZIP integrity all pass, and a
fresh extracted bundle starts through both BULL and compatibility launchers.
