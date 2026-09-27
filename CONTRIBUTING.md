# Contributing to BULL

Thank you for helping improve BULL — Benchmark Lab. English and Russian are both
welcome. The best contribution is a small, reproducible change with a clear
measurement or user benefit.

## Choose the right channel

- **Discussion:** open-ended benchmark design, scorer trade-offs, taxonomy,
  hardware methodology, questions and early ideas.
- **Benchmark feedback issue:** a concrete false positive, false negative,
  ambiguous prompt, scorer blind spot or reproducibility problem.
- **Bug report:** reproducible application, installer, server or report failure.
- **Feature request:** a scoped capability with a user scenario and constraints.
- **Pull request:** an agreed or independently testable implementation.

Search existing Issues and Discussions before opening a new thread.

## Before opening an issue

1. Reproduce the behavior on the latest release.
2. Record the BULL version, component, backend and minimal steps.
3. Explain expected and observed behavior separately.
4. Remove keys, tokens, endpoints, usernames, personal paths, private prompts,
   model responses and unreviewed logs.
5. For scorer feedback, include the case ID, scorer version and the smallest
   sanitized example that demonstrates the problem.

## Before submitting code

1. Never add `Runtime`, `Chats`, `Benchmarks`, `Exports`, `Workspace`, models,
   keys, tokens, private addresses or personal paths.
2. Do not change a benchmark prompt, its scorer and the runtime pipeline in one
   pull request.
3. Preserve behavior with regression tests before extracting modules.
4. Keep native-model metrics separate from client-recovery metrics.
5. Prefer one verifiable semantic change per pull request.
6. Update `Docs/USER_GUIDE.md` and `Docs/AI_CONTEXT.yaml` when release behavior
   changes.

Run the relevant gates on Windows:

```powershell
.\Run-Tests.ps1
.\Test-Public-Release.ps1 -AuditReleaseCandidatesOnly
```

For release or packaging changes, also run:

```powershell
.\Build-Release.ps1
```

## Pull request description

Include:

- the problem and intended user outcome;
- the chosen design and alternatives considered;
- compatibility and security impact;
- tests and manual checks performed;
- whether prompts, scorers, runtime, schemas or artifacts changed;
- before/after evidence when UI or measurement behavior changes.

## Benchmark contributions

Benchmark packs must declare identity, engine compatibility, license,
provenance, taxonomy and content hashes. Packs are data-only: they may not load
Python modules or executable content. Read
[`Docs/BENCHMARK_PACK_AUTHORING.md`](Docs/BENCHMARK_PACK_AUTHORING.md).

Prompt, gold-answer and scorer changes require separate review because they can
break longitudinal comparability. Explain what failure mode the change detects,
which existing results become incomparable and how false positives were tested.

## License

BULL is released under MIT. By submitting a pull request, you confirm that you
have the right to contribute the work under the MIT License. External code,
datasets and benchmark packs require a compatible license and explicit
provenance.
