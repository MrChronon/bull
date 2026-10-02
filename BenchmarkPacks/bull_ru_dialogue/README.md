# BULL RU Dialogue 1.0.0

Candidate public benchmark pack for Russian multi-turn dialogue correctness. It targets confirmed state changes, stale-data replacement, unsupported assistant claims, evidence limits, causal caution, instruction retention, modern business Russian and embedded-instruction resistance.

The pack is data-only. `development_set.json` is the public parameterized source; `cases.json` is its deterministic expansion. `scorer_gold.json` freezes positive scorer examples. `manual_audit.json` contains adversarial critical-failure examples reviewed against the declared contract. These fixtures audit scorer behavior, not model quality.

Scores expose two independent dimensions:

- `semantic_score`: reference values and required/forbidden claims;
- `structural_score`: terminal JSON, exact schema, section and format contracts.

Critical semantic contradictions are capped and always set `manual_review_required=true`. The pack remains `candidate` until it has cross-model evidence and a second independent human review. Benchmark prompts and scorer behavior must not be changed in the same release as recovery/runtime behavior.
