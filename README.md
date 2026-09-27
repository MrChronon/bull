<p align="center">
  <img src="Assets/Brand/bull-wordmark.png" alt="BULL" width="720">
</p>

<p align="center">
  <strong>Benchmarking &amp; Usage of Local LLMs</strong><br>
  Reproducible local-model evaluation on the hardware you actually use.
</p>

<p align="center">
  <a href="https://github.com/MrChronon/bull/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/MrChronon/bull?style=for-the-badge&color=00E6A8&label=release"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/github/license/MrChronon/bull?style=for-the-badge&color=24D6FF"></a>
  <a href="https://github.com/MrChronon/bull/releases"><img alt="Downloads" src="https://img.shields.io/github/downloads/MrChronon/bull/total?style=for-the-badge&color=00E6A8"></a>
  <img alt="Windows 11" src="https://img.shields.io/badge/Windows_11-supported-24D6FF?style=for-the-badge&logo=windows11&logoColor=white">
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="Docs/USER_GUIDE.md">User guide</a> ·
  <a href="Docs/BENCHMARK_PACK_AUTHORING.md">Build a benchmark pack</a> ·
  <a href="https://github.com/MrChronon/bull/discussions">Discuss methodology</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

---

> **BULL is not a hosted leaderboard.** It is an open, portable benchmark lab for
> inspecting local LLM quality, stability, speed, recovery and runtime behavior
> without sending prompts or model output to a cloud service.

BULL — Benchmark Lab is a Windows-first client and reproducible evaluation
platform for local LLMs served by **Ollama** or a compatible **llama.cpp HTTP
server**. Run chat, compare selected models, resume interrupted suites, inspect
offline reports and move a tested profile into the working client.

## Why BULL

| Evaluation problem | How BULL handles it |
| --- | --- |
| Client recovery can hide weak native output | Reports **native model quality** and **final system quality** separately |
| One average hides unstable seeds | Shows mean, sample SD, min/max, worst seed and rank stability |
| Model/test order can distort speed | Uses job-level counterbalanced scheduling for new runs |
| Cold load and warm generation get mixed | Classifies warm measurements from observed load duration |
| A disconnect can invalidate hours of work | Atomically checkpoints completed runs and resumes only unfinished work |
| Benchmark changes are hard to audit | Uses versioned, hash-checked, data-only benchmark packs |
| Private endpoints leak into shared results | Excludes connections, keys, logs, chats and runtime state from public releases |

## What you can measure

- **CHAT quality:** instruction following, groundedness, dialogue state,
  causality, semantic negation, Russian business language and reasoning;
- **contract completion:** generation, structure, terminal JSON and exact schema
  are tracked as distinct facts;
- **performance:** load duration, warm tokens/second, VRAM and GPU telemetry;
- **stability:** multi-seed dispersion, worst cases, uncertainty-aware Pareto
  status and category-level comparisons;
- **system behavior:** recovery use, retries, fingerprints, resume provenance and
  tested-profile export;
- **agent behavior:** a restricted Agent Lab MVP with independent verification;
- **hardware experiments:** an experimental Windows + Ollama GPU Lab.

The bundled `bull_chat_core@1.0.0` pack contains the stable 12-case CHAT Core.
Its extracted definitions are hash-checked against the proven suite. Automatic
scores support investigation; they do not replace expert review or establish
general model superiority from a single run.

## Quick start

### Requirements

- Windows 11;
- Python 3 and PowerShell;
- Ollama or a compatible llama.cpp HTTP server;
- at least one model installed in the selected backend.

### Install

1. Download `BULL-v0.24.0.0-Bundle.zip` and its SHA-256 file from the
   [latest release](https://github.com/MrChronon/bull/releases/latest).
2. Verify the checksum, extract the archive and run
   `Install-BULL-v0.24.0.0.cmd`.
3. Choose `Client`, `Server` or `AllInOne`.
4. Start `BULL-v0.24.0.0.cmd` for chat or
   `BULL-Benchmark-Lab-v0.24.0.0.cmd` for evaluation.

The interface opens without a running backend, so connection setup, help,
diagnostics and saved reports remain available offline.

## Local, remote and all-in-one

```mermaid
flowchart LR
    M[Ollama / llama.cpp] --> R[BULL runtime]
    R --> C[LLM Client]
    R --> L[Benchmark Lab]
    R --> A[Agent Lab]
    L --> J[JSON / CSV / checkpoint]
    L --> H[Offline HTML report]
    L --> P[Tested profile]
    P --> C
```

- **Local:** client and models run on one Windows computer.
- **Remote:** BULL reaches a separately administered Windows node through a
  pinned SSH tunnel.
- **AllInOne:** install client and server roles on the same machine.

If `ssh bull-home` already works with your key, choose
**Connections → SSH alias** and enter `bull-home`. See the
[SSH quick start](Docs/SSH_QUICKSTART.md). Never expose Ollama `11434` or
llama.cpp `8080` directly to the Internet.

## Reproducible outputs

Each benchmark can produce raw JSON/CSV, summary JSON/CSV, an atomic checkpoint,
tested profiles and a self-contained HTML report. Reports separate descriptive
observations from claims and keep native model output distinct from client
assistance.

```powershell
.\Run-Tests.ps1
.\Test-Public-Release.ps1 -AuditReleaseCandidatesOnly
.\Build-Release.ps1
```

The current release passes **349/349 offline regressions**, including clean
Python without site packages, forced `cp1251`, startup integration, manifest
hashes and ZIP verification.

## Help shape the benchmark

The project is looking for rigorous criticism from local-LLM users, benchmark
authors, inference engineers and hardware experimenters.

- Use [Discussions](https://github.com/MrChronon/bull/discussions) for benchmark
  design, scorer trade-offs, taxonomy, hardware methodology and open-ended ideas.
- Open a [benchmark feedback issue](https://github.com/MrChronon/bull/issues/new/choose)
  for a concrete false positive, false negative or reproducibility problem.
- Open a bug report only when behavior is reproducible; sanitize endpoints,
  usernames, paths, prompts and model responses before attaching evidence.
- Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing prompts, scorers,
  schemas, runtime or benchmark packs.

English and Russian are both welcome. Small, test-backed pull requests are
preferred. The current architecture and transition plan live in
[Docs/BULL_TARGET_ARCHITECTURE.md](Docs/BULL_TARGET_ARCHITECTURE.md) and
[Docs/BULL_TRANSITION_ROADMAP.md](Docs/BULL_TRANSITION_ROADMAP.md).

## Security and privacy

Language models are not bundled. Generated-code execution is not an OS sandbox;
use a disposable VM without secrets or network access for untrusted output.
Public release gates exclude `Chats`, `Runtime`, `Benchmarks`, `Exports`,
`Workspace`, keys, endpoints and local logs. Read the
[security model](Docs/SECURITY.md) before exposing any server role.

## Project status

`v0.24.0.0` is the **BULL Registry** release. It introduces independent,
versioned data-only benchmark packs while preserving CHAT prompts, scorers,
recovery behavior and historical artifact compatibility. See the
[release notes](Docs/RELEASE_NOTES_0.24.0.0.md) and
[documentation index](Docs/README.md).

## License and naming

BULL is released under the [MIT License](LICENSE). Third-party models, engines
and benchmark packs retain their own licenses. Use **BULL — Benchmark Lab** on
first mention; the technical namespace is `bull_llm`.
