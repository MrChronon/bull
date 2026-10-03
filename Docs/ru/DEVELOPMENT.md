# Разработка и выпуск релиза

## Архитектура

BULL сохраняет три продуктовые границы:

- Client: чат, lifecycle сессии и явный импорт tested profile;
- Benchmark Lab: каталог, план запуска, scoring, checkpoint/resume и отчёты;
- `Shared/bull_llm`: backend adapters, profiles, schemas, evaluation contracts,
  telemetry, evidence, storage, compatibility и presentation helpers.

Публичный Python namespace — `bull_llm`. Исторические schemas артефактов читаются
через compatibility adapters и никогда не переписываются молча.

## Правила изменений

- не выполнять big-bang rewrite;
- сначала фиксировать поведение regression tests, затем извлекать модуль;
- не менять prompts, scorers и runtime pipeline в одном изменении;
- разделять native model quality и client recovery;
- делать небольшие проверяемые commits;
- для релиза обновлять обе языковые ветки и `AI_CONTEXT.yaml`.

## Проверки

```powershell
.\Run-Tests.ps1
.\Test-Public-Release.ps1 -AuditReleaseCandidatesOnly
.\Build-Release.ps1
```

Suite проверяет benchmark/scorer contracts, resume, runtime fingerprints, порядок
запусков, typed shared contracts, UX/localization, forced cp1251 startup,
PowerShell launchers, manifests, privacy и итоговый ZIP.

Новое поведение требует focused regression test. Изменение методики benchmark
также требует golden fixtures и проверки false positive/false negative.

## Граница публичного релиза

Сборка выполняется из чистого checkout. Локальные результаты и secrets не входят
в package. Manifest сверяется со staging tree и ZIP, затем клиент проверяется из
распакованного релиза в offline-режиме и на одном локальном или synthetic пути.

В GitHub release следует загружать bundle ZIP и его SHA-256. GitHub download
statistics считает загрузки release assets; source archives репозитория в этот
счётчик не входят.

## Участие в разработке

Discussions предназначены для предложений по методике, Issues — для
воспроизводимых дефектов. Опишите поддерживаемое решение, затронутую метрику,
evidence и compatibility impact. Prompts, scorers и runtime changes должны
оставаться независимо проверяемыми.

