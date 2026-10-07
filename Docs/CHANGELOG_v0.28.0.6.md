# Changelog v0.28.0.6

## Result clarity and reporting

- Added measured top-three places for Native quality, warm speed, VRAM and
  balance; ties remain ties rather than being broken by a model name.
- Separated descriptive ranks from quality-gated profile recommendations.
- Withheld recommendations when tested coverage or effective configuration is
  not comparable, while retaining visible measurements.
- Added a compact current-test provisional roll-up after each persisted run.
- Added aggregate CPU/RAM observations beside GPU/VRAM when sensors expose
  those host-level values.
- Replaced the legacy HTML result page with an offline, JavaScript-free BULL
  report: rankings, charts, resource views, test heatmap, test descriptions,
  configuration provenance and uncertainty context.

## Documentation and validation

- Added dedicated English and Russian results guides.
- Updated the documentation index and benchmark guides.
- Expanded regression coverage for ties, coverage gaps, resource privacy,
  narrow terminals, bilingual reports and provisional output.
- Release validation covers 398 offline checks, compilation, forced cp1251,
  public-data audit, manifest verification and ZIP integrity.
