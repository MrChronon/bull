# BULL v0.29.0.1 — Pack Library

Test packs now live independently of the benchmark engine. Choose the tasks
that fit your work instead of accepting one mandatory built-in suite.

Stable edition: **11 October 2026**, including the 10 October follow-up;
older release notes describe historical builds, not the current acceptance state.

Documentation synchronized 11 October 2026: current author-library paths and
exact-version commands, portable AGENTS.md, citation and issue forms. No prompt,
scorer or runtime change in this synchronization. Stable promotion changes only
metadata/current documentation; published ZIP/checksum and tag are preserved.
[Release readiness](../RELEASE_READINESS.md) retains open manual acceptance and
explains the historical pre-release wording inside the unchanged archive.

The full repository kit now includes paired community policies, installation and
public roadmap/releasing guides, bilingual Issue/PR forms, dependency notices
and [ready-to-use GitHub Release text](../../GITHUB_RELEASE_v0.29.0.1.md).
See [repository handoff](../GITHUB_REPOSITORY.md). Publication remains owner-controlled.

## Highlights

### v0.29.0.1 fixes

Direct Home access to Test settings; batch base-ZIP installation with `all`;
return navigation from the test list; Windows CPU/RAM without WMI;
recoverable checkpoint writes; restored red startup artwork and 18 essential
boot checks. Full details: [Pack Library fixes](../RELEASE_NOTES_0.29.0.1.md).

Home shows integrity and connection once at the top. Pack readiness belongs to
Model testing and Test settings, including a read-only pack → tasks browser. The terminal
bull uses font-independent coloured cells, with ASCII fallback without colours.
Only **BULL Red** and **BULL Matrix** remain. Legacy Matrix aliases select the
green theme; saved contrast settings migrate to red. Language changes retain the theme.
Console UTF-8 and colour mode are refreshed after boot checks and on theme selection.
BULL Matrix also selects a green analogue of the approved startup artwork,
with a matching frame and progress bar on the next launch. BULL Red restores
the red variant; semantic status colours do not change.
Right-edge digital rain animates only in Matrix's startup artwork. The bull,
graphs and check panel remain readable; the animation does not advance progress.

- Optional base ZIPs, your own local ZIP/explicit HTTPS archive link, or skip in Setup.
- Persistent Windows library at `%LOCALAPPDATA%\BULL\BenchmarkPacks`.
- One exact pack version per comparison; all tasks or an explicit subset.
- Before inference: identity, coverage, skills, languages, scoring and settings.
- Author Workshop: editable UTF-8 YAML/TXT, deterministic criteria, positive and
  negative answer fixtures, reproducible ZIP building and explicit version updates.
- Complete private task snapshots for resume after pack removal or update.
- Terminal/HTML coverage labels and manifest/compiled hashes; allowlisted
  version/hash/coverage provenance in share-safe evidence.
- Updated English/Russian guides and instructions for cloud LLM pack authors.
- Red or green startup artwork and theme-matched owned shortcut icons.
- `Setup.exe` with a distinct install-arrow icon: language → theme before all other steps.
- One `BULL.exe` entrypoint for setup launch and shortcuts; same Terminal profile,
  per-window Consolas fallback, sharper 48×24 terminal logo. No global settings edits.
- Root `BULL.exe` is absent before Setup; a verified payload is materialized
  only after full regression and connection setup/skip. The logo flushes 24 rows
  before the wordmark; live terminal visual acceptance remains open.
- Diagnostics: basic or Setup's full suite. Empty status does not invent a chat;
  unsupported THINK falls back to FAST in chat with the documented retry limits.
- Owned sampler/SSH children are reaped at exit; external servers are not stopped.
  Real folder-deletion acceptance remains open. GPU Lab is removed, ordinary GPU telemetry stays.
- GPU/VRAM/CPU/RAM each report a value or `N/A` reason; paths with spaces work with
  pinned SSH without weakening host-key verification.
- Language pack 1.0.1/scorer v2 penalizes foreign-script prose; separate RU/EN
  reports show language checks, native timings, seed ranges and exact pairs, not a merged winner.

Full follow-up scope and limits: [corrections](../FOLLOWUP_2026_10_10.md),
[RU/EN interpretation](RESULTS.md), [roadmap](../BULL_TRANSITION_ROADMAP.md).

## First comparison

1. Extract into a new directory and run `Setup.exe`.
2. Choose language, BULL Red / BULL Matrix, and a base/user pack or skip.
3. Open **Model testing → Compare a test pack**.
4. Choose the exact version and all or specific tasks, then models and settings.
5. Review the plan; after the run open the recommended offline HTML report.

Four separate base ZIPs are included: CHAT Core (12 cases), Extended Core
(4 cases), RU Dialogue candidate (10 cases), Language Comparison (6 cases).
None is automatically installed or required for chat and saved reports.

Do not copy an old configured bundle over the release. The shared pack library
is reused automatically; connection selection remains explicit.

## Integrity and limits

Both setup and shortcuts now launch the same executable and Terminal profile;
native console font settings are normalized per window. Real clean-install
first-menu visual acceptance remains open: automated tests do not prove that
the user's terminal displays identically. The portable launchers are unsigned.

The offline suite contains **668 checks**. UTF-8 and forced-cp1251 runs passed
668/668; startup passed 18/18. The release gate verifies UTF-8,
forced cp1251 startup, PowerShell syntax, source/staged privacy, the exact
manifest set and every archive entry hash. Verify the separate SHA-256 file.

Existing base prompts and references are unchanged. Language scorer v2 is a
separate versioned correction; historical v1 and old results are preserved.
Chat/runtime fixes and report-only changes were made independently, not as one
prompt/scorer/runtime rewrite. New compatible packs need no engine edits. TXT tasks have human
review, not automatic quality scores; deterministic checks do not certify
reasoning or domain correctness.

Packs contain data, not author executable code. Existing engine-owned code
checks still require explicit consent and are not an OS sandbox. Use a
disposable VM for untrusted code. ZIP limits and source formats are documented;
checksums do not authenticate an author.

Private checkpoints/evidence and authored ZIPs contain task content and must
not be treated as share-safe reports. Review pack/case IDs and model labels
before sharing metrics. No telemetry service, online catalog or LLM judge is
added. Linux is the next planned stage, not supported by this release.
No live model inference was performed in the follow-up. A finite read-only
resource probe confirmed all four counters on one selected pinned host; it does
not replace live chat/benchmark/resume acceptance. General per-pack report
profiles and richer language tasks remain roadmap work.

[User guide](USER_GUIDE.md) · [Pack library](PACK_LIBRARY_GUIDE.md) ·
[Author Workshop](AUTHOR_WORKSHOP.md) · [Security](SECURITY.md)

Client setup: language → theme → optional ZIP packs (file/HTTPS) → full internal
regression → existing connection or skip → launch/exit.
Five Home sections separate testing, chat and three settings areas.
Section 6, Additional, provides session status, diagnostics, help and
experimental tools without an extra submenu.
Every launch checks integrity, connection and packs; green signals readiness,
warnings identify missing setup.
