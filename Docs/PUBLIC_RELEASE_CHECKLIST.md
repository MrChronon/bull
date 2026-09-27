# Public release checklist

Use this checklist for every GitHub release.

## Automated gates

- Run `Test-Public-Release.ps1` from the bundle root.
- Run `Run-Tests.ps1` in UTF-8 and the forced cp1251 gate through `Build-Release.ps1`.
- Verify `RELEASE_MANIFEST.json`, staged hashes, ZIP structure, and the published SHA-256 file.
- Confirm that the ZIP contains no runtime directories or local settings.

## Privacy review

- No private key, public connection bundle tied to a real node, API token, password, `.env`, `known_hosts`, or `Runtime/connections.json`.
- No Windows username, home-directory path, e-mail address, hostname, private endpoint, VPN address, or personal model path.
- No `Chats`, `Benchmarks`, `Exports`, `Workspace`, `client_debug.log`, `ui_settings.json`, screenshots, or terminal transcripts from a real environment.
- Regression fixtures use synthetic or anonymized provenance. Raw user benchmark results are not release fixtures.
- Documentation examples use loopback, reserved documentation domains, or explicit placeholders.

## Product review

- Fresh local launch does not open SSH and does not know any private server.
- Client, Benchmark Lab, Server, and AllInOne installation roles remain available.
- Interrupted benchmark resume reconnects before reading the model catalog and replays only the unfinished run.
- HTML reports are offline, escape model/test labels, and never embed prompts or raw answers.
- Native model quality and final system quality are labeled separately.

## Repository review

- `README.md`, `.gitignore`, security policy, contributing guide, Issue Forms, changelog, user guide, and AI context match the release version.
- The root `LICENSE` contains the owner-approved MIT text and README links to it.
- Inspect `git status` and the final ZIP file list before publishing.

## Clean public-repository workflow

Do not push the development repository or its history merely because the current release ZIP passed. Old commits, historical baselines and untracked bundles can contain machine/model provenance that is intentionally absent from the public release.

1. Build and verify `BULL-v0.24.0.0-Bundle.zip` and its SHA-256.
2. Extract the audited bundle into a new empty directory.
3. Add the license selected by the repository owner.
4. Run `Test-Public-Release.ps1` again from that directory.
5. Initialize a new Git repository there and inspect the complete first commit before adding a GitHub remote.

Rewriting or force-pushing the private development history is not part of the release build and requires a separate explicit decision.
