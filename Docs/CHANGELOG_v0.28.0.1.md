# Changelog v0.28.0.1

## Startup presentation hotfix

- Replaced the terminal-rendered verification artwork with a separate native
  desktop splash window.
- The splash uses the exact versioned PNG, shows only the three observed
  verification stages, and closes before connection handling and the menu.
- Reset terminal foreground and background before every screen clear so a
  previous ANSI renderer cannot affect the BULL interface.
- Removed the obsolete terminal splash renderer and its generated ANSI asset.

## Validation

- Added regression coverage for the versioned image, truthful progress bounds,
  splash lifecycle boundary, and terminal background reset.
- The release process continues to run compile, offline regression,
  forced-cp1251, privacy, manifest, staged-payload, and ZIP-integrity gates.
