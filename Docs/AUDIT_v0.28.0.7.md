# Public release audit — BULL v0.28.0.7

## Scope

This patch fixes the interpretation and presentation of sampling values inherited
from Ollama Modelfiles. Built-in benchmark prompts, scorers, recovery, inference,
and backend connection behaviour are unchanged.

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
