# Public release checklist

Use this checklist for every GitHub release.

Current edition: **v0.29.0.1 stable/latest**, documentation synchronized **11 October 2026**.
See [release readiness](RELEASE_READINESS.md): open manual acceptance is not a passed gate.

## Automated gates

- Run `Test-Public-Release.ps1` from the bundle root.
- Run `Run-Tests.ps1` in UTF-8 and the forced cp1251 gate through `Build-Release.ps1`.
- Recompile Setup.exe and BULL.exe from the shipped C# source using the release gate.
- Verify `RELEASE_MANIFEST.json`, staged hashes, ZIP structure, and the published SHA-256 file.
- Confirm that the ZIP contains no runtime directories or local settings.
- Freshly extract the final ZIP and check native launchers/startup; before Setup
  only Setup.exe is in the root, with the verified client payload under Setup/.

## Privacy review

- No private key, public connection bundle tied to a real node, API token, password, `.env`, `known_hosts`, or `Runtime/connections.json`.
- No Windows username, home-directory path, e-mail address, hostname, private endpoint, VPN address, or personal model path.
- No `Chats`, `Benchmarks`, `Exports`, `Workspace`, `client_debug.log`, `ui_settings.json`, screenshots, or terminal transcripts from a real environment.
- Regression fixtures use synthetic or anonymized provenance. Raw user benchmark results are not release fixtures.
- Documentation examples use loopback, reserved documentation domains, or explicit placeholders.

## Product review

- Fresh local launch does not open SSH and does not know any private server.
- Setup.exe offers language, BULL Red / BULL Matrix, optional packs, full regression, optional connection, launch or exit. It never provisions a server.
- Compare direct Launch BULL from setup with a later shortcut launch in the user's terminal; automated console tests do not replace visual acceptance.
- Verify theme-matched Desktop/Start icons without editing foreign shortcuts. The native launchers are unsigned; document possible Windows reputation warnings.
- Interrupted benchmark resume reconnects before reading the model catalog and replays only the unfinished run.
- HTML reports are offline, escape model/test labels, and never embed prompts or raw answers.
- Native model quality and final system quality are labeled separately.

## Repository review

- `README.md`, `.gitignore`, security policy, contributing guide, Issue Forms, changelog, user guide, and AI context match the release version.
- AGENTS.md and all mandatory LLM reads are present in the ZIP. Author instructions
  use shared-library storage and exact `ID@VERSION` commands; examples match the builder.
- EN/RU README, contributing/support/conduct, installation, roadmap and publishing
  guides are navigable. Root changelog, security, dependency notices and the
  bilingual GitHub release body are present in the exact ZIP/manifest inventory.
- Follow [GitHub repository handoff](GITHUB_REPOSITORY.md). Check real issue labels,
  Discussions and private reporting settings; local documents do not enable them.
- Target the exact public source commit. Classification needs explicit owner
  authorization and honest acceptance limits; never replace a published tag/archive.
- For metadata-only stable promotion, preserve tag/ZIP/checksum and original date.
  Verify stable/latest and synchronized EN/RU pages; later `main` documentation
  is not part of the tagged distribution manifest. Keep archive history intact.
- CITATION.cff uses the current version; add its release date only on publication.
  Issue Forms do not offer retired GPU Lab or AllInOne routes as current features.
- Historical audit/changelog scopes are explicit. Current totals are 668 full
  offline/cp1251 checks and 18 startup checks; do not present the 644-check snapshot as current.
- Compare source and ZIP documentation hashes; matching binaries alone do not prove
  that the latest guides/roadmap were packaged.
- Preserve root `.gitattributes` and verify Git blob hashes against the manifest:
  line-ending conversion must not change the public tag's distributed bytes.
- The root `LICENSE` contains the owner-approved MIT text and README links to it.
- Inspect `git status` and the final ZIP file list before publishing.

## Clean public-repository workflow

Do not push the development repository or its history merely because the current release ZIP passed. Old commits, historical baselines and untracked bundles can contain machine/model provenance that is intentionally absent from the public release.

1. Build and verify `BULL-v0.29.0.1-Bundle.zip` and its SHA-256.
2. Extract the audited bundle into a new empty directory.
3. Verify the owner-approved license included by the build; do not modify the audited snapshot.
4. Run `Test-Public-Release.ps1` again from that directory.
5. For an existing public repository, clone it separately and update from the
   audited snapshot while preserving its public history. Remove only reviewed
   obsolete public paths. For first publication only, initialize a new repository.
   In either case, inspect the exact staged/committed bytes before pushing.

Rewriting or force-pushing the private development history is not part of the release build and requires a separate explicit decision.
