# BULL roadmap

[Русский](../ru/ROADMAP.md) · [Engineering plan 1.10](../BULL_TRANSITION_ROADMAP.md)

This public summary reflects the approved plan, not new deadlines or a promise
that planned features are already shipped. Current edition: v0.29.0.1 stable,
11 October 2026; owner-designated stable status does not close manual acceptance.

## Implemented

Pack Library separates optional versioned ZIP content from the engine. Shared
storage, exact-version/subset selection, Author Workshop, complete private run
snapshots, resume and paired documentation are implemented. The follow-up adds
Setup-only distribution, flat navigation, two themes, diagnostics, lifecycle and
telemetry corrections, language scorer v2 and dedicated RU/EN reports.

Automated checks do not close [manual acceptance](../RELEASE_READINESS.md):
clean/repeated terminal rendering, immediate themes, folder release after exit,
live chat/benchmark/resume and clean-machine dependency setup remain open.

## Next sequence

1. **PK1 acceptance:** finish the user checks before another architecture stage.
2. **P1 — Linux:** planned terminal client on the existing contracts; no Linux/macOS
   support claim in this Windows release.
3. **U2 — Quick Compare:** a small candidate pack plus a confirmatory run;
   its time budget is a target on declared hardware, not a universal guarantee.
4. **Reliable Runs:** separate transport fault-injection and hardware-comparability work.

**RPT1** plans safe engine-owned/declarative report profiles for other domains;
the specific RU/EN view already exists. **LANG1** plans more discriminative paired
language content and independent human validation. Their scheduling relative to
P1/U2 needs an owner decision; no date/version is committed.

## Later / deferred

Isolated execution precedes executable author extensions and more extensive
Agent/long-context/security work. External adapters/SDK and stable v1.0 formats
come later. GUI, hosted leaderboard, marketplace, branding redesign and automatic
model downloads are not in the current delivery scope. Red/green hybrid design
remains a separate visual study, not a third application theme.

All stages preserve historical artifacts, version prompt/scorer corrections
separately, keep native/recovery metrics distinct and retain offline/privacy gates.
