# Preparing and publishing BULL

[Русский](../ru/RELEASING.md) · [Repository handoff](../GITHUB_REPOSITORY.md)

Current version: **v0.29.0.1**, an owner-authorized pre-release for user testing.
Future source pushes, drafts/tags, repository settings and publication require
owner authorization. This guide is a procedure, not authorization by itself.

## 1. Freeze and verify

Read AGENTS, AI_CONTEXT, the paired guides and [acceptance status](../RELEASE_READINESS.md).
Resolve version/metadata differences before building. Keep historical pack/scorer
versions immutable. Do not include a configured installation or private Git history.

```powershell
.\Run-Tests.ps1
.\Test-Public-Release.ps1 -AuditReleaseCandidatesOnly
# Create a new, empty output directory; never overwrite an earlier archive.
New-Item -ItemType Directory -Path 'RELEASE_OUTPUT'
.\Build-Release.ps1 -OutputDirectory 'RELEASE_OUTPUT'
```

The pipeline verifies UTF-8 and forced-cp1251 regression, native launchers,
PowerShell, essential startup, public/staged privacy, the manifest and ZIP hashes.
Freshly extract the final ZIP: confirm no root BULL.exe, check Setup, completion,
installed launchers/shortcuts and full diagnostics in an isolated profile.
Check source/ZIP documentation bytes and the external checksum too.

## 2. Record acceptance honestly

Record first/repeat Terminal geometry, immediate Red/Matrix switching, clean exit,
folder release, clean-machine dependencies and live chat/benchmark/resume on the
intended local/SSH backends. Automated fixtures do not certify those scenarios.
Unresolved checks require a candidate/pre-release label, not a “fully verified” claim.

## 3. Prepare the public snapshot

Use only the final audited ZIP contents; keep `.github` and `.gitignore` when
copying. Preserve the established public repository's history, not the private
workspace's `.git`. Review the [repository inventory and About metadata](../GITHUB_REPOSITORY.md).
Keep root `.gitattributes`: the manifest requires exact bytes, not normalized
line endings. Compare the staged/committed Git blobs with every ZIP entry;
a clean working directory alone does not prove byte-for-byte parity.
Enable/check the actual issue labels (`bug`, `enhancement`), Issues/Discussions
and a working private vulnerability-reporting channel before advertising them.
Do not publish secrets or QA/runtime files. Keep the canonical logo/license intact.

## 4. Owner-authorized GitHub release

Check the proposed tag is unused. Target the exact public source commit matching
the ZIP, not a moving development branch. Create a **draft** with the prepared
[bilingual body](../../GITHUB_RELEASE_v0.29.0.1.md) and both ZIP/checksum assets.
Use **pre-release** while manual acceptance is open; do not mark it latest stable.
Review the complete draft before publication. GitHub documents these controls in
[Managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

Private reporting is a repository setting, not enabled by SECURITY.md; see
[GitHub's configuration guide](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).
No feature setting is assumed enabled during local preparation.

On actual publication, update status and CITATION's date consistently, rebuild
the final bundle/checksum and verify the draft assets before making it public.
Do not edit published archive bytes or retarget an existing public tag.
If publication is postponed, leave `date-released` absent rather than guessing.

## 5. Post-publication inspection

Test both version-specific download links and the checksum on downloaded assets.
Check EN/RU README navigation, rendered local images, docs, Issue forms, license,
security policy, tag/commit identity and installed behavior. Record the public
release URL and final SHA-256 locally. Never use GitHub download counts as proof
of successful installation, benchmark quality or usability.
