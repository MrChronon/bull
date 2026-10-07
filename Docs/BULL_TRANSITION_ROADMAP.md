# BULL Transition Roadmap

**Документ:** поэтапный план архитектурного перехода к BULL

**Версия документа:** 1.2

**Дата:** 2026-10-03

**Текущий продукт:** BULL v0.28.0.7

**Замороженная baseline:** v17.3.2

**Целевое имя:** BULL — Benchmarking & Usage of Local Language Models

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

Ближайшая продуктовая цель — помочь пользователю выбрать установленную модель
для своих задач по качеству, времени ответа, устойчивости и доступной памяти.
Основной сценарий: открыть BULL, выбрать локальное или сохранённое удалённое
подключение, выбрать задачи и модели, получить понятное сравнение и сохранить
отчёт. Терминальный интерфейс остаётся основным; существующие экспертные функции
сохраняются в дополнительных разделах.

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

| Код | Рабочее имя | Состояние и цель | Версия |
|---|---|---|---|
| T0 | **BULL Charter** | Завершён: продуктовые и архитектурные решения | Без релиза |
| T1 | **BULL Bridge** | Завершён: бренд и compatibility bridge | v0.22.0.0 |
| T2 | **BULL Core** | Контракты и adapters выпущены; извлечение production runtime продолжается поэтапно | v0.23.0.0 |
| T3 | **BULL Registry** | Завершён: data-only versioned packs | v0.24.0.0 |
| T4 | **BULL Evidence** | Завершён: provenance, private/share-safe artifacts и отчёты | v0.25.0.0 |
| T5.1 | **BULL RU Dialogue** | Выпущен candidate; promotion в stable требует независимых проверок | v0.26.0.0 |
| UX Gate | **BULL Simple Experience** | Выпущен: четыре основных действия, UserTests и рекомендации | v0.27.0.0; visual patch v0.27.0.1 |
| U1 | **BULL Clear Choice** | Выпущен: достоверная карточка выбора, строгие YAML-задачи и шаблоны | v0.28.0.4 |
| U2 | **BULL Quick Compare** | Короткий candidate pack и подтверждающий прогон | План v0.28.1.0 |
| T5.3 + T5.2 | **BULL Reliable Runs** | Восстановление и аппаратная сопоставимость; отдельные поставки | TBD после U2 |
| P1 | **BULL Anywhere** | Linux/macOS client после извлечения рабочего transport-пути | TBD; может опередить полную T5.2 |
| T6 | **BULL Field Lab** | Отложен: изоляция, расширение Agent, Long Context и Security | TBD |
| T7 | **BULL Open Range** | Отложен: external adapters и contributor SDK | TBD |
| T8 | **BULL One** | Стабильные API, formats и release process | Цель v1.0.0 |

Версии являются плановыми и могут сдвигаться. Нельзя объединять этапы только ради сохранения номера версии.

Коды T0–T8 сохраняют архитектурный смысл. U1/U2 — пользовательские этапы,
P1 — переносимость клиента. Reliable Runs объединяет приоритеты T5.3 и T5.2
в плане поставки, но не требует одного большого изменения runtime и метрик.
Названия Field Lab и Open Range больше не привязаны к уже занятой серии v0.27
и ближайшей v0.28.

### 3.1. Согласованный порядок поставки

1. **U1 Clear Choice:** корректность рекомендаций и YAML-проверок, затем первый
   экран результата, установка, прикладные шаблоны и экспорт для коллеги.
2. **U2 Quick Compare:** короткий pack после исправления рекомендаций; отдельный
   подтверждающий режим и понятные ограничения оценки.
3. **Reliable Runs:** полный fault-injection coverage T5.3, затем расширение
   T5.2 с проверкой условий измерения и наблюдаемого GPU placement.
4. **P1 Anywhere:** извлечение transport, Unix client и отдельные live gates.
   При подтверждённом спросе P1 может предшествовать полной аппаратной Matrix.

Минимум надёжности нужен уже в U1: конкурентное resume, сохранность готовых
records и понятная пауза после разрыва проверяются до расширения первого
пользовательского сценария. Полноценный resilience pack остаётся задачей T5.3.

### 3.2. U1 — BULL Clear Choice

**Статус:** выпущен в v0.28.0.4; текущая поддерживающая версия — v0.28.0.7. Поставки внутри этапа выполнены небольшими
независимыми изменениями.

**Результат для пользователя:** после сравнения видно, какие модели подходят
его приоритетам, почему они выбраны и каких измерений не хватает для вывода.

#### Карточка результата и правила выбора

- Первым экраном terminal и HTML становится одна и та же карточка
  Quality / Speed / Balance / Low memory; cases, provenance и подробная
  статистика открываются следующим уровнем.
- Равные показатели дают несколько равноценных кандидатов. Имя модели
  используется только для порядка отображения, не для назначения победителя.
- Средний Native score и консервативная оценка для выбора имеют разные поля
  и подписи. Нижняя граница CI не отображается как измеренный средний балл.
- Отдельно показываются наблюдаемое предпочтение, практически значимое
  различие и уверенность. Одно пересечение CI не является тестом разности.
  Если данных недостаточно, карточка сообщает об этом и предлагает повтор.
- Quality/task gate получает явную версию политики, порог и причину допуска
  или отказа. `fast_unqualified` означает высокую наблюдаемую скорость без
  допуска к рекомендации; `insufficient_data` не подменяется провалом модели.
- Пользовательские веса — предпочтения пользователя, а не новый benchmark
  score. Рекомендации не записываются обратно в `quality.*`.
- Время выполнения задачи, скорость генерации, cold/warm и неизвестное
  состояние показываются раздельно. Общая скорость не маскируется под warm.
  Используются уже измеренные данные; новые probes относятся к T5.2.
- Отсутствующая VRAM остаётся неизвестной; профиль Low memory не выдаёт
  рекомендацию без сопоставимых измерений памяти.
- Импорт tested profile выполняется после preview по явному выбору пользователя.

#### Проверяемые пользовательские задачи

- Уточнить версионированные контракты YAML-scorer: типы `true` и `1`, лишний
  текст после terminal JSON, значение по JSON path и полная схема — разные
  проверки. Балл по отдельным полям не должен означать «строгий JSON соблюдён».
- Изменения scorer поставляются отдельными PR с gold/negative fixtures и
  новой идентичностью поведения. Старые результаты не пересчитываются молча;
  доступный rescore создаёт копию с provenance.
- Добавить три самодостаточных синтетических шаблона: извлечение полей,
  структурированный ответ и деловой перевод. Каждый содержит все исходные
  данные, ясные автоматические проверки и `manual_review` для смысла/стиля.
- Заменить существующий расчётный пример, ожидающий число без исходных данных.
  Не выдавать substring-проверки за лингвистическую оценку: запрет `ты` не
  должен ошибочно штрафовать «Документы готовы».
- Формат `.txt` сохраняет отсутствие автоматического quality score. Число слов
  и отсутствие запрещённых строк сами по себе не доказывают качество перевода.
- Шаблоны исключаются из автоматического discovery до создания своей копии:
  использовать `.example.*` либо явно исключённый каталог. Простой перенос
  обычных `.yaml` в подпапку недостаточен при рекурсивном discovery.
- Подготовка и проверка задач доступны без backend. Ошибка одного файла не
  блокирует соседние. Парсер остаётся data-only, без regex/code/tags/aliases.

#### Установка, экспорт и доступ к экспериментам

- Сохранить главное меню из четырёх действий; улучшать существующий маршрут
  Compare, а не вводить параллельное меню с теми же сценариями.
- Quick start — три шага с отдельной секцией проверки SHA-256. Вход в релиз
  через одну ссылку latest; версия ZIP и checksum остаются однозначными.
  Дополнительный дубликат `latest`-архива не обязателен.
- Launcher/installer проверяет работоспособность и совместимость найденного
  Python, обрабатывает отсутствие Python, winget и прав записи. Сообщение
  объясняет следующий шаг без traceback. Shortcut необязателен для portable run.
- Offline UI доступен сразу после локальных проверок. Backend проверяется для
  выбранного подключения перед inference. Нет скрытого SSH, переключения
  сервера или обязательной локальной Ollama для удалённого подключения.
- При нуле моделей показать подключение/инструкции установки; при одной модели
  разрешить проверку задачи без сравнительного победителя. Загрузка моделей
  и установка backend требуют явного действия пользователя.
- «Отчёт для коллеги» создаёт отдельные HTML и share-safe JSON из проверенных
  данных, показывает место сохранения. Экспорт не содержит prompts, raw answers,
  endpoints, путей и секретов. Имена моделей остаются видимыми и требуют preview:
  share-safe не означает анонимность. HTML работает без JS/CDN.
- Для README/руководства использовать синтетический пример отчёта и короткий
  сценарий первого запуска. Документация и экранные тексты поддерживаются EN/RU.
- Потенциально опасное выполнение кода выключено по умолчанию; разрешения
  проверяются в обработчике действия, включая команды и отдельные launchers.
  Скрытие пункта меню само по себе не является ограничением доступа.
- Различать ограниченный интерпретатор текущей Agent-задачи и произвольное
  выполнение Python в legacy CODE/chat tools. Opt-in объясняет реальные
  полномочия; число подтверждений не заменяет OS-изоляцию. Расширение
  произвольных Agent-задач остаётся заблокировано до T6.0.

#### Критерии выхода и риски

- При равных метриках нет искусственного единственного победителя; причины
  gate и отсутствующих рекомендаций одинаковы в terminal и HTML.
- JSON type/terminal-boundary cases, ложное substring-срабатывание и отсутствие
  исходных данных покрыты явными fixture-проверками новых контрактов.
- Пользователь может создать задачу из шаблона, запустить её и сохранить отчёт
  без редактирования кода и перехода в экспертные меню.
- Нет обхода experimental opt-in через команду или отдельный entry point.
- Проверены отказ второго concurrent resume, повтор только незавершённой
  работы и сохранность готовых records после сбоя. Исправления orchestration
  отделены от scorer/template PR.
- На чистой Windows-системе измерены установка, первый startup и путь до
  результата. Полная startup-регрессия учитывается в этих затратах; её замена
  короткой проверкой требует отдельного решения и сохранения fail-closed
  проверки целостности. Release-regression не сокращается.
- Риск этапа — слишком широкий пакет. Порядок PR: fixtures и корректность,
  представление результата, шаблоны, installer/export, execution permissions;
  runtime reliability исправляется отдельным изменением.

### 3.3. U2 — BULL Quick Compare

**Статус:** запланирован, v0.28.1.0; зависит от U1.

- Новый data-only pack `bull_choose@1.0.0`, первоначально `candidate`:
  ориентир 5–8 коротких задач с собственными IDs, manifest/lock, gold fixtures
  и явно обозначенными проверяемыми навыками.
- `bull_chat_core@1.0.0` и его hashes сохраняются. Полный CHAT-набор и
  RU Dialogue доступны в дополнительных тестах; RU Dialogue не становится
  stable без независимых cross-model данных и второго review.
- «Быстрый обзор» даёт предварительные наблюдения, «Подтвердить результат» —
  заранее определённые дополнительные повторения с оценкой устойчивости.
  Один seed или smoke одной задачи не создаёт доказанного рейтинга.
- До запуска показываются модели, задачи, повторы, условия и ориентировочное
  время. Цель 8–15 минут проверяется на описанном оборудовании с 2–3 моделями,
  не обещается для любых размеров моделей, CPU и удалённых машин.
- Матрица сравнения фиксируется заранее. Остановка по времени или ошибка
  не должны превращать неполное, неравномерное покрытие в победу модели.
- Определить EN/RU coverage и versioned language variants; язык UI не выдаётся
  за язык тестирования. Scores разных вариантов не считаются эквивалентными
  без подтверждения сопоставимости.
- Использовать подходящие engine-owned scorers. Если нужен новый scorer,
  сначала отдельный PR и проверки, затем content PR с новым inference baseline.

**Критерии выхода:** pack validate/inspect до inference; unchanged CHAT Core
hashes; совместное отображение области оценки и ограничений; сравнение
короткого и подтверждающего прогона на объявленной матрице моделей/оборудования;
зафиксированы расхождения рекомендаций и длительности. Default переключается
на короткий pack только после подтверждения его пользы.

**Риск:** быстрый набор даёт ложное чувство полноты. Решение — показывать
измеренные навыки, объём выборки и статус предварительного результата,
сохраняя простой путь к собственным задачам и полному прогону.

### 3.4. Reliable Runs и Anywhere

**Reliable Runs:** после U2 закрывает полную T5.3, затем развивает T5.2.
Fault-injection и hardware measurement остаются отдельными проверяемыми
поставками. Неизвестное placement/датчики не превращаются в подтверждённые
результаты; mock-тесты дополняются live local/SSH/restart протоколами.

**P1 Anywhere:** сначала завершить извлечение рабочего backend/transport-пути
через существующий `BackendAdapter`, затем добавить Linux/macOS client.
Не создавать вторую копию монолита. Начальный scope — chat, compare,
локальные отчёты, UserTests, HTTP и pinned SSH к уже работающему backend.
GPU Lab, Windows installer и подготовка серверной ОС не входят в Unix parity.

Критерии P1: отдельные Unix CI jobs, опубликованная матрица реально проверенных
client/server OS, live local и remote smoke, отмена и resume, неизменные hashes
CHAT Core. Запрет недоверенного `ProxyCommand`, SSH pinning и отсутствие
обязательного облака сохраняются. Поддержка маркируется experimental до live
проверок; MLX и отличающиеся backends не маскируются под один runtime.

Риск P1 — разрастание платформенного scope. Linux/macOS не обещаются до
проверенного working path; при подтверждённом спросе P1 допускается перед
полной T5.2, но не вместо исправления достоверности рекомендаций U1.

### 3.5. Пользовательская приёмка и отложенные идеи

Внешняя telemetry не добавляется. На описанной чистой конфигурации вручную
фиксируются установка, startup, настройка и inference как отдельные интервалы.
Цель U1/U2: пользователь с двумя уже установленными моделями проходит путь до
карточки без USER_GUIDE и expert menu; ориентир usability-проверки — не менее
4 из 5 новых пользователей правильно объясняют рекомендацию и её ограничение.
Это критерий сценария, не доказательство спроса или общего качества моделей.

Отчёт для коллеги проходит privacy-проверку; сценарии 0/1/несколько моделей,
offline, разрыв сети и ошибочный YAML имеют понятный выход. Новые tests сами по
себе, GitHub stars и число packs не считаются продуктовым результатом.

За пределами ближайших этапов: GUI/Electron, hosted leaderboard, marketplace,
новый branding, внешняя telemetry, автоматическая загрузка моделей и расширение
агентов до OS-изоляции. Contributor SDK и внешние benchmark adapters остаются
в T7. Гипотезы о размере аудитории и превосходстве над конкурентами требуют
отдельных данных и не используются как обещания релиза.

### 3.6. Соответствие предложенным пакетам работ

| Пакет | Решение в roadmap |
|---|---|
| WP-1 First Comparison | U1 onboarding + U2 короткий pack; не перестройка готового Home |
| WP-2 Decision card | U1: исправления, видимый gate, равенство и происхождение метрик |
| WP-3 Installer | U1: надёжный preflight и portable run поверх существующей установки |
| WP-4 UserTests | U1: исправления контракта и три самодостаточных шаблона |
| WP-5 Colleague report | U1: законченный экспорт на основе существующих share-safe artifacts |
| WP-6 Unix | P1 Anywhere после извлечения production transport |
| WP-7 First-run safety | U1 permissions во всех entry points; T6.0 остаётся отдельным эпиком |
| WP-8 Local System Matrix | Подписи текущих измерений — U1; полная Matrix — T5.2 |
| Дополнение: Resilience | Минимум — U1; полный fault-injection pack — T5.3 / Reliable Runs |

---

## T0 — BULL Charter

**Статус:** завершён 2026-09-26.

### Назначение

Зафиксировать границы продукта до изменения кода. Этап устраняет неоднозначности имени, форматов и зон ответственности.

### Работы

- принять полное имя `BULL — Benchmarking & Usage of Local Language Models`;
- зафиксировать публичное описание `BULL Benchmark Lab`;
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
- ввести compatibility namespace без удаления исторических artefacts;
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

**Статус:** завершён в v0.25.0.0 (2026-09-28); prompts, scorers, recovery и
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

### UX Gate — Simple Experience, v0.27.0.0 / v0.27.0.1

**Статус:** реализован как обязательный пользовательский этап перед T5.2.

Simple Experience выпущен в v0.27.0.0; v0.27.0.1 — visual patch Red Release.
Перечень ниже описывает наличие функций, а не закрывает замечания U1 к
точности рекомендаций, трактовке YAML-критериев и пути экспорта.

- [x] четыре однозначных действия на главной;
- [x] expert/server/Agent/GPU функции раскрываются постепенно;
- [x] краткий результат и выбор модели доступны в терминале;
- [x] профили Quality/Speed/Balance/Low memory и пользовательские веса;
- [x] относительная quality/speed карта в терминале и HTML;
- [x] `.txt` user task без фиктивного score;
- [x] безопасный `.yaml` contract с документированными criteria;
- [x] raw и share-safe export явно разделены;
- [x] встроенные prompts/scorers/runtime/recovery не менялись.

### T5.2 — BULL Local System Matrix, version TBD

**Статус:** запланирован в Reliable Runs после U1/U2. Уточнение подписей
существующих timing-метрик выполняется в U1; новые измерения и hardware matrix
остаются в этом подэтапе.

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

**Статус:** минимум сохранности/конкурентного resume — приёмка U1;
полный pack и fault-injection coverage — Reliable Runs после U2.

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
- одновременное продолжение одного checkpoint отклоняется; stale ownership
  после сбоя обрабатывается явно, без потери завершённых records;
- transport retry не становится model recovery;
- диагностика не раскрывает endpoint, username или home path.

### Ограничение этапа

Подэтапы T5.1–T5.3 выпускаются отдельно. Нельзя одновременно менять content scorer RU Dialogue и recovery runtime.

---

## T6 — BULL Field Lab

**Статус:** отложен; версия TBD. U1 вводит permissions для существующих
возможностей, но не заменяет Isolated Executor Foundation.

### Назначение

Расширить оценку на агентность, длинный контекст и безопасность после стабилизации core и artifact model.

### T6.0 — Isolated Executor Foundation

Текущая фиксированная Agent-задача уже использует отдельный trusted verifier
с ограниченным интерпретатором. T6.0 расширяет границу на произвольные build
tasks и legacy executable CODE/chat tools; отдельного процесса и `-I`
недостаточно для заявления об OS sandbox.

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

**Статус:** отложен; версия TBD. Ближайшая v0.28 отведена Clear Choice,
а не SDK. P1 Anywhere использует внутренние backend contracts и не требует
предварительного выпуска contributor SDK.

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

- исторические артефакты открываются read-only;
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

Направление U1 → U2 → Reliable Runs → Anywhere согласовано 3 октября 2026.
Это приоритетный план, а не отметка о выполнении или публикации будущих релизов.

- после T0 — подтверждение имени, subtitle и brand direction;
- после T1 — подтверждение публичного вида BULL;
- после T3 — утверждение authoring workflow для benchmark packs;
- перед T5 — утверждение состава флагманских packs;
- перед назначением `bull_choose` default — review состава, EN/RU coverage
  и результатов короткого/подтверждающего прогона;
- перед T7 — утверждение лицензии и contribution policy;
- перед T8 — отдельное разрешение на публичный релиз v1.0.0.

## 7. Определение завершённого перехода

Переход к BULL завершён, когда:

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
