# BULL v0.29.0.1 documentation

[English documentation](en/README.md) · [Документация на русском](ru/README.md)

The current documentation is maintained in two equivalent language trees:

| Topic | English | Русский |
| --- | --- | --- |
| Installation, menus, chat and reports | [User guide](en/USER_GUIDE.md) | [Руководство пользователя](ru/USER_GUIDE.md) |
| Built-in and user-owned benchmarks | [Benchmarks](en/BENCHMARKS.md) | [Бенчмарки](ru/BENCHMARKS.md) |
| Live output, rankings and HTML reports | [Results](en/RESULTS.md) | [Результаты](ru/RESULTS.md) |
| Local, SSH and Internet connections | [Connections](en/CONNECTIONS.md) | [Подключения](ru/CONNECTIONS.md) |
| Privacy and threat model | [Security](en/SECURITY.md) | [Безопасность](ru/SECURITY.md) |
| Agent Lab | [Experimental features](en/EXPERIMENTAL.md) | [Экспериментальные функции](ru/EXPERIMENTAL.md) |
| Architecture, tests and release process | [Development](en/DEVELOPMENT.md) | [Разработка](ru/DEVELOPMENT.md) |
| Pack installation, versions and subsets | [Pack library](en/PACK_LIBRARY_GUIDE.md) | [Библиотека наборов](ru/PACK_LIBRARY_GUIDE.md) |
| Editable sources and ZIP building | [Author Workshop](en/AUTHOR_WORKSHOP.md) | [Мастерская автора](ru/AUTHOR_WORKSHOP.md) |
| Cloud LLM authoring instructions | [LLM instructions](en/PACK_AUTHOR_LLM.md) | [Инструкция для LLM](ru/PACK_AUTHOR_LLM.md) |
| v0.29.0.1 Pack Library | [Release notes](en/RELEASE_NOTES.md) | [Описание релиза](ru/RELEASE_NOTES.md) |

Release documentation: **BULL v0.29.0.1 Pack Library**. Use the release ZIP and
matching checksum; do not copy a configured old bundle over a fresh installation.

Documentation synchronized **11 October 2026** for pre-release v0.29.0.1;
the 10 October behavior is unchanged and manual acceptance remains open.
Current automated release gates: 668/668 offline, 668/668 cp1251 and 18/18 startup.
See [corrections and acceptance limits](FOLLOWUP_2026_10_10.md) and
[roadmap 1.10](BULL_TRANSITION_ROADMAP.md): implemented work, open manual acceptance
and future stages are listed separately. [Release readiness](RELEASE_READINESS.md)
separates archive verification from manual acceptance. Rebuild the final ZIP and
checksum after this synchronization; do not distribute an older archive as current.

`AI_CONTEXT.yaml` is the machine-readable engineering contract used by coding
agents. It is language-neutral and does not replace the user guides. The public
[AGENTS.md](../AGENTS.md) supplies portable project rules without a private parent workspace.

## GitHub release kit

[Repository inventory and metadata](GITHUB_REPOSITORY.md),
[prepared bilingual release body](../GITHUB_RELEASE_v0.29.0.1.md),
[English publishing guide](en/RELEASING.md) / [русская инструкция](ru/RELEASING.md),
[changelog index](../CHANGELOG.md) and [dependencies/rights](../THIRD_PARTY_NOTICES.md)
are part of the verified package. Full English/Russian contributing, support and
conduct documents live at the root; vulnerability reporting uses [SECURITY.md](../SECURITY.md).
This preparation adds no new runtime, prompt or scorer behavior and performs no remote publication.

## Reference and archive

Pack Library requirements: [requirements and delivery gates](PACK_LIBRARY_SPEC.md).
Install and select packs: [English](en/PACK_LIBRARY_GUIDE.md) · [Русский](ru/PACK_LIBRARY_GUIDE.md).
Editable author sources, fixture validation and ZIP building: [English](en/AUTHOR_WORKSHOP.md) · [Русский](ru/AUTHOR_WORKSHOP.md).
Data/engine separation: [PK1.2 boundary contract](PACK_ENGINE_BOUNDARY.md).
Instructions for drafting test sources with a cloud LLM:
[English](en/PACK_AUTHOR_LLM.md) / [Русский](ru/PACK_AUTHOR_LLM.md).
The library and workshop are offline-first; no pack is automatically downloaded or published.

The documents stored directly in `Docs/` provide detailed technical reference,
design history, audits and earlier release records. Current product behavior and
menu names are defined by the paired guides above. Earlier audits/changelogs and
release notes are historical records. The current v0.29.0.1 audit/changelog have
an explicit current-scope pointer followed by the preserved 644-check snapshot;
do not read its old totals or status-strip wording as the current behavior.
