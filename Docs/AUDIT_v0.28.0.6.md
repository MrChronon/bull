# Public release audit — BULL v0.28.0.6

## Scope

This patch changes benchmark selection navigation and optional system-resource
telemetry. Built-in benchmark prompts, scorers, inference, recovery, and backend
connection behaviour are unchanged.

## Public-data boundary

The release excludes `Chats`, `Runtime`, `Benchmarks`, `Exports`, local
settings, logs, private keys, known-hosts files, tokens, endpoints, and
personal paths. The splash accepts no external URL or user-supplied path; it
loads only the bundled versioned PNG.

## Required validation

- `Run-Tests.ps1` in UTF-8;
- forced cp1251 regression through `Build-Release.ps1`;
- source and staged public-release audits;
- manifest hash verification before and after packaging;
- archive entry verification and SHA-256 output.
