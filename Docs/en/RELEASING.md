# Preparing and publishing BULL

[Русский](../ru/RELEASING.md) · [Repository handoff](../GITHUB_REPOSITORY.md)

Current version: **v0.29.0.1**, the owner-designated latest stable release.
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
Normally use a candidate/pre-release while checks are unresolved. An explicit owner
decision may designate stable with those limits disclosed; never claim unrun checks
are completed or call every environment fully verified.

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
Use the classification explicitly authorized by the owner. v0.29.0.1 was initially
published as pre-release, then explicitly designated **stable/latest** without new bytes.
Review the complete draft before publication. GitHub documents these controls in
[Managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

Private reporting is a repository setting, not enabled by SECURITY.md; see
[GitHub's configuration guide](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).
No feature setting is assumed enabled during local preparation.

On actual publication, update status and CITATION's date consistently, rebuild
the final bundle/checksum and verify the draft assets before making it public.
Do not edit published archive bytes or retarget an existing public tag.
If publication is postponed, leave `date-released` absent rather than guessing.

For a metadata-only promotion, update release status/body and current EN/RU pages
in a documentation commit. Keep the original date, tag target and both asset bytes;
verify stable/latest through GitHub and recheck downloads. The manifest remains
the tagged distribution inventory. Archived pre-release wording is historical,
not a reason to replace a published ZIP under the same version.

## 5. Post-publication inspection

Test both version-specific download links and the checksum on downloaded assets.
Check EN/RU README navigation, rendered local images, docs, Issue forms, license,
security policy, tag/commit identity and installed behavior. Record the public
release URL and final SHA-256 locally. Never use GitHub download counts as proof
of successful installation, benchmark quality or usability.
