# Changelog v0.28.0.7

## Ollama profile comparisons

- Fixed `strict_fair_compare` rejecting sampling differences inherited from
  Ollama Modelfiles, including an absent `repeat_penalty` value.
- Added explicit `profile-owned differences` to the fairness evidence instead
  of treating them as unapproved runtime differences.
- Resolved `/api/show` profile data before rendering the confirmation plan.
- Declared all sampler fields editable by the per-model wizard as intentional
  experimental parameters.

## Documentation and validation

- Documented the boundary between profile-owned comparisons and identical
  benchmark sampler settings in English and Russian.
- Expanded coverage to 400 offline regression checks.
