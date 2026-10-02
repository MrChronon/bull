# Changelog v0.26.0.0

## Added

- Public candidate pack `bull_ru_dialogue@1.0.0` with 10 parameterized cases.
- Six RU Dialogue families covering state, evidence, causality, instruction
  retention, business language and embedded-instruction resistance.
- Engine-owned allowlisted scorer `ru_dialogue_contract_v1`.
- Separate `semantic_score` and `structural_score` fields.
- Public development set, deterministic pack builder, gold fixtures and
  synthetic manual-audit fixtures.
- Five RU Dialogue regression contracts; total offline suite is 363/363.

## Changed

- `ru_language_stress_v3` and `groundedness_adversarial_v1` now expose semantic
  and structural aliases for their existing content/format subscores. Their
  calculated `value` is unchanged.
- Current documentation and release identities moved to v0.26.0.0.

## Unchanged

- Frozen CHAT Core prompts, result instructions and score values.
- Recovery, checkpoint/resume and inference runtime behavior.
- Evidence schemas and legacy-artifact compatibility.

## Security and privacy

- Benchmark packs remain data-only and resolve scorers through an engine-owned
  allowlist.
- New fixtures are synthetic and contain no local connection or personal data.
- Critical scorer events carry evidence/reason and require manual review.
