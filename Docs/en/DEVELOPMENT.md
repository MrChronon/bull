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

BULL v0.29.0.1 Pack Library completes PK1.0–PK1.5. The engine uses a single
explicitly selected pack version; optional base ZIPs are never a catalog fallback.
The shared library, source workshop and complete private snapshots are independent
of application builds. Existing 16 definitions and 15 full scorer results remain
frozen by the extraction gold contracts. The local follow-up of 10 October has
**668/668 offline checks**, **668/668 forced-cp1251 checks** and **18/18 startup
checks**. Source/staging privacy, exact manifest/ZIP contents and extracted Setup
integration passed. These gates do not certify live model or terminal behavior.

| Next stage | Target | Purpose |
| --- | --- | --- |
| PK1 acceptance | Open | First/repeat terminal geometry, immediate theme switching, folder deletion after exit, live local/SSH chat/benchmark/resume |
| P1 — Anywhere — Linux | TBD | Linux terminal client on shared engine contracts and the same packs |
| U2 — Quick Compare | After P1 | Short candidate pack and confirmatory runs with explicit language coverage |
| Reliable Runs — T5.3/T5.2 | After U2 | Live fault recovery and hardware comparability in separate deliveries |
| RPT1 — Pack report profiles | Backlog; scheduling TBD | Engine-owned or schema-validated declarative views; no executable templates from packs |
| LANG1 — Language methodology | Research; scheduling TBD | More discriminating paired tasks, human validation and separately versioned scorer/content changes |

PK1 introduces no scorer, prompt or inference-pipeline rewrite and no Linux
implementation. The later language correction is separate: pack 1.0.1/scorer v2
penalizes foreign-script prose while preserving prompts/references and historical
v1. Specialized RU/EN reporting is implemented; general pack-report profiles are not.
See [follow-up scope and limits](../FOLLOWUP_2026_10_10.md).
Author criteria use existing deterministic scoring; open tasks
keep human review. Existing executable engine tests need explicit consent and
remain unsuitable for untrusted code outside a disposable VM.

Separate model/test settings, isolated executable checks and creative/LLM-judge
evaluation remain future work. See [Pack Library specification](../PACK_LIBRARY_SPEC.md),
[author instructions](PACK_AUTHOR_LLM.md) and [Author Workshop](AUTHOR_WORKSHOP.md).

Field Lab and Open Range have no assigned release versions. GUI, a hosted
leaderboard and a marketplace remain outside the near-term scope. The stable
CHAT Core content and hashes stay frozen; scorer corrections, new tasks and
runtime changes are independently versioned and reviewed.

See the [detailed roadmap and acceptance criteria](../BULL_TRANSITION_ROADMAP.md)
and the `planned_roadmap` section in [AI context](../AI_CONTEXT.yaml).

## Change rules

Read [AGENTS.md](../../AGENTS.md), [AI context](../AI_CONTEXT.yaml) and the current
user guide before changes. The public bundle contains these instructions.

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
order planning, typed shared contracts and UX/localization. `Run-Tests.ps1`
compiles source and runs the full offline regression. Forced cp1251, PowerShell
parse, source/staging audits, manifest and ZIP verification are separate release
gates in `Build-Release.ps1`; do not claim an archive was rebuilt by running tests.
Every application launch runs the 18 essential checks without a cached pass.
Setup and Additional → Diagnostics → Full regression run the full offline suite.

New behavior needs a focused regression test. Benchmark methodology changes also
need golden fixtures and review of false positives and false negatives.

## Public release boundary

Build from a clean checkout. Do not package local outputs or secrets. Verify the
manifest against the staging tree and the ZIP contents, run the client from the
unpacked release, and test offline startup plus one local or synthetic path.
Before Setup the root has `Setup.exe`, not `BULL.exe`; the manifest-verified
`Setup/BULL.launcher.bin` is materialized only after full verification and
connection setup/skip. Validate both pre-install and installed layouts. The ZIP
gate must include every mandatory file, all four base archives and the historical
language fixture, not just an outdated hard-coded language ZIP revision.

Source documentation and its manifest hashes can advance independently of an
existing ZIP. The 11 October synchronization requires a new archive/checksum
through the release pipeline; do not distribute the preceding archive as current.
See [release readiness](../RELEASE_READINESS.md). Publication remains separate;
automated success does not close manual terminal, shutdown or inference acceptance.

Release assets should include the bundle ZIP and its SHA-256 file. GitHub download
statistics count release-asset downloads; repository source archives are not part
of that asset count.

## Contributions

Use Discussions for methodology proposals and Issues for reproducible defects.
Explain the decision a change supports, the metric affected, the evidence, and
compatibility impact. Keep prompts, scorers, and runtime changes independently
reviewable.
