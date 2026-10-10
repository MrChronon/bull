# BULL v0.29.0.1 verification scope

## Current scope pointer · 11 October 2026

This file retains the **earlier 644-check patch snapshot** below. Current local
follow-up verification uses **668 offline checks**, the same **668 under forced
cp1251**, and **18 essential startup checks**. See
[follow-up evidence and limits](FOLLOWUP_2026_10_10.md),
[current release notes](en/RELEASE_NOTES.md) / [русское описание](ru/RELEASE_NOTES.md),
and [release readiness](RELEASE_READINESS.md).

The later language pack 1.0.1/scorer v2, chat fallback, shutdown, telemetry,
selected-track and report changes are separate verified corrections; the earlier
preservation statements below apply only to that earlier patch. Prompts and
historical scorer versions were not silently replaced. Manual terminal,
folder-deletion and live inference acceptance are still open. Publication is separate.

## Earlier patch snapshot — historical record

## Runtime and preservation

The patch retains benchmark prompts, scorer contracts and inference settings.
Persistence retries happen outside model generation. A failed checkpoint
replacement does not overwrite the preceding file or count a persistence
failure as a model-quality defect. A complete temporary payload is retained;
recovery requires confirmation and produces a different checkpoint path.

CPU/RAM are aggregate inference-host measurements. The fixed engine-owned
Windows sampler uses GetSystemTimes and GlobalMemoryStatusEx, emitting JSON
without machine identity or process names. Unknown host placement never
substitutes local-client measurements for the server.

Batch installation retains preview approval and digest checks, installs packs
individually, and never enables multiple packs in one benchmark run. Identical
versions are retained; different content under an installed version is refused.

## Required verification

- `Run-Tests.ps1`: complete 644-check offline regression, including the patch
  reproductions, real native Windows counters and unchanged scorer fixtures.
- The same complete suite under forced cp1251.
- Essential startup gate: 18 checks against the finalized release manifest.
- Public privacy audit, PowerShell 5.1 encoding/parse, exact source/staging/ZIP
  hashes, and archive SHA-256.
- Fresh-extraction startup and offline navigation; every launch forces the
  18 essential checks rather than accepting a cached pass.

The 518 pre-patch compatibility regressions remain in the full suite.
They are not all necessary at application startup: release fixtures, synthetic
transports, historical score cases and report checks belong in the release
gate, not every cold boot. Benchmark measurement contracts remain unchanged.
Server and all-in-one installer roles were intentionally retired.

## Client installation and navigation

The client installer selects English/Russian and BULL Red / BULL Matrix before dependency checks, then
offers optional standard or user packs, full internal regression, an existing
connection or skip, and launch/exit. Only a passed full regression permits the
completion state. Connection or pack absence is valid unconfigured state.

The main menu isolates model testing, chat, test settings, connection settings
and program settings. Pack selection for a run bypasses library management.
Green readiness and yellow missing-setup labels use semantic colors independent
of the selected theme and appear once in the Home header, not beneath its items.
Reports remain available without an LLM connection. The terminal bull uses only
RGB background cells and ASCII spaces, with an ASCII fallback without colours;
tests reject unsupported glyphs, control injection and missing row resets.
Theme contracts cover red-to-Matrix Home redraw, a newly loaded application
instance, display-name/environment aliases, and retention when changing language.
Windows console contracts simulate a VT-mode reset during first-launch checks
and theme selection. Failed/non-terminal handles cannot retain a stale enabled flag.
This is a simulated console-host test, not a capture of the user's terminal.
Startup-theme contracts cover saved preferences and environment overrides,
switching back to red, all Matrix variants, theme-bound native-widget palettes,
real completed-check progress and optional GUI failure. The green hero retains
the red composition and square dimensions; both versioned PNGs are required
and hashed by the startup gate. The locked canonical logo remains unchanged.

HTTPS pack imports retain the existing ZIP validation and approval gate.
Tests cover unsafe URLs, redirects, credentials, size limits, deadlines,
truncation, cleanup and non-overwrite behavior with fake responses, not a live
remote service. Shortcut integration uses isolated target directories. Python
installation through winget still needs clean-machine manual acceptance.

Presentation contracts cover two selectable themes, retired contrast migration,
theme-before-packs ordering, one native entrypoint and fixed launch commands.
Real Windows shell-link integration changes both colours in isolated directories
and preserves foreign links. The terminal logo is 48×24 cells, directly sampled
from the locked canonical crop. Approved startup artwork is unchanged.
An isolated hidden native-console probe sets and reads back Consolas at 10×20;
portable companion checks pass from a path with spaces, Cyrillic and a semicolon.
These are API/entrypoint checks, not captures of a visible user Terminal session.
Release construction recompiles the two unsigned native launchers from shipped
C# source before the binary allowlist and manifest gates.

## Limits

Setup launch and shortcuts now use the same BULL.exe and default Terminal profile;
native consoles use per-window Consolas. This avoids the differing launch-host
configuration but does not establish the exact cause of the earlier screenshots.
Automated console-mode tests do not close visual acceptance: clean installation
followed by direct installer launch still needs comparison in the user's terminal.

Windows file-lock reasons cannot be inferred reliably from WinError 5 alone.
Retries are bounded and cannot repair permanent ACL restrictions. Optional
telemetry can remain unavailable on unsupported or restricted servers and
shows N/A. Previous reports lacking CPU/RAM are not retroactively populated.
Red/green visual concepts remain outside the application.
