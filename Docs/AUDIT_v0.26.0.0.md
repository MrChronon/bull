# Public release audit — BULL v0.26.0.0

**Scope:** T5.1 BULL RU Dialogue, release boundary, scorer correctness and
compatibility with v0.25.0.0.

**Date:** 2 October 2026

## Result

Release candidate approved for packaging after all mandatory gates pass. The
new pack is intentionally marked `candidate`; this audit does not promote its
methodology to `stable` and does not evaluate model quality.

## Reviewed changes

- 10 generated cases match the public parameterized development set.
- Pack manifest, cases, gold and lock validate through BULL Registry.
- The scorer is engine-owned; no executable file exists inside the pack.
- Semantic and structural scores are calculated independently.
- Invalid terminal JSON, schema mismatch and critical semantic contradictions
  have explicit caps.
- Every critical event contains a check name, evidence and reason and sets
  `manual_review_required=true`.
- Positive gold fixtures score exactly 1.0/1.0 by dimension.
- Six adversarial fixtures trigger their reviewed critical checks.
- Existing CHAT Core definitions still match their canonical hashes.
- Recovery and inference runtime code were not changed in T5.1.

## Privacy review

The new development set and fixtures are synthetic. No host, public IP, user
name, private-key path, API token, chat history, model response, local benchmark
result or home-directory path is intentionally included. Standard release gates
still exclude `Chats`, `Runtime`, `Benchmarks`, `Exports`, `Workspace`, private
keys and logs.

## Verification

- Python compile: pass.
- Offline regression: 363/363 pass.
- Dedicated RU Dialogue contracts: 5/5 pass.
- Clean Python, cp1251, startup, manifest and archive gates: executed by
  `Build-Release.ps1` before release publication.

## Residual risks

1. Literal contract matching cannot understand every valid Russian paraphrase;
   critical failures therefore require human review.
2. Synthetic gold fixtures validate scorer behavior, not ecological validity.
3. The candidate pack has not yet received independent cross-model evidence or
   a second human methodology review.
4. Automatic scores must not be presented as proof of general model superiority.

## Promotion requirements

- Run the pack across materially different models and at least three seeds.
- Audit false positives, false negatives and all critical failures.
- Obtain a second human review of prompts, references and caps.
- Version any content/scorer change; do not silently rewrite 1.0.0 results.
