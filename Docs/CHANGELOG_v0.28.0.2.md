# Changelog v0.28.0.2

## Startup status and default appearance

- The desktop startup window now separates the verification stage from its
  detail and identifies the active offline regression suite:
  `Tests/benchmark_regression.py`.
- The default BULL terminal presentation is now BULL Red.
- The retained green alternative is named **Matrix BULL**.
- Existing saved `bull_brand` preferences are safely migrated to BULL Red;
  no backend, connection, benchmark, or model setting is changed.

## Validation

- Added regression coverage for the splash detail line and red-theme migration.
- Release validation continues to cover compilation, regression, cp1251,
  public-data audit, manifest verification, staged payload, and ZIP integrity.
