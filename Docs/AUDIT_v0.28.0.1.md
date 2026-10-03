# Public release audit — BULL v0.28.0.1

## Scope

This is a presentation hotfix for startup verification. Built-in benchmark
prompts, scorers, inference and recovery behaviour are unchanged.

## Public-data boundary

The release excludes `Chats`, `Runtime`, `Benchmarks`, `Exports`, local
settings, logs, private keys, known-hosts files, tokens, endpoints, and
personal paths. The splash reads only a fixed versioned PNG bundled with the
release; it accepts no user-provided path or external URL.

## Verification required for the release candidate

- `Run-Tests.ps1` in UTF-8;
- forced-cp1251 regression through `Build-Release.ps1`;
- source and staged public-release audits;
- manifest hash verification before and after packaging;
- archive entry verification and SHA-256 output.
