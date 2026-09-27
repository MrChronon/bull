# BULL v0.24.0.0 — BULL Registry

This release completes transition stage T3. Benchmarks can now be distributed as
independent, versioned data packs while the proven runtime and scorer
implementations remain inside the BULL engine.

## What users get

- the standard 12-case CHAT Core now loads through `bull_chat_core@1.0.0`;
- public packs live in `BenchmarkPacks`; personal packs live in
  `Runtime/BenchmarkPacks` and never enter a release archive;
- pack status is explicit: experimental, candidate, stable, deprecated or retired;
- `/bench pack list`, `validate` and `inspect` show lifecycle, references, case
  count and hashes without exposing prompts or gold answers;
- invalid installed packs stop benchmark discovery before any model request.

Install with `Install-BULL-v0.24.0.0.cmd`, then start
`BULL-v0.24.0.0.cmd`. The v0.23 launch failure under Windows PowerShell 5.1 is
also fixed; the entry script is now ASCII-safe before Python enables UTF-8.

The installer shortcut script is also PowerShell 5.1-safe. Release packaging now
excludes only the root private `Runtime` directory and always retains the engine
module `Shared/bull_llm/runtime`. Legacy launcher aliases and the duplicate
internal package were removed; runtime code imports only `Shared.bull_llm`.
The startup regression no longer imports Pillow just to inspect brand images, so
a clean Python installation passes the same fail-closed checks without hidden
third-party packages.

The home screen now opens with a compact terminal pixel bull. Connections add a
short OpenSSH-alias path: an already working direct key profile can be imported by
typing its `Host` name. BULL resolves it with `ssh -G`, reuses a matching trusted
`known_hosts` entry, preserves strict per-connection pinning and rejects
`ProxyCommand`, `ProxyJump` and option injection. An in-app walkthrough and
`Docs/SSH_QUICKSTART.md` cover key creation, server authorization and alias setup.

## For benchmark authors

Every pack declares identity, engine range, license, provenance, taxonomy,
content, gold snapshots and documentation. Packs contain JSON and text only.
Runner, scorer and verifier values are allowlisted IDs, not imports. Canonical
compilation produces stable hashes and a lock file. See
`Docs/BENCHMARK_PACK_AUTHORING.md` and the bundled CHAT Core reference pack.

## Measurement integrity

The CHAT Core extraction is hash-checked against the legacy v0.23 definitions at
runtime and in regression tests. This release does not change benchmark prompts,
result instructions, scorers, per-request generation, or runtime options. Native
output and client-assisted recovery remain separate measurements. A field-data
audit added job-level counterbalanced scheduling for new runs: model, test and seed
positions rotate across waves. Existing checkpoints resume in their original order.
Tested-profile export now deduplicates the importable Client payload and never
imports an evidence seed into normal chat settings.

## Security and privacy

Registry validation rejects executable content, symbolic links, traversal,
unknown engine references, duplicate pack/case identities, incompatible versions,
missing license metadata and damaged content/gold/lock hashes. Public release gates
still exclude models, Chats, Runtime, Benchmarks, keys, endpoints and local secrets.
The final candidate is also verified with `python -S`, which disables installed
site-packages and catches accidental dependencies on a developer workstation.

The repository source is released under the MIT License. Third-party models,
engines and benchmark packs retain their own licenses; pack contributions still
require explicit license and provenance metadata.
