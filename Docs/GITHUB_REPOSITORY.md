# GitHub repository handoff / Комплект репозитория

Publication edition: **BULL v0.29.0.1 — Pack Library**, 11 October 2026,
owner-authorized pre-release. Manual acceptance remains open.
Публикация разрешена владельцем как pre-release; ручная приёмка ещё открыта.

Release-time settings checked: Issues and the `bug`/`enhancement` labels are
available; Discussions and private vulnerability reporting are enabled.
При подготовке публикации проверены Issues и labels; включены Discussions
и приватный канал уязвимостей. Настройки сообщества не заменяют приёмку приложения.

## About settings / Настройки About

Repository: the existing public project linked from root README/CITATION;
use that identity, not a private development remote.

English description:

> Windows-first local LLM chat and reproducible model comparisons: versioned test packs, private checkpoints and offline reports for Ollama/llama.cpp.

Русское описание:

> Чат и воспроизводимое сравнение локальных LLM: наборы тестов, приватные checkpoints и автономные отчёты для Ollama/llama.cpp на Windows.

Suggested topics / Предлагаемые topics:

`llm`, `local-llm`, `benchmark`, `ollama`, `llama-cpp`, `model-evaluation`,
`python`, `windows`, `reproducibility`, `privacy`, `terminal`, `benchmark-packs`.

Use the existing repository URL as the website unless the owner supplies a
real project site. Do not add unsupported-platform topics or a placeholder website.
Social preview: `Assets/Brand/github-social-preview.png`, from the locked brand.
Owner must enable/check Issues, Discussions and private vulnerability reporting;
having Markdown links does not prove those settings are active.

Если сайта нет, используйте адрес репозитория, не выдуманный URL. Social preview
уже есть в `Assets/Brand`. Issues, Discussions и приватный канал уязвимостей
включает/проверяет владелец отдельно. Наличие ссылки не доказывает включение сервиса.

## Repository contents / Состав

| Area / Раздел | Purpose / Назначение |
| --- | --- |
| README.md / README_RU.md | English/Russian project page, requirements and quick start |
| LICENSE / THIRD_PARTY_NOTICES.md / CITATION.cff | Rights, dependencies and citation metadata |
| CONTRIBUTING*, SUPPORT*, CODE_OF_CONDUCT*, SECURITY.md | Full EN/RU community and security entrypoints |
| CHANGELOG.md / GITHUB_RELEASE_v0.29.0.1.md | Current/historical change index and bilingual release body |
| Docs/en / Docs/ru | Installation, use, results, packs, author/LLM instructions, roadmap and releasing |
| AGENTS.md / Docs/AI_CONTEXT.yaml | Portable coding-agent instructions and machine-readable state |
| Apps / Shared / Tools / Schemas | Source, native-launcher source, contracts and builders |
| Tests / BenchmarkPacks / BasePacks | Regression, public reference inputs and four optional ZIPs |
| Assets | Locked BULL branding, theme assets and localization |
| Setup.exe / Setup / launch scripts | Native setup and verified client payload; no root BULL.exe before installation |
| RELEASE_MANIFEST.json | Exact distributed file hashes; not a cryptographic signature |
| .github | Issue forms, PR checklist and security-policy pointer |

Private configured state, user-library contents, models, QA logs and `.git` do
not belong in the uploaded snapshot. Preserve existing public history when
updating an established repository; never upload private development history.
Use a fresh, audited ZIP extraction as the source snapshot, not the configured
application folder or a blanket copy of the development workspace.

Приватные настройки, пользовательские наборы, модели, QA-логи и `.git` не входят
в snapshot. Обновляя существующий публичный репозиторий, сохраняйте его историю;
приватную историю разработки не переносите. Источник — проверенная свежая
распаковка ZIP, не настроенная установка или вся рабочая папка.

## Release identity / Идентификаторы

- Tag: `v0.29.0.1`; title: `BULL v0.29.0.1 — Pack Library`.
- Body: [prepared EN/RU text](../GITHUB_RELEASE_v0.29.0.1.md).
- Assets: `BULL-v0.29.0.1-Bundle.zip` and `BULL-v0.29.0.1-Bundle.sha256.txt`.
- Use draft for asset verification, then publish as pre-release while acceptance is open.
- If this tag/assets already exist publicly, do not replace their bytes or move
  the tag: choose a new version through the release process.
- The automatic GitHub source archive is not the tested installation ZIP.

До публикации — draft; при открытой приёмке для пользовательского тестирования —
pre-release. Существующие опубликованные tag/assets не заменяйте. Дата CITATION
добавляется только при реальной публикации с повторной упаковкой изменённых файлов.

[English releasing](en/RELEASING.md) · [Публикация на русском](ru/RELEASING.md)
