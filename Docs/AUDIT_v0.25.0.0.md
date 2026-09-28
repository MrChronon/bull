# BULL v0.25.0.0 — аудит этапа T4 Evidence

Дата аудита: 28 сентября 2026 года.

## Область

Аудит охватывает evidence contracts, provenance, private/share-safe artifacts,
compatibility, миграцию, terminal/HTML reporting и release packaging. Benchmark
content, scorers, recovery и inference runtime не менялись.

## Подтверждённые свойства

- `quality.native` и `quality.assisted` имеют разные поля и не агрегируются в
  один score;
- recovery хранится как системная метрика и не изменяет native score;
- provenance имеет собственный schema/version и content hash;
- launch и effective runtime fingerprints сохраняются раздельно;
- hashes prompt/pack, scorer, verifier, spec и execution order воспроизводимы;
- SD не вычисляется для `n < 2`; CI и context curves не рисуются без данных;
- warm measurements классифицируются по фактическому load duration;
- private evidence сохраняет raw records, share-safe summary строится по
  allow-list;
- privacy audit блокирует prompts, raw answers, endpoints, e-mail, private-key
  данные и домашние пути;
- copy-only migration использует новый путь, проверяет source SHA-256 до/после и
  не допускает overwrite;
- HTML автономен: без CDN, JavaScript, prompts и raw answers;
- legacy artifacts распознаются compatibility layer.
- Agent stream deadline event считается авторитетным после принудительного
  shutdown, поэтому timeout не зависит от субмиллисекундной гонки scheduler.

## Производительность

SHA-256 исходника клиента кэшируется в процессе, поэтому provenance не читает
много-мегабайтный core заново для каждого run. Нормализация evidence выполняется
один раз при финализации suite и не меняет inference timing.

## Privacy и публичный релиз

В репозиторий и ZIP не включаются `Chats`, `Runtime`, `Benchmarks`, `Exports`,
`Workspace`, ключи, connection vault, endpoints и debug logs. Share-safe не
означает анонимный: model labels специально сохранены и должны быть просмотрены
пользователем перед публикацией.

## Остаточные риски

- privacy audit защищает форматы BULL, но не может сделать безопасным неизвестный
  произвольный файл;
- legacy CODE runner и chat `python_exec` не имеют полноценной OS sandbox;
- статистический вывод зависит от корректности hardware/runtime telemetry и
  достаточной выборки;
- live WAN, реальное multi-GPU оборудование и все сторонние Ollama/llama.cpp
  версии не могут быть покрыты offline regression.

## Проверка

- `Run-Tests.ps1`: 358/358;
- evidence regression: 9/9;
- финальные public audit, forced cp1251, manifest и ZIP проверки выполняются
  `Build-Release.ps1`.
