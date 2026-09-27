# BULL Product Charter

**Статус:** Accepted for T0  
**Версия:** 1.0  
**Дата:** 2026-09-26  
**Владелец продукта:** владелец публичного репозитория проекта  
**Исходный продукт:** Local LLM v0.21.0.0  
**Целевой продукт:** BULL — Benchmarking & Usage of Local LLMs

## 1. Миссия

BULL — локальная лаборатория для воспроизводимой оценки языковых моделей, inference-конфигураций, оборудования и прикладных LLM-систем.

BULL отвечает не на абстрактный вопрос «какая модель лучше», а на проверяемые вопросы:

- какая конфигурация подходит для конкретного класса задач;
- насколько устойчив результат между seeds, prompts и порядками запуска;
- как влияют quantization, context, sampling, backend и hardware;
- что относится к native quality модели, а что создано recovery или другим поведением клиента;
- можно ли воспроизвести результат по сохранённой provenance;
- насколько надёжно решение переживает реальные сбои.

## 2. Публичная идентичность

- **Короткое имя:** BULL.
- **Расшифровка:** Benchmarking & Usage of Local LLMs.
- **Обязательное пояснение при первом упоминании:** Local LLM Benchmark Lab.
- **Рекомендуемая полная форма:** BULL — Local LLM Benchmark Lab.
- **Python namespace:** `bull_llm`.
- **Запрещённый distribution name:** `bull`.
- **Рабочий будущий repository/package qualifier:** `bull-local-llm` / `bull-llm`, только после проверки доступности.

Имя BULL без qualifier допускается в логотипе и внутри уже однозначного интерфейса. В package registries, schemas, поисковых metadata и первом упоминании оно не используется отдельно из-за существующих одноимённых проектов.

## 3. Целевые пользователи

### Основные

- пользователь локальных LLM, выбирающий модель и quantization под своё оборудование;
- разработчик, проверяющий модель перед включением в приложение;
- исследователь, которому нужны воспроизводимые локальные результаты;
- владелец нескольких GPU или удалённого inference-сервера;
- автор собственного benchmark pack.

### Неосновные на первом этапе

- публичный облачный leaderboard;
- массовый SaaS;
- обучение и fine-tuning моделей;
- управление парком production-серверов;
- автоматическая публикация пользовательских результатов.

## 4. Продуктовые поверхности

### BULL Benchmark Lab

Владеет:

- benchmark catalog и packs;
- run plans, balanced order, seeds и repeats;
- scoring, verification и statistics;
- checkpoint/resume;
- benchmark reports;
- tested profile artifacts.

Не имеет права незаметно менять настройки рабочего Client.

### BULL Client

Владеет:

- рабочими чатами;
- FAST, THINK и ULTIMATE workflows;
- пользовательскими сессиями;
- явным импортом выбранного tested profile;
- экспортом по явному действию пользователя.

Не является источником benchmark score.

### BULL Agent Lab

Владеет:

- agent tasks;
- tool trajectories;
- изолированными verifiers;
- вмешательствами и agent-specific telemetry.

Agent metrics не смешиваются с CHAT-рейтингом.

### BULL GPU Lab

Владеет:

- hardware selection;
- performance workloads;
- resource telemetry;
- single/multi-GPU comparisons.

GPU Lab не объявляет performance workload тестом качества модели.

## 5. Неизменяемые принципы

1. Offline-first и local-first.
2. Никакой внешней telemetry по умолчанию.
3. Native model quality и final system quality разделены.
4. Recovery не повышает native score.
5. Нет одного универсального рейтинга.
6. Result без provenance не считается воспроизводимым.
7. Старые artifacts не перезаписываются.
8. Prompt, scorer и runtime versioned независимо.
9. Недоступный sensor означает `null`, а не ноль.
10. Публичный release не содержит пользовательские подключения и секреты.
11. Расширение выполняется benchmark packs, а не ростом одного монолитного файла.
12. Любое утверждение о превосходстве ограничено условиями конкретного прогона.

## 6. Флагманские направления

### BULL RU Dialogue

Прикладная русскоязычная многоходовая надёжность: corrections, negation, causality, tone, groundedness, instruction retention и согласованность prose/structured output.

### BULL Local System Matrix

Связь quality с quantization, backend, context, sampling, GPU, load state и resource cost.

### BULL Resilience

Корректность checkpoint/resume и системы при disconnect, restart, incomplete stream и повторном resume.

Следующие направления после стабилизации: Agent, Long Context, Security и Robustness Surface.

## 7. Что сохраняется из Local LLM

- CHAT Core и его текущие prompts/scorers;
- Ollama и llama.cpp adapters;
- local, AllInOne и pinned SSH workflows;
- tested profiles;
- custom prompt versioning;
- native/assisted attribution;
- balanced execution order;
- seeds, SD, min/max, worst seed, rank stability и uncertainty;
- checkpoint/resume;
- offline HTML;
- Agent Benchmark MVP;
- experimental GPU Lab;
- security и public release gates.

## 8. Что не делаем

- big-bang rewrite;
- скрытую автоматическую миграцию;
- общий score «лучшая модель»;
- обязательный LLM-as-a-judge;
- обязательное облако;
- прямую публикацию Ollama/llama.cpp в Интернет;
- автоматическую отправку результатов на leaderboard;
- копирование внешних datasets без license/provenance review;
- одновременное изменение prompt, scorer и runtime.

## 9. Критерии успеха перехода

Переход успешен, когда:

- BULL является единым публичным именем;
- legacy artifacts открываются read-only;
- новая задача добавляется как versioned pack;
- engine отделён от UI и transport;
- native, assisted, runtime, recovery и security metrics невозможно перепутать;
- как минимум три собственных pack имеют gold tests и baseline;
- public release проходит privacy/security gates;
- новый пользователь выполняет первый benchmark по документации;
- результат воспроизводится по сохранённым fingerprints и hashes.

## 10. Решения T0

Приняты:

- [ADR-0001: Product Boundaries](ADR/0001-product-boundaries.md)
- [ADR-0002: Legacy Schema Compatibility](ADR/0002-legacy-schema-compatibility.md)
- [ADR-0003: Metric Taxonomy](ADR/0003-metric-taxonomy.md)
- [ADR-0004: Benchmark Pack Registry](ADR/0004-benchmark-pack-registry.md)
- [Naming Research](BULL_NAMING_RESEARCH.md)
- [Brand Guide](BULL_BRAND_GUIDE.md)
- [Compatibility Matrix](BULL_COMPATIBILITY_MATRIX.md)
- [Target Architecture](BULL_TARGET_ARCHITECTURE.md)
- [Transition Roadmap](BULL_TRANSITION_ROADMAP.md)

## 11. Gate перед T1

T0 считается завершённым с архитектурной точки зрения. До публичного запуска BULL Bridge владелец продукта должен подтвердить:

1. использование бренда только с qualifier `Local LLM Benchmark Lab` в первом упоминании;
2. принятие риска существующего Text-to-SQL benchmark BULL;
3. проведение отдельной trademark-проверки до публичного коммерческого релиза;
4. сохранение текущего GitHub repository name до подготовленной миграции;
5. отсутствие изменения benchmark content в branding release.
