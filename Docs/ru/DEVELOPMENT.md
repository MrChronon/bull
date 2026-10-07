# Разработка и выпуск релиза

## Архитектура

BULL сохраняет три продуктовые границы:

- Client: чат, lifecycle сессии и явный импорт tested profile;
- Benchmark Lab: каталог, план запуска, scoring, checkpoint/resume и отчёты;
- `Shared/bull_llm`: backend adapters, profiles, schemas, evaluation contracts,
  telemetry, evidence, storage, compatibility и presentation helpers.

Публичный Python namespace — `bull_llm`. Исторические schemas артефактов читаются
через compatibility adapters и никогда не переписываются молча.

## Дорожная карта разработки

Текущий релиз — v0.28.0.7. Следующие этапы запланированы, но ещё не выпущены:

| Этап | Целевая версия | Назначение |
| --- | --- | --- |
| U2 — Quick Compare | v0.28.1.0 | Отдельный короткий candidate pack, явное языковое покрытие и подтверждающий прогон |
| Reliable Runs — T5.3/T5.2 | TBD | Полная проверка восстановления, затем аппаратная сопоставимость и дополнительные измерения |
| P1 — Anywhere | TBD | Linux/macOS client после извлечения рабочего backend/transport-пути |

Минимальная защита resume и разрешения на выполнение кода относятся к U1.
Равные результаты не должны давать случайного победителя; нехватка данных
показывается явно. Цель короткого сравнения за 8–15 минут относится к описанной
конфигурации, а не к любому компьютеру. При подтверждённом спросе Anywhere
может опередить полную аппаратную Matrix.

Для Field Lab и Open Range номера релизов не назначены. GUI, публичный
лидерборд и marketplace не входят в ближайшие этапы. Содержимое и hashes
стабильного CHAT Core сохраняются; исправления scorer, новые задачи и runtime
изменяются с независимым версионированием и review.

Подробности: [roadmap и критерии приёмки](../BULL_TRANSITION_ROADMAP.md),
раздел `planned_roadmap` в [AI-контексте](../AI_CONTEXT.yaml).

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
