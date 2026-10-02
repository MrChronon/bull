# BULL v0.26.0.0 — RU Dialogue

2 October 2026

This is the first BULL Flagships release. It introduces a public candidate
benchmark for Russian multi-turn dialogue correctness without changing the
stable CHAT Core or the inference/recovery path.

## What is new

- `bull_ru_dialogue@1.0.0`: 10 parameterized cases in six families:
  confirmed state, evidence limits, causal caution, instruction retention,
  business Russian and embedded-instruction resistance.
- A public `development_set.json` plus deterministic builder. The generated pack
  remains data-only and cannot execute code.
- Engine-owned `ru_dialogue_contract_v1`, which reports `semantic_score` and
  `structural_score` independently.
- Critical failures include the failed check, observed evidence and reason; they
  always set `manual_review_required=true` and apply a documented cap.
- Positive scorer gold fixtures and six synthetic adversarial cases audited
  against the declared contract.
- 363/363 offline regressions, including registry, scorer, cp1251, startup,
  security, manifest and ZIP checks.

## What did not change

This release does not change benchmark prompts in `bull_chat_core`, existing
scorers, recovery behavior or the runtime inference pipeline. It adds a new pack
and a scorer used only by that pack. Native model quality and client-assisted
quality remain separate evidence dimensions.

## Maturity and interpretation

The RU Dialogue pack is `candidate`, not `stable`. Its automatic scores are
diagnostic evidence, not a universal model ranking. Promotion requires an
independent cross-model run and a second human review of scorer false positives,
false negatives and every critical failure category.

The manual audit file covers synthetic scorer fixtures. It does not claim that
any model was manually evaluated.

## Try it

1. Install with `Install-BULL-v0.26.0.0.cmd`.
2. Open `BULL-Benchmark-Lab-v0.26.0.0.cmd`.
3. Choose Advanced tests, then list cases or run one of the `ru_dialogue_*`
   cases/categories.
4. Inspect metadata with `/bench pack inspect bull_ru_dialogue`.
5. Review native answers for every critical failure before drawing conclusions.

## Public files

- `BenchmarkPacks/bull_ru_dialogue/development_set.json`
- `BenchmarkPacks/bull_ru_dialogue/scorer_gold.json`
- `BenchmarkPacks/bull_ru_dialogue/manual_audit.json`
- `Tools/build_ru_dialogue_pack.py`
- `Tests/ru_dialogue_regression.py`

## Privacy

All new prompts and fixtures are synthetic. The release archive excludes local
Chats, Runtime, Benchmarks, Exports, Workspace, keys, endpoints and debug logs.
Raw benchmark results can still contain model answers and must be reviewed before
sharing.
