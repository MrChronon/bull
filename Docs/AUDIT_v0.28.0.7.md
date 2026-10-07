# Public release audit — BULL v0.28.0.7

## Scope

This audit covers the complete v0.28.0.7 public bundle: result presentation,
language-track separation, Ollama profile comparison, packaging, documentation,
privacy exclusions, and release integrity. Built-in benchmark prompts, scorers,
recovery, inference, and backend connection behaviour are unchanged.

## Public-data boundary

The release excludes `Chats`, `Runtime`, `Benchmarks`, `Exports`, local settings,
logs, private keys, known-hosts files, tokens, endpoints, and personal paths. The
splash accepts no external URL or user-supplied path; it loads only the bundled
versioned PNG.

## Required validation

- `Run-Tests.ps1` in UTF-8;
- forced cp1251 regression through `Build-Release.ps1`;
- source and staged public-release audits;
- manifest hash verification before and after packaging;
- archive entry verification and SHA-256 output.

## Verified release

- offline regression: **401/401**;
- manifest-controlled archive: **256 files**;
- mandatory BULL runtime and language-pack modules present;
- public launchers, paths, schemas, and documentation use BULL-only identifiers;
- obsolete splash assets and private runtime data absent;
- published assets: `BULL-v0.28.0.7-Bundle.zip` and
  `BULL-v0.28.0.7-Bundle.sha256.txt`.
