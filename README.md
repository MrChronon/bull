# BULL — Benchmark Lab

![BULL wordmark](Assets/Brand/bull-wordmark.png)

BULL is a portable Windows client and reproducible benchmark laboratory for
local LLMs served by Ollama or a compatible llama.cpp HTTP server. It supports
models on the same computer and separately administered Windows nodes reached
through a pinned SSH tunnel.

v0.24.0.0 is the **BULL Registry** release. It adds safe, versioned data-only
benchmark packs around the proven runtime while intentionally preserving CHAT
prompts, scorers, recovery behavior and legacy artifact schemas. The bundled
`bull_chat_core@1.0.0` pack is hash-checked against the former built-in suite.

## Start

1. Download `BULL-v0.24.0.0-Bundle.zip` and verify its SHA-256 file.
2. Run `Install-BULL-v0.24.0.0.cmd`.
3. Choose `Client`, `Server`, or `AllInOne`.
4. Start `BULL-v0.24.0.0.cmd` for the client or
   `BULL-Benchmark-Lab-v0.24.0.0.cmd` for benchmarks.

This release ships only BULL launchers and the `Shared.bull_llm` Python namespace.
See [the migration guide](Docs/MIGRATION_TO_BULL.md) before updating older automation.
The [documentation index](Docs/README.md) separates current instructions from
historical audits and release provenance.

The interface opens offline. A stopped Ollama does not block connection setup,
help, diagnostics or saved reports. Remote inference remains loopback-only behind
SSH; never expose Ollama `11434` or llama.cpp `8080` directly to the Internet.

If `ssh bull-home` already works with your key, choose **Connections → SSH alias**
and enter `bull-home`; BULL resolves the direct profile through OpenSSH and keeps
strict host-key pinning. See [SSH quick start](Docs/SSH_QUICKSTART.md). The first
home screen also carries the compact terminal pixel-bull mark.

## What is included

- LLM Client for chat and imported tested profiles;
- Benchmark Lab with checkpoint/resume, native vs assisted metrics and offline HTML;
- Agent Lab MVP with independent verification;
- experimental Windows + Ollama GPU Lab;
- typed `bull_llm.core`, runtime adapters, evaluation, telemetry and report boundaries;
- data-only Benchmark Registry with public/private roots, lifecycle, gold snapshots
  and canonical hashes;
- one self-contained `Shared.bull_llm` namespace plus read-only artifact compatibility.

Language models are not bundled. Generated-code execution is not an OS sandbox;
use a disposable VM without secrets or network access for untrusted output.

## Verification

```powershell
.\Run-Tests.ps1
.\Test-Public-Release.ps1 -AuditReleaseCandidatesOnly
.\Build-Release.ps1
```

The release builder validates documentation versions, UTF-8 and forced cp1251,
startup integration, privacy exclusions, brand assets, manifest hashes and ZIP
contents. It excludes `Chats`, `Runtime`, `Benchmarks`, `Exports`, `Workspace`,
keys and local logs.

Read the [user guide](Docs/USER_GUIDE.md), [release notes](Docs/RELEASE_NOTES_0.24.0.0.md),
[pack authoring guide](Docs/BENCHMARK_PACK_AUTHORING.md), [security model](Docs/SECURITY.md)
and [public-release checklist](Docs/PUBLIC_RELEASE_CHECKLIST.md).

## Naming and license

Use the qualified name **BULL — Benchmark Lab** on first mention. The
technical namespace is `bull_llm`; legacy schema identifiers remain unchanged.
“BULL” is not claimed as a unique unqualified ecosystem name.

BULL is released under the [MIT License](LICENSE). Third-party models, engines
and benchmark packs retain their own licenses and are not relicensed by BULL.
