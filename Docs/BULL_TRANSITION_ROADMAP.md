# BULL Transition Roadmap

**Документ:** поэтапный план архитектурного перехода Local LLM → BULL

**Версия документа:** 1.1

**Дата:** 2026-09-28

**Текущий продукт:** BULL v0.27.0.0

**Замороженная baseline:** v17.3.2

**Целевое имя:** BULL — Benchmarking & Usage of Local LLMs

**Целевой стабильный релиз:** BULL v1.0.0

## 1. Назначение дорожной карты

Эта дорожная карта разбивает переход к BULL на небольшие проверяемые этапы. Она не разрешает big-bang rewrite и не предполагает одновременного изменения benchmark prompts, scorers и runtime pipeline.

BULL должен стать локальной лабораторией, которая раздельно измеряет:

- native quality модели;
- final system quality после разрешённой помощи клиента;
- соблюдение формата и task contract;
- скорость и использование ресурсов;
- надёжность runtime и recovery;
- работу инструментов и агентов;
- безопасность и приватность.

Переход считается законченным только после стабилизации публичных интерфейсов, форматов результатов и compatibility layer. До этого версии BULL остаются `0.x`.

## 2. Общие ограничения перехода

На всех этапах действуют следующие правила:

1. Сохранять поведение тестами до извлечения модулей.
2. Не менять prompt, scorer и runtime pipeline в одном изменении.
3. Не объединять native quality с recovery или assisted quality.
4. Не перезаписывать старые benchmark artifacts и checkpoints.
5. Новая миграция создаёт копию и сохраняет provenance исходника.
6. Не добавлять обязательную облачную зависимость или внешнюю telemetry.
7. Не публиковать Chats, Runtime, Benchmarks, Exports, ключи и локальные секреты.
8. После каждого программного изменения запускать `Run-Tests.ps1`.
9. Каждый релиз проверять через public release gate, manifest, cp1251 startup и ZIP audit.
10. Делать небольшие проверяемые commits, соответствующие одному архитектурному шагу.

## 3. Карта этапов

| Код | Рабочее имя | Цель | Плановая версия |
|---|---|---|---|
| T0 | **BULL Charter** | Зафиксировать продуктовые и архитектурные решения | Документация, без релиза |
| T1 | **BULL Bridge** | Ввести новый бренд и compatibility bridge без изменения benchmark-поведения | v0.22.0.0 |
| T2 | **BULL Core** | Извлечь стабильное ядро и публичные контракты | v0.23.0.0 |
| T3 | **BULL Registry** | Ввести benchmark packs и независимый registry | v0.24.0.0 |
| T4 | **BULL Evidence** | Унифицировать provenance, метрики, artifacts и отчётность | v0.25.0.0 |
| T5 | **BULL Flagships** | Выпустить собственные флагманские benchmark packs | v0.26.x |
| T6 | **BULL Field Lab** | Расширить agent, long-context и security evaluation | v0.27.x |
| T7 | **BULL Open Range** | Открыть adapters и contributor SDK | v0.28.0.0 |
| T8 | **BULL One** | Стабилизировать API и выпустить BULL v1.0.0 | v1.0.0 |

Версии являются плановыми и могут сдвигаться. Нельзя объединять этапы только ради сохранения номера версии.

---

## T0 — BULL Charter

**Статус:** завершён 2026-09-26.

### Назначение

Зафиксировать границы продукта до изменения кода. Этап устраняет неоднозначности имени, форматов и зон ответственности.

### Работы

- принять полное имя `BULL — Benchmarking & Usage of Local LLMs`;
- зафиксировать публичное описание `Local LLM Benchmark Lab`;
- выполнить предварительную проверку товарного знака, имени GitHub, домена и package names;
- утвердить brand brief и требования к логотипу;
- принять ADR по compatibility policy;
- принять ADR по metric taxonomy;
- принять ADR по benchmark registry;
- определить naming map старых и новых компонентов;
- определить границу между BULL Benchmark Lab и рабочим Client;
- зафиксировать, какие старые schemas обязаны читаться.

### Результаты

- [Product Charter](BULL_PRODUCT_CHARTER.md);
- [Architecture Decision Records](ADR/README.md);
- [brand guide](BULL_BRAND_GUIDE.md);
- [naming research](BULL_NAMING_RESEARCH.md);
- [compatibility matrix](BULL_COMPATIBILITY_MATRIX.md);
- [целевая структура и границы модулей](BULL_TARGET_ARCHITECTURE.md);
- список поддерживаемых legacy schemas в compatibility matrix.

### Не входит

- переименование файлов и модулей;
- изменение UI;
- изменение prompts, scorers или runtime;
- миграция artifacts.

### Критерии выхода

- имя и subtitle утверждены;
- отсутствует неразрешённый критический naming conflict;
- для каждого существующего компонента определено целевое место;
- правила совместимости однозначны;
- дальнейшие этапы не требуют скрытых продуктовых решений.

---

## T1 — BULL Bridge

**Статус:** завершён 2026-09-26, релиз v0.22.0.0.

### Назначение

Представить продукт как BULL, сохранив существующее внутреннее поведение и возможность открыть старые результаты.

### Работы

- добавить новый display name, version banner и branding assets;
- подготовить финальный SVG, icon-only, wordmark, monochромный, light и dark variants;
- добавить Windows `.ico`, favicon и GitHub social preview;
- ввести compatibility namespace без удаления `local_llm_shared`;
- добавить read-only compatibility readers текущих schemas;
- сохранить старые launchers как aliases с понятным уведомлением;
- обновить README, USER_GUIDE, AI_CONTEXT, SECURITY и release notes;
- добавить migration guide для пользователей v0.21.0.0;
- сохранить существующее имя GitHub-репозитория до отдельного подтверждённого переименования.

### Запрещено совмещать

- изменения branding с изменением benchmark prompt;
- изменения branding с изменением scorer;
- переименование модулей с рефакторингом runtime;
- автоматическое изменение пользовательских checkpoints.

### Проверки

- startup в UTF-8 и cp1251;
- старые launchers запускают новый entrypoint или показывают migration notice;
- старые artifacts открываются read-only;
- public release не содержит private assets или локальные пути;
- иконка читается в размерах 16, 32 и 64 px;
- UI сохраняет достаточный контраст.

### Критерии выхода

- пользователь видит имя BULL во всех публичных поверхностях;
- текущие benchmark prompts и scores не изменились;
- все regression tests проходят;
- старые JSON и checkpoints не были перезаписаны;
- новый release проходит public audit и ZIP verification.

---

## T2 — BULL Core

**Статус:** завершён 2026-09-26, релиз v0.23.0.0. Production runtime оставлен
на проверенном пути; новые контракты являются швом для поэтапной миграции T3+.

### Назначение

Создать минимальное стабильное ядро, от которого не зависят UI, конкретные benchmarks и transport implementation.

### Целевые модули

```text
bull_llm.core
bull_llm.runtime
bull_llm.evaluation
bull_llm.telemetry
bull_llm.reports
```

### Публичные контракты

- `BackendAdapter`;
- `BenchmarkPack`;
- `Runner`;
- `Scorer`;
- `Verifier`;
- `TelemetryProvider`;
- `ArtifactStore`;
- `ReportRenderer`;
- `SchemaMigration`.

### Работы

- описать typed request/response contracts;
- отделить model discovery от UI;
- отделить inference events от terminal rendering;
- отделить scoring от runtime transport;
- отделить atomic artifact storage от benchmark orchestration;
- ввести capability discovery для backend и telemetry;
- добавить contract tests для Ollama и llama.cpp adapters;
- сохранить текущие runtime options и recovery semantics.

### Стратегия извлечения

1. Зафиксировать поведение golden tests.
2. Ввести интерфейс вокруг существующей реализации.
3. Перенести одну ответственность.
4. Проверить parity.
5. Только затем удалить старый внутренний путь.

### Критерии выхода

- UI не содержит scorer logic;
- scorers не вызывают transport;
- reports не пересчитывают результаты;
- adapters проходят единый contract test suite;
- существующие CHAT-прогоны совпадают с v0.21.0.0;
- runtime fingerprints не изменились без явной schema revision.

---

## T3 — BULL Registry

**Статус:** завершён в v0.24.0.0 (2026-09-27); все release gates являются обязательной частью сборки.

### Назначение

Сделать benchmark расширяемым через независимые versioned packs, не требующие изменения центрального клиента.

### Структура pack

Каждый pack содержит:

- manifest;
- cases или versioned generator;
- runner type;
- scorer reference;
- verifier reference при необходимости;
- category taxonomy;
- license и provenance;
- gold tests;
- documentation;
- minimum engine version.

### Работы

- реализовать manifest schema;
- реализовать pack discovery и validation;
- добавить canonical JSON compilation и SHA-256;
- перенести текущий Chat Core без изменения prompts;
- ввести состояния `experimental`, `candidate`, `stable`, `deprecated`, `retired`;
- ввести public development packs и user-owned private packs;
- добавить команды list, validate и inspect;
- запретить выполнение произвольного Python из недоверенного pack;
- подготовить authoring guide.

### Проверки

- duplicate pack ID;
- incompatible engine version;
- неизвестный runner или scorer;
- повреждённый hash;
- отсутствие license metadata;
- path traversal в pack;
- несовместимая case version;
- детерминированность versioned generator.

### Критерии выхода

- новая безопасная задача добавляется без редактирования central client;
- Chat Core работает через registry;
- prompt snapshots совпадают с legacy implementation;
- pack validation выполняется до inference;
- manifest и compiled pack имеют стабильные hashes.

---

## T4 — BULL Evidence

**Статус:** завершён в v0.26.0.0 (2026-09-28); prompts, scorers, recovery и
runtime inference pipeline не изменялись.

### Назначение

Создать единый доказательный формат результата и исключить смешивание разных типов качества.

### Пространства метрик

```text
quality.native
quality.assisted
contract
runtime
resources
recovery
reliability
security
human
```

### Работы

- ввести `bull-benchmark-record`;
- ввести `bull-benchmark-summary`;
- ввести immutable provenance block;
- разделить launch и effective runtime fingerprints;
- сохранять prompt, pack, scorer и verifier hashes;
- ввести явные private и share-safe artifacts;
- добавить schema migration как создание новой копии;
- обновить terminal и HTML reports;
- добавить графики с confidence intervals;
- добавить context curves, latency distributions и category heatmaps;
- сохранить offline-only HTML без CDN;
- добавить privacy audit для share-safe export.

### Статистические правила

- sample SD доступен только при `n >= 2`;
- confidence intervals показываются только при достаточной выборке;
- сравнение содержит worst seed, min/max и rank stability;
- warm state определяется по фактическому load duration;
- balanced order и фактический execution order сохраняются;
- Pareto учитывает неопределённость;
- один run не создаёт универсального вывода о превосходстве модели.

### Критерии выхода

- native score невозможно спутать с assisted score;
- recovery не изменяет native score;
- старые artifacts читаются через compatibility layer;
- migration никогда не перезаписывает source;
- share-safe report не содержит prompts, raw answers, endpoints и домашние пути;
- terminal и HTML используют одни и те же summary data.

---

## T5 — BULL Flagships

### Назначение

Выпустить три собственных направления, которые определяют уникальность BULL.

### T5.1 — BULL RU Dialogue, v0.26.0.0

**Статус:** завершён 2 октября 2026 года как candidate pack
`bull_ru_dialogue@1.0.0`. Pack намеренно не помечен `stable` до независимого
cross-model прогона и второго человеческого review.

Категории:

- изменение подтверждённого состояния;
- замена устаревших данных;
- неподтверждённые утверждения assistant;
- отрицания и ограничения доказательности;
- причинная осторожность;
- временные, числовые и форматные ограничения;
- современный деловой русский;
- согласованность prose и JSON;
- multi-turn instruction retention;
- embedded instruction resistance.

Критерии выхода:

- [x] public development set;
- [x] 10 parameterized variants в шести семействах;
- [x] scorer gold set;
- [x] adversarial cases;
- [x] ручной audit всех synthetic critical-failure fixtures;
- [x] отдельные `semantic_score` и `structural_score`;
- [x] critical failures содержат evidence/reason и требуют manual review;
- [x] CHAT Core, recovery и inference runtime не изменены.

### UX Gate — Simple Experience, v0.27.0.0

**Статус:** реализован как обязательный пользовательский этап перед T5.2.

- [x] четыре однозначных действия на главной;
- [x] expert/server/Agent/GPU функции раскрываются постепенно;
- [x] краткий результат и выбор модели доступны в терминале;
- [x] профили Quality/Speed/Balance/Low memory и пользовательские веса;
- [x] относительная quality/speed карта в терминале и HTML;
- [x] `.txt` user task без фиктивного score;
- [x] безопасный `.yaml` contract с документированными criteria;
- [x] raw и share-safe export явно разделены;
- [x] встроенные prompts/scorers/runtime/recovery не менялись.

### T5.2 — BULL Local System Matrix, version TBD after v0.27

**Статус:** отложен. Перед расширением научной матрицы выпущен пользовательский
этап v0.27 Simple Experience.

Измерения:

- model, quantization и backend;
- cold/warm load;
- TTFT;
- prompt и output tokens/s;
- P50/P95 latency;
- VRAM, RAM, utilization и temperature;
- single и multi-GPU;
- context и sampling provenance;
- optional power и energy;
- native quality gate.

Критерии выхода:

- быстрый, но не прошедший quality gate профиль не отмечается как рекомендованный;
- фактическое GPU placement отличается от запрошенного и сохраняется отдельно;
- hardware comparison содержит полный fingerprint;
- performance overhead harness измерен и документирован.

### T5.3 — BULL Resilience, version TBD

Сценарии:

- backend offline;
- disconnect до первого token;
- mid-stream disconnect;
- restart backend;
- restart SSH tunnel;
- restart клиента;
- повторный resume;
- damaged checkpoint;
- incomplete JSON stream;
- concurrent resume.

Критерии выхода:

- завершённые records не повторяются;
- незавершённый run повторяется с начала;
- duplicate artifacts отсутствуют;
- checkpoint пишется атомарно;
- transport retry не становится model recovery;
- диагностика не раскрывает endpoint, username или home path.

### Ограничение этапа

Подэтапы T5.1–T5.3 выпускаются отдельно. Нельзя одновременно менять content scorer RU Dialogue и recovery runtime.

---

## T6 — BULL Field Lab

### Назначение

Расширить оценку на агентность, длинный контекст и безопасность после стабилизации core и artifact model.

### T6.0 — Isolated Executor Foundation

До расширения Agent Benchmark необходимо:

- вынести verifier в отдельный процесс;
- ограничить workspace;
- запретить произвольный доступ к сети;
- ограничить CPU, memory и execution time;
- валидировать пути;
- разделить trusted fixture code и model-generated changes;
- журналировать события без tool payload secrets.

### T6.1 — BULL Agent

Минимум 10 независимых задач:

- исправление кода;
- исправление тестов;
- работа с несколькими файлами;
- structured extraction;
- выбор инструмента;
- неправильный аргумент tool call;
- tool timeout;
- восстановление после tool error;
- сохранение состояния;
- завершение task contract.

### T6.2 — BULL Long Context

Уровни запуска:

```text
4K → 8K → 16K → 32K → далее при реальной поддержке backend
```

Оценивается кривая деградации для revision history, project state, contradictory documents, distractors и prompt injection.

### T6.3 — BULL Security

Категории:

- prompt injection;
- embedded instructions;
- secret exfiltration;
- path traversal;
- tool permission violations;
- unsafe generated actions;
- excessive refusal;
- system prompt leakage;
- private data in share-safe reports.

### Критерии выхода

- произвольный model-generated Python не исполняется в основном процессе;
- Agent результаты не смешиваются с CHAT-рейтингом;
- long-context результат представлен кривой, а не одним maximum-context числом;
- security metrics не входят в общий quality score;
- все fixtures имеют versioned verifier и deterministic reset.

---

## T7 — BULL Open Range

### Назначение

Сделать BULL расширяемой публичной платформой без включения чужих datasets в основной bundle.

### Работы

- adapter для `lm-evaluation-harness`;
- adapter для Inspect AI;
- contributor SDK;
- pack template;
- schema documentation;
- compatibility test kit;
- license/provenance checker;
- optional blind local A/B evaluation;
- contributor review checklist;
- stable plugin discovery без выполнения неизвестного кода по умолчанию.

### Правила внешних datasets

- dataset устанавливается отдельно;
- license фиксируется явно;
- version и checksum обязательны;
- источник и citation включаются в metadata;
- BULL не объявляет чужой benchmark собственным;
- результаты разных dataset revisions не смешиваются;
- hidden или restricted data не попадают в публичный ZIP.

### Критерии выхода

- внешний pack может быть установлен и удалён независимо;
- несовместимый adapter блокируется до inference;
- contribution можно проверить без доступа к частной инфраструктуре автора;
- основной BULL остаётся offline-first;
- public package не содержит автоматически скачанные datasets.

---

## T8 — BULL One

### Назначение

Стабилизировать публичные контракты и выпустить BULL v1.0.0.

### Обязательные условия

- стабильные public interfaces;
- документированная deprecation policy;
- schema migration guide;
- минимум три стабильных собственных benchmark pack;
- проверенный isolated executor;
- public license;
- security audit;
- privacy audit;
- воспроизводимая release pipeline;
- чистый публичный repository;
- live smoke local Ollama;
- live smoke remote pinned SSH;
- fault-injection acceptance suite;
- полная пользовательская и AI-документация.

### Совместимость v1

- legacy Local LLM artifacts открываются read-only;
- compatibility aliases могут быть deprecated, но не удаляются без отдельной major policy;
- schemas v1 замораживаются;
- breaking changes после v1 требуют major version;
- benchmark pack version остаётся независимой от версии приложения.

### Критерии выхода

- все обязательные gates проходят;
- отсутствуют unresolved critical security findings;
- нет скрытых подключений и external telemetry;
- пользователь может установить BULL, настроить локальный backend и выполнить первый benchmark по документации;
- пользователь может настроить SSH без редактирования кода;
- результат воспроизводим по сохранённой provenance;
- название, логотип и документация единообразны во всех публичных поверхностях.

---

## 4. Сквозные test gates

Каждый программный этап обязан проходить:

1. Python compile.
2. Unit tests.
3. Existing regression suite.
4. Golden prompt snapshots.
5. Scorer gold tests, если scorer входил в изменение.
6. Runtime contract tests, если менялся transport или backend adapter.
7. Checkpoint and resume tests, если менялся orchestration.
8. Security tests.
9. Forced cp1251 startup.
10. PowerShell parse.
11. Public source audit.
12. Staged release audit.
13. Manifest verification.
14. ZIP content и SHA-256 verification.

Для live hardware и network tests используется отдельный acceptance checklist. Недоступность конкретного оборудования не должна маскироваться успешными mocked tests.

## 5. Правила работы с benchmark content

Для каждого изменения применяется один из классов:

- `PROMPT_CHANGE`;
- `SCORER_CHANGE`;
- `RUNTIME_CHANGE`;
- `REPORT_ONLY`;
- `SCHEMA_COMPATIBILITY`;
- `BRANDING_ONLY`.

Один pull request не должен объединять `PROMPT_CHANGE`, `SCORER_CHANGE` и `RUNTIME_CHANGE`.

При `PROMPT_CHANGE` нужен новый inference baseline.  
При совместимом `SCORER_CHANGE` допускается offline rescore.  
При `RUNTIME_CHANGE` нужен повторный inference, если изменились фактически отправленные options или streaming semantics.

## 6. Контрольные точки владельца продукта

Перед началом следующих этапов требуется решение владельца:

- после T0 — подтверждение имени, subtitle и brand direction;
- после T1 — подтверждение публичного вида BULL;
- после T3 — утверждение authoring workflow для benchmark packs;
- перед T5 — утверждение состава флагманских packs;
- перед T7 — утверждение лицензии и contribution policy;
- перед T8 — отдельное разрешение на публичный релиз v1.0.0.

## 7. Определение завершённого перехода

Переход Local LLM → BULL завершён, когда:

- BULL является основным публичным именем;
- существующие пользователи не теряют результаты и profiles;
- benchmark engine отделён от UI и transport;
- benchmarks распространяются как versioned packs;
- native, assisted, runtime и recovery metrics разделены;
- новые RU, local-system и resilience packs стабильны;
- Agent Benchmark использует изолированный verifier;
- external adapters не нарушают offline-first модель;
- public release не содержит приватных данных;
- BULL v1.0.0 проходит все regression, security и release gates.

До выполнения этих условий проект остаётся в переходной серии BULL `0.x`.
