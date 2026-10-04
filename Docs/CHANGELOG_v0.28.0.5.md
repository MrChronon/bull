# Changelog v0.28.0.5

## Benchmark flow and telemetry

- Fixed comma-separated model selection with optional whitespace.
- Separated the sampling-source page from the preset page to prevent stale menu
  text from remaining on screen.
- Added aggregate CPU and RAM telemetry to live benchmark progress where the
  active host provides it; GPU and VRAM remain separate measurements.
- Added one concise checkpoint line after every persisted run.

## Validation

- Extended regression coverage for selection normalization, clean navigation,
  system telemetry and run checkpoints.
- Release validation covers compilation, regression, cp1251, public-data audit,
  manifest verification, staged payload and ZIP integrity.
