# Changelog v0.28.0.7 — Clean Release

## Benchmark results and language tracks

- Added separate Russian, English, and bilingual comparison tracks.
- Expanded terminal and offline HTML analytics with top-3 rankings,
  quality/speed maps, test heatmaps, stability ranges, and resource views.
- Added post-test checkpoints with score, speed, and available CPU, RAM, GPU,
  and VRAM telemetry.
- Made the HTML report the recommended post-run view while retaining JSON and
  CSV artifacts for analysis.

## Ollama profile comparisons

- Fixed `strict_fair_compare` rejecting sampling differences inherited from
  Ollama Modelfiles, including an absent `repeat_penalty` value.
- Added explicit `profile-owned differences` to the fairness evidence instead
  of treating them as unapproved runtime differences.
- Resolved `/api/show` profile data before rendering the confirmation plan.
- Declared all sampler fields editable by the per-model wizard as intentional
  experimental parameters.

## Documentation and validation

- Updated the English and Russian documentation for the complete v0.28.0.7
  workflow and report surfaces.
- Removed obsolete public product identifiers and stale release-only assets.
- Rebuilt the manifest-controlled public archive with 256 files.
- Expanded coverage to 401 offline regression checks.
