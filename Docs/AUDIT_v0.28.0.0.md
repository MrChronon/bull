# Public release audit — BULL v0.28.0.0

## Scope

This release contains the Clear Choice decision-support and user-task contract
updates. Built-in prompts, built-in scorer definitions, and inference/recovery
runtime behavior were not changed in this release.

## Public-data boundary

The release process excludes `Chats`, `Runtime`, `Benchmarks`, `Exports`,
`Workspace`, local settings, logs, private keys, known-hosts files, tokens,
endpoints, and personal paths. It runs a fail-closed content scan on both the
source candidate and staged bundle.

## Verification required for the release candidate

- `Run-Tests.ps1` in UTF-8;
- forced-cp1251 regression via `Build-Release.ps1`;
- `Test-Public-Release.ps1` source and staged audits;
- manifest hash verification before and after packaging;
- archive entry verification and SHA-256 output.

The scanner reduces accidental disclosure risk; it does not replace human review
of the final ZIP contents and Git diff.
