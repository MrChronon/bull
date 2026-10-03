# Development and release process

## Architecture

BULL keeps three product boundaries:

- Client: chat, session lifecycle, and explicit tested-profile import;
- Benchmark Lab: catalog, execution plan, scoring, checkpoint/resume, and reports;
- `Shared/bull_llm`: backend adapters, profiles, schemas, evaluation contracts,
  telemetry, evidence, storage, compatibility, and presentation helpers.

The public Python namespace is `bull_llm`. Historical artifact schemas remain
readable through compatibility adapters and are never silently rewritten.

## Development roadmap

The current release is v0.28.0.1. The following stages are planned, not shipped:

| Stage | Target | Purpose |
| --- | --- | --- |
| U2 — Quick Compare | v0.28.1.0 | A separate candidate short pack, explicit language coverage and a confirmatory run |
| Reliable Runs — T5.3/T5.2 | TBD | Full interruption recovery coverage, followed by hardware comparability and additional measurements |
| P1 — Anywhere | TBD | Linux/macOS client after extracting the production backend/transport path |

Minimum resume safety and execution permissions belong to U1. Equal results must
not produce an arbitrary winner; missing evidence must remain visible. The
8–15-minute quick-comparison target applies to a documented setup, not every
machine. User demand may move Anywhere ahead of the full hardware Matrix.

Field Lab and Open Range have no assigned release versions. GUI, a hosted
leaderboard and a marketplace remain outside the near-term scope. The stable
CHAT Core content and hashes stay frozen; scorer corrections, new tasks and
runtime changes are independently versioned and reviewed.

See the [detailed roadmap and acceptance criteria](../BULL_TRANSITION_ROADMAP.md)
and the `planned_roadmap` section in [AI context](../AI_CONTEXT.yaml).

## Change rules

- no big-bang rewrite;
- preserve behavior with regression tests before extracting a module;
- do not change benchmark prompts, scorers, and runtime pipeline in one change;
- keep native model quality separate from client recovery;
- make small, reviewable commits;
- update both language trees and `AI_CONTEXT.yaml` for a release.

## Tests

```powershell
.\Run-Tests.ps1
.\Test-Public-Release.ps1 -AuditReleaseCandidatesOnly
.\Build-Release.ps1
```

The suite covers scorer and benchmark contracts, resume, runtime fingerprints,
order planning, typed shared contracts, UX/localization, forced cp1251 startup,
PowerShell launchers, manifests, privacy rules, and the generated ZIP.

New behavior needs a focused regression test. Benchmark methodology changes also
need golden fixtures and review of false positives and false negatives.

## Public release boundary

Build from a clean checkout. Do not package local outputs or secrets. Verify the
manifest against the staging tree and the ZIP contents, run the client from the
unpacked release, and test offline startup plus one local or synthetic path.

Release assets should include the bundle ZIP and its SHA-256 file. GitHub download
statistics count release-asset downloads; repository source archives are not part
of that asset count.

## Contributions

Use Discussions for methodology proposals and Issues for reproducible defects.
Explain the decision a change supports, the metric affected, the evidence, and
compatibility impact. Keep prompts, scorers, and runtime changes independently
reviewable.
