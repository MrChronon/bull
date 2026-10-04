# Changelog v0.28.0.3

## Exact startup verification status

- The startup window now displays the exact active primary check, emitted by
  the regression harness immediately before it starts.
- Imported contract suites also identify themselves before execution, so the
  displayed name never remains stale while a secondary suite is running.
- Startup output is read incrementally with a bounded timeout; the gate remains
  fail-closed on a timeout or a failing check.

## Validation

- Added regression coverage for explicit check markers, stream delivery,
  localization of the status label, and bounded marker handling.
- Release validation continues to cover compilation, regression, cp1251,
  public-data audit, manifest verification, staged payload, and ZIP integrity.
