# BULL v0.29.0.1 — release readiness

Documentation synchronized: **11 October 2026**.
Status: **v0.29.0.1 pre-release for user testing; not latest stable**.
Publication was explicitly authorized by the owner. This record distinguishes
automated release gates from still-open user acceptance; it is not a claim
that a live model comparison was performed.

The full [GitHub repository kit](GITHUB_REPOSITORY.md) and
[bilingual release body](../GITHUB_RELEASE_v0.29.0.1.md) are prepared with this
documentation revision. Community policies, metadata and forms are included;
the same manual acceptance boundary remains. The public source uses the audited
ZIP snapshot on the existing public history, never private development history.
Root `.gitattributes` preserves exact bytes for manifest/ZIP/source parity.
Version-specific release/download links are in the root README.

## Current release contract

- Setup.exe is the first entrypoint. BULL.exe is absent from the distributed
  root and is materialized only after the full regression and connection setup/skip.
- Six Home sections; only integrity and connection appear in the Home status.
  Pack readiness and pack → task browsing are inside testing/test settings.
- Exactly BULL Red / BULL Matrix. High contrast, GPU Lab and server/all-in-one
  installer roles are retired; ordinary resource telemetry remains.
- Shared pack storage is `%LOCALAPPDATA%/BULL/BenchmarkPacks`, resolved for the
  current user. One exact installed version is selected per run.
- Language pack 1.0.1/scorer v2 and specialized RU/EN reporting are current;
  historical 1.0.0/v1 and existing results remain unchanged. No merged winner
  or arbitrary executable pack-report template is available.

See the [follow-up](FOLLOWUP_2026_10_10.md), [current release notes](en/RELEASE_NOTES.md),
[user guide](USER_GUIDE.md) and [roadmap 1.10](BULL_TRANSITION_ROADMAP.md).
The earlier 644-check audit/changelog sections are explicitly historical snapshots.

## Automated evidence and reproducible release gate

Publication gates: **668/668 offline**, **668/668 forced cp1251**, **18/18 essential
startup**, source/staging privacy, exact manifest/ZIP hashes and isolated Setup/full
diagnostics. A documentation-only update does not inherit archive freshness:
rerun the release pipeline for every final tree before distribution.

```powershell
.\Run-Tests.ps1
.\Test-Public-Release.ps1 -AuditReleaseCandidatesOnly
.\Build-Release.ps1 -OutputDirectory "PATH_TO_NEW_EMPTY_OUTPUT_DIRECTORY"
```

The output directory must already exist and must not contain an archive with
the same name. Keep old archives intact. Verify the external SHA-256, the exact
ZIP/manifest inventory, every entry hash and a fresh-extraction startup before
distribution. The final ZIP must contain the current documents and AGENTS.md,
not only matching application binaries. Do not put QA logs inside the bundle.

LLM author instructions and Author Workshop contracts are paired in English and
Russian. Their example scores are 1.00 / 0.59 / 0.00; fixture validation does not
prove domain references. AI_CONTEXT is valid YAML; local documentation links
must resolve. CITATION.cff identifies 0.29.0.1 and the pre-release publication date,
11 October 2026 in Europe/Moscow, not an earlier local build date.

## Open manual acceptance — not closed by automated tests

- Clean Setup → direct launch, then shortcut/repeated launch in Windows Terminal:
  full logo height, matching width/font, wordmark below it, immediate Red ↔ Matrix.
- Normal exit: owned children finish and the application folder can be deleted;
  do not stop a separately running model server to satisfy this check.
- Live chat, benchmark and interrupted checkpoint resume on the intended local
  and pinned SSH backends. The earlier read-only resource probe is not inference
  acceptance or proof for all servers.
- Clean-machine Python/dependency setup where installation is required; isolated
  launcher/shortcut tests do not replace this environment check.

Until these are recorded, describe the build as a **candidate for user testing**,
not a fully accepted stable public release. Pre-release publication does not
change this boundary; later publication still requires owner authorization.
