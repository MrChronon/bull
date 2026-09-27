# BULL v0.24.0.0 — changelog

## Added

- data-only BULL Benchmark Registry with strict pack discovery and validation;
- manifest v1 JSON Schema, lifecycle states and public/private pack roots;
- canonical JSON compilation, SHA-256 gold snapshots and `pack.lock.json`;
- stable `bull_chat_core@1.0.0` pack containing the unchanged 12-case CHAT Core;
- `/bench pack list`, `/bench pack validate` and `/bench pack inspect`;
- bounded deterministic `cartesian_v1` case generator;
- benchmark pack authoring guide and 12 registry security/regression checks.
- one-time terminal pixel-bull mark on the first home screen;
- direct OpenSSH alias onboarding through `ssh -G`, existing `IdentityFile` and
  trusted `known_hosts`, plus an in-app key/alias walkthrough.

## Security

- packs cannot contain executable files, links, absolute paths or path traversal;
- runner, scorer and verifier references resolve only through engine allowlists;
- unknown references, duplicate identities, hash damage and incompatible engine or
  case versions fail before inference;
- private packs stay under `Runtime/BenchmarkPacks` and are excluded from release.

## Fixed

- the Windows PowerShell 5.1 launcher is ASCII-safe, fixing v0.23 windows that
  opened and closed immediately because a BOM-less UTF-8 em dash caused a parse
  error;
- startup failure-path regression now bypasses the success cache and cannot report
  a false positive after an earlier successful launch.
- release filtering no longer mistakes `Shared/bull_llm/runtime` for the private
  root `Runtime` directory;
- the Client installer shortcut is ASCII-safe under Windows PowerShell 5.1;
- duplicate legacy launchers and the old internal Python package were removed.
- SSH alias names are option-safe; ProxyCommand/ProxyJump are rejected, and an
  unknown host key still requires independent fingerprint verification.
- new balanced runs use a job-level counterbalanced execution plan instead of one
  fixed model block and one fixed seed position; legacy checkpoints keep their
  original order when resumed;
- tested-profile export groups identical importable Client configurations, keeps
  plural evidence fingerprints and does not import the first benchmark seed;
- native effective configuration records requested and suppressed recovery
  separately instead of claiming that recovery was active.
- brand-image regression uses standard-library PNG/ICO header validation instead
  of requiring Pillow on a fresh Client installation;
- the remaining visible `LOCAL LLM DASHBOARD` title is now `BULL CHAT DASHBOARD`.

## Intentionally unchanged

- CHAT Core prompts, result instructions, scorer IDs and score semantics;
- generation, recovery behavior, resume safety and model runtime settings;
- native versus assisted metric separation;
- legacy artifact schemas and v0.23 compatibility behavior.
