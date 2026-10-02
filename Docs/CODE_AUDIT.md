# BULL — аудит кода, benchmark, безопасности, производительности и UX

## Текущий аудит v0.27.0.0

Текущий аудит: **`AUDIT_v0.27.0.0.md`**. Релиз упрощает терминальную навигацию,
добавляет безопасные пользовательские `.txt/.yaml` задачи и прозрачную
decision-support сводку поверх уже рассчитанных метрик. Встроенные prompts,
scorers, recovery и runtime inference pipeline не менялись.

YAML loader ограничен по размеру и схеме, не исполняет tags, aliases, regex или
код. `.txt` не получает фиктивного quality score. Профили выбора не изменяют
сохранённые scores и действуют только внутри сопоставимого прогона. HTML и
share-safe evidence исключают prompts/answers; raw JSON помечается приватным.
Полный технический аудит v0.21 сохранён ниже как историческая база.

## Историческая база аудита v0.21.0.0

Актуальные находки, исправления, замер производительности и высокий остаточный
риск legacy CODE executor: **`AUDIT_v0.21.0.0.md`**. Ниже сохранена история прошлых
этапов; её номера тестов и утверждения о неизменности runtime относятся к тем этапам.

## Agent Benchmark, 19 сентября 2026

Добавлен независимый MVP с ограниченным task harness. Regression включает golden
repair, ложный SUCCESS, malformed/unknown tools, выход за границы workspace,
запрет импорта/атрибутов/рекурсии/огромных значений, loop, обрыв/ручной retry,
correction, ручную правку файла, чистый rerun, compaction, effective context mismatch,
агрегирование и приватность JSON/HTML/CSV.

Исторические CHAT/CODE prompts, scorers и runtime pipeline сохранены. Изменения
legacy core ограничены маршрутом нового UI и идентичностью startup cache.
Фактические token counts и оценки не смешиваются; неизвестные resource metrics — null.

Ограничения: одна synthetic task не представляет реальные большие проекты;
AST subset не эквивалентен полному Python; build-tools требуют контейнера/VM.
Resource peaks сэмплированные, manual edits наблюдаются на границах шагов.
После crash поддержан чистый attempt, не восстановление середины task.
Автоматический tuning и статистика серии относятся к следующему этапу.

Далее — исторический аудит унаследованного функционала.

**Версия:** v0.21.0.0  
**Дата:** 30 августа 2026  
**Объект:** `local_llm_client_v0.21.0.0.py`, RU_LANGUAGE_STRESS, checkpoint/resume, безопасность, производительность и UI

## Аудит startup/SSH navigation v0.21.0.0

Startup выполнял `connect_active_backend()` и `installed_models()` до показа главного меню. При выключенной локальной Ollama пользователь попадал во вложенные connection/backend/remote menus, а успешный setup предлагал перезапуск и возвращал на предыдущий уровень. Ошибка удалённого llama.cpp дополнительно могла незаметно переключить процесс на Ollama.

Исправление переводит оболочку в offline-first режим. Главное меню, конфигурация и сохранённые отчёты не требуют inference API. Выбор connection возвращает единый сигнал немедленного reconnect. Чат и новый стандартный benchmark используют runtime guard, который проверяет только выбранный backend и при ошибке возвращает пользователя домой без изменения конфигурации. Покрытие: 210/210 offline regression; prompts, scorers и benchmark execution contracts не изменены.

## Аудит direct Internet v0.21.0.0

Клиентская SSH-туннелизация уже поддерживала внешний host/port, но основной installer не передавал `Route` и `EndpointPort` серверному этапу, а UI прятал direct SSH среди нескольких legacy-профилей. В результате безопасный сценарий с белым IP был технически возможен, но требовал ручной сборки конфигурации и допускал ошибочное открытие inference API.

Исправление добавляет отдельный WAN-flow и fail-closed readiness check. Внешняя поверхность ограничена одним TCP port-forward на OpenSSH `22`; Ollama/llama.cpp остаются loopback-only. UPnP, DMZ и хранение router credentials запрещены. Server проверяет automatic `sshd`, key-only policy, firewall и listeners до рекомендации открыть NAT. SSH keepalive быстрее обнаруживает разрыв, а существующий checkpoint/resume сохраняет готовые runs.

Проверка реального узла в локальной сети подтвердила доступность OpenSSH и loopback bind Ollama. При этом до повторной установки key-only policy сервер объявлял password/keyboard-interactive методы; поэтому router rule нельзя активировать до успешного readiness check. Это operational blocker, а не дефект benchmark pipeline.

## Аудит v0.21.0.0: результаты текущей ревизии

### Ollama sampling correctness

Обнаружено, что benchmark resolver применял общий `sampling_preset`, а нижний `/api/chat` serializer безусловно добавлял пять sampling-полей. Поэтому разные значения в Modelfile фактически не участвовали в эксперименте. Поле `profile_ctx` одновременно читалось из локального `model_profiles.json`, хотя `/api/show` сообщал другой `num_ctx`.

Исправление разделяет `resolved configuration`, точный `sent runtime options` и parameter provenance. Режим `model_profile` получает digest/version-bound snapshot через `/api/show`, оставляет sampling options отсутствующими и честно маркирует неизвестные backend defaults. `per_model` передаёт только явно заданные значения. Preflight блокирует отсутствие вариации и утечку общего preset до inference; strict fairness допускает лишь заявленные `experimental_parameters`. Нижний serializer и обновление cache после смены digest покрыты отдельными interception/regression tests.

Старый прогон с перезаписанными API-параметрами методологически недействителен для сравнения Modelfile-профилей. Offline rescore не меняет уже выполненный inference, поэтому требуется новый CODE-прогон.

### Privacy и готовность к GitHub

Проверен весь release payload, включая hidden `.github` files, документацию, fixtures, scripts, configs и binary assets. В исходном v18.1.0 не было high-confidence private keys или API credentials, а public backend defaults уже были local/manual. При этом документация и regression provenance содержали идентифицирующие детали частной среды: реальный hostname, конкретную аппаратную конфигурацию, measured throughput, реальные model aliases, timestamps и digest/source names. Они удалены или заменены стабильными synthetic values; содержательная evidence scorer fixtures сохранена.

Добавлен рекурсивный `Test-Public-Release.ps1`. Он fail-closed обнаруживает runtime/results directories, timestamped benchmark artifacts, private/public key files, private-key bodies, известные token formats, реальные home paths, non-example e-mail, personal markers и включённый remote target. Тот же scanner запускается для source и staged bundle. Ограничение: pattern scan не доказывает отсутствие секрета произвольного формата, поэтому checklist требует ручной проверки diff, ZIP list и diagnostics. Перед open-source публикацией всё ещё требуется явный выбор лицензии.

Текущий development Git root не является public-ready source tree: он отслеживает historical raw baselines, а рядом находятся старые bundle/ZIP. Аудит всех двух commits не нашёл private-key bodies или high-confidence credential tokens, но обнаружил Windows-home patterns в 3 tracked files и известные private identity/topology markers в 12 tracked files, включая historical checkpoints. Remote сейчас не настроен, поэтому внешней публикации из этого checkout не обнаружено. Безопасный путь зафиксирован в checklist: создать новый репозиторий из прошедшего audit v0.21.0.0 snapshot. Историю development-репозитория нельзя отправлять в public remote или переписывать без отдельного явного решения владельца.

### Benchmark resume

Подтверждена причина повторного `WinError 10061`: прежний `/bench resume` вызывал `model_catalog()` до восстановления backend/tunnel. В v0.21.0.0 порядок исправлен: stale transport завершается, cache сбрасывается, выполняются ограниченные reconnect attempts, затем читаются version/catalog и проверяется environment. Completed records не повторяются; active run начинается сначала. Idempotent export после уже завершённого inference не требует сервера. Checkpoint diagnostics очищаются от endpoint/user/home path и отделены от model score.

Остающиеся ограничения: resume остаётся явным действием пользователя и не ждёт сеть бесконечно; незавершённый streamed response не может безопасно продолжаться с середины; после перезагрузки inference node повторяемый run ожидаемо становится cold и маркируется recovery telemetry.

### Результаты и UX

JSON/CSV были пригодны для машинного анализа, но не давали пользователю немедленной визуальной интерпретации. Теперь финализация создаёт offline HTML с отдельными Native/Final шкалами, warm speed, uncertainty, heatmap и сравнительными таблицами. Raw prompts и model answers не включаются. Интерфейс сокращён до task-oriented основных действий, а single/category/full/sweep/CLI перенесены на второй уровень. Дублирующий resume из advanced удалён.

Терминальная сводка дополнительно показывает наблюдаемую сравнительную аналитику: Native-лидера и отрыв, пересечение доступных 95% интервалов, warm-speed, минимальный seed SD, category leaders, recovery и format/schema diagnostics. Двусмысленные `COMPLETE` и `RECOVERY` заменены на `GEN`, `TASK` и `REC.USED`; полное имя worst test не обрезается.

HTML escaping и запрет external URL/JavaScript покрыты regression tests. Остающийся риск: статический отчёт не заменяет интерактивную статистическую среду; при одном seed он явно показывает недостаточность stability evidence, но не может исправить дизайн эксперимента.

### Границы изменения и проверка

Видимые benchmark prompts, references и sampling не менялись. Scorer исправлен отдельным этапом с regression fixtures; затем без изменения prompts введены независимые completion facets. `groundedness_adversarial` различает semantic content, exact schema и prose/JSON consistency; RU context scorer не принимает цитирование ошибки assistant за текущий факт; instruction scorer допускает необязательную нумерацию перед обязательными русскими префиксами.

Схемы: config v3, spec v9, record v12, summary v11, checkpoint v9. Offline regression: 210/210; scorer gold: 15/15. Offline audit сохранённого прогона обработал 216/216 records без inference и без изменения SHA-256 исходника. Forced cp1251, privacy audit, staged hashes и ZIP integrity выполняются release gate.

## Аудит v18.0.0: topology, installer и публичная безопасность

### Найдено в v17.6.0

- public `backend_settings.json` включал LAN profile и `remote_access.mode=auto`;
- client source содержал конкретный SSH alias;
- llama.cpp defaults содержали абсолютные пути одного Windows-пользователя;
- Ollama всегда вызывал SSH tunnel, поэтому Client не мог штатно работать с Ollama на том же ПК;
- portable backend export отделял API secrets, но endpoint и локальный key path всё ещё жили в общей конфигурации;
- setup wizard только проверял заранее подготовленную удалённую машину и не разворачивал OpenSSH/Ollama;
- release gate не доказывал отсутствие private keys и personal topology.

### Исправлено

- backend schema v3 разделяет `target_mode=local|remote` и backend transport;
- public defaults local/manual и identity-free;
- локальный Ollama использует `127.0.0.1:11434` без SSH;
- remote endpoint/key path извлечены в release-excluded `Runtime/connections.json`;
- connection bundle v1 проверяется fail-closed, pinning использует host public key + fingerprint;
- Client использует отдельный `known_hosts`, `StrictHostKeyChecking=yes` и `IdentitiesOnly=yes`;
- добавлены Client/Server/AllInOne installer roles;
- Server installer требует `.pub`, включает Windows OpenSSH, глобальный publickey-only policy, loopback Ollama и только SSH firewall rule;
- добавлен client-side Ed25519 key helper без перезаписи существующего key;
- release gate проверяет public topology, private-key markers, common key/access names, runtime exclusions и personal markers.

### Не изменено

Benchmark prompts, scorers, fair compare, execution order, RU_LANGUAGE_STRESS v2 и checkpoint state machine сохранены. Это отделяет deployment/security migration от методологии оценки моделей.

### Remaining risks

- Windows installer проверен parser/static regression, но фактические OpenSSH/Ollama/Tailscale installation paths требуют smoke-test на чистой Windows 11 VM;
- Tailscale login/ACL и router port forwarding намеренно не автоматизированы;
- direct inbound SSH зависит от public address/CGNAT и политики сети;
- Python tools/scorers остаются defense-in-depth, не полноценной OS sandbox;
- compatibility core остаётся большим монолитом и должен декомпозироваться только последовательно после characterization tests;
- installer по умолчанию настраивает Ollama; llama.cpp binaries/models остаются отдельной optional установкой.

## Аудит RU_LANGUAGE_STRESS v17.6.0

Проверены 35 реальных RU records из `2026-08-24_12-59-55_all_compare.json` без оценки сравнительного качества моделей. Во всех 35 terminal JSON совпадал с reference, но scorer v1 систематически смешивал семантику с наличием узких фраз:

- корректные русские переформулировки получали примерно `0.55–0.88` из-за отсутствия ожидаемого regex;
- полностью английский business-tone ответ мог получить до `0.64` при правильном JSON;
- полный повтор одного business-tone ответа получил `0.90`, хотя duplicate five-gram ratio был около `0.443`;
- скрытый word range у context-corrections не следовал из prompt;
- check rows не объясняли, какой фрагмент ответа вызвал результат.

Scorer v2 устраняет эти дефекты без изменения inference settings. Terminal `BENCHMARK_RESULT` является основным источником структурированной семантики. Prose оценивается только по явно заданным format constraints, противоречиям, запрещённым добавлениям, языку и repetition. Конфигурация весов и caps хранится рядом со спецификацией теста; у context-corrections диапазона слов нет ни в prompt, ни в scorer.

Шесть subscores выводятся раздельно: `structured_semantics`, `format_constraints`, `prose_consistency`, `forbidden_additions`, `language_quality`, `repetition`. Каждый check содержит evidence/reason. Caps делают видимыми критические случаи: отсутствие prose, неверный JSON, смысловое противоречие, запрещённый новый факт, неверный язык и сильное повторение.

Проверка на пяти gold answers даёт `1.0`. Реальные корректные перефразировки больше не получают ложный штраф; английский, смешанный и повторённый ответы получают соответствующие diagnostics/caps. Fixture `Tests/Fixtures/ru_language_stress_sanitized_v2.json` содержит 35 обезличенных regression records: реальные имена моделей, timestamps и digests удалены. Offline rescore сохраняет raw primary/final answers и полный исходный score в `score.original`, inference не запускается.

Prompt изменён только у `ru_business_tone`: benchmark v2 восстанавливает исходный диапазон 70–110 слов. Для legacy v17.5.3 rescore сохраняется исторический явный диапазон 55–90. Остальные четыре RU prompts/version не менялись.

## Короткий аудит остальных текстовых scorers

- `logic_constraints`, `dialogue_state`, `russian_editing` и `groundedness` используют общий `structured_reference_v1`: он надёжно проверяет terminal JSON, но почти не проверяет противоречия свободного текста. Это medium-risk false-positive и следующий кандидат на versioned scorer v2.
- `russian_editing` требует один точный `corrected_text` в JSON. Допустимые эквивалентные редакторские варианты могут получить ложный штраф. Нужен отдельный semantic/edit-distance plus protected-token contract, а не изменение текущего v1 на месте.
- `instruction_v4` проверяет требования, явно заданные prompt: четыре строки, prefixes, одно предложение, отсутствие Latin и таблиц. Узких скрытых смысловых regex в нём нет.
- `simpson_v3` и `funnel_v3` сочетают terminal JSON с явно сформулированной структурой текста. Их ограничения длины присутствуют в prompt/metadata; менять их вместе с RU scorer не следует.
- Исполняемые `python_debug`, `retention_d7` и `analytics_case` не зависят от позитивных языковых regex; их отдельная проблема — граница OS sandbox, уже отражённая в SECURITY.md.

Эти scorers намеренно не переписаны в v17.6.0: одновременная смена нескольких prompt/scorer contracts затруднила бы атрибуцию регрессий.

## Аудит обрыва и продолжения benchmark

В приложенном suite после обрыва было 105/105 уникальных записей без пропусков и дублей. Между четвёртым и пятым record наблюдался разрыв около 45 минут, после которого suite продолжился. Однако checkpoint v6 сохранялся только после завершённого run, не фиксировал активную попытку и не отделял транспортную ошибку от model error. Поэтому точный прерванный run и число попыток восстановить было невозможно; дополнительная cold load после рестарта смешивалась с обычной скоростью.

Checkpoint v7 вводит durable state machine:

- перед inference атомарно сохраняются `active_job` и attempt со статусом `running`;
- hard restart переводит stale attempt в `abandoned` и повторяет только этот run с начала;
- retryable transport failure переводит suite в `paused_connectivity` и не запускает оставшуюся матрицу;
- completed records остаются неизменными;
- clean Ctrl+C и hard restart имеют отдельную attempt history;
- export проходит через `finalizing` и завершается только после записи пяти output paths, размеров и SHA-256;
- missing output делает checkpoint resumable, а повторная финализация безопасно перезаписывает тот же набор файлов.

Client-recovery diagnostics (`attempt_count`, interruptions, transport failures, resumed run, post-resume load state) записываются отдельно. Summary v7 показывает эти поля, но не добавляет неудачные транспортные попытки в native/final quality или speed samples.

Остающийся риск: v0.21.0.0 сознательно ставит suite на паузу и требует явного `/bench resume` после восстановления сети; бесконечное автоматическое ожидание не используется. Это предотвращает незаметное многочасовое зависание и даёт оператору проверить backend. Текущий run всегда повторяется целиком — частичный streamed answer не считается завершённым и не получает model score.

Валидация изменений: Python compile, UTF-8 regression `158/158`, forced-cp1251 regression `158/158`, затем manifest/staged payload/ZIP gate через `Build-Release.ps1`.

## Аудит UI-яркости v0.21.0.0

Причина плохой читаемости — не Matrix-дизайн как таковой, а систематическое использование ANSI `dim`/dark gray для разделителей, breadcrumbs, status strips и пояснений. На части Windows-терминалов эти цвета визуально почти сливаются с фоном.

В v0.21.0.0 яркая Matrix стала default: accent и secondary используют bright green без `dim`, muted text — bright white. Добавлены сбалансированная, прежняя приглушённая и классическая контрастная палитры. Все существующие UI-примитивы используют одну динамическую palette function, поэтому тема переключается без перезапуска и без дублирования экранов.

Настройка хранится отдельно от backend/model profiles в schema `local-llm-ui-settings` v1. Запись атомарная (`.tmp` + replace), повреждение fail-soft возвращает яркий default и не блокирует startup. ENV override сохранён для automation. В главное меню добавлен пункт 7, в command surface — `/ui`.

Регрессии проверяют яркий default без ANSI dim, атомарное сохранение, повторное чтение, смену темы через меню и маршрут главного меню. UI-theme subchange не меняет inference; изменения scorer/recovery описаны отдельными разделами выше.

Финальная валидация версии выполняется единым release gate: compile, UTF-8/forced-cp1251 regression, startup integration, manifest, staged hashes и ZIP integrity.

## Аудит startup-дефекта v17.5.1

Причина ошибки запуска подтверждена статическим symbol-table анализом. Присваивание `version=int(...)` находилось внутри `main()`, поэтому Python считал имя `version` локальным во всей функции. Более ранний вызов `version(2)` после подключения к Ollama приводил к `UnboundLocalError`, хотя regression suite завершался успешно.

В v17.5.2 локальное имя заменено на `prompt_version`. Regression проверяет таблицу символов `main()` и запрещает локальное затенение backend probe. Это надёжнее проверки одной строки: тест упадёт при любом будущем присваивании имени `version` в той же области.

Диагностический пробел также устранён: `main()` раньше перехватывал startup-исключение и возвращал код 1, поэтому внешний обработчик записывал только `exit_code=1`. Теперь `STARTUP_ERROR`, тип исключения и traceback записываются до возврата. Benchmark/runtime/UI-поведение не менялось.

Валидация: compile; UTF-8 и forced-cp1251 regression `151/151`; отдельный mocked startup-путь `regression -> connect -> version probe -> model catalog -> home -> clean exit`; manifest, staged hashes и ZIP integrity.

## Аудит UI v17.5.1

В v17.5.0 одновременно использовались 60- и 78-символьные рамки, несвязанные стили заголовков и плоские длинные списки. В Advanced Benchmark клавиша `0` вела домой, хотя в остальных вложенных меню означала «назад». Термины `prompt/prompts`, `benchmark`, `status` и русские аналоги смешивались даже в одном сценарии.

В v17.5.1 добавлена единая система UI-примитивов: header, breadcrumb, section, menu item, status strip и footer. На неё переведены Control Deck, рабочий Client, Benchmark Lab, custom-prompt wizard, Advanced, Backend, Remote, setup, doctor, Dashboard, Status, help и post-benchmark actions. Matrix-оформление статичное: без мерцания, задержек и фоновых потоков. Значимые состояния продублированы текстом и не зависят от различения цветов. Переменная `LOCAL_LLM_UI_THEME=classic` сохраняет альтернативную палитру.

Исправлена навигация Advanced: `0` возвращает в Benchmark Lab, `H` — в главное меню; прежний `9` сохранён как совместимый alias. Мастер «Свой промпт» разбит на четыре видимых этапа без добавления новых обязательных вопросов.

Границы патча: prompts, scorers, sampling, recovery, backend lifecycle и форматы артефактов не менялись. Добавлены две UI-регрессии: согласованность рамок/доступность без цвета и маршруты `0/H` в Benchmark Advanced. Python compile и offline regression: `150/150`.

## Аудит v17.5.0

Прогоны custom prompt технически создавали raw, checkpoint, summary и tested-profile artifacts, но workflow был слишком сложным, а хранение prompt имело неясную семантику. Найдены и исправлены следующие дефекты:

- `prompts.json` хранил только текущую версию; сохранение было неатомарным, а malformed JSON мог быть тихо заменён;
- точный custom prompt не хранился как версионный checkpoint snapshot;
- unscored и single-run evidence могли попасть в импортируемые tested profiles;
- один seed давал `rank_stability=1.0`, хотя стабильность не измерялась;
- summary singleton fingerprint мог скрывать несколько launch/runtime fingerprints;
- CSV не нейтрализовал строки, которые spreadsheet может интерпретировать как формулу;
- свободный русский текст и terminal JSON не имели отдельной семантической проверки.

В v17.5.0 добавлены immutable prompt versions, atomic/fail-closed index, точная provenance, evidence gate, plural fingerprints, честная семантика rank stability, CSV hardening и `ru_language_stress_v1`.

Пять присланных RU tests адекватно разделяют context correction, causal caution, negation, business tone и debureaucratization. Изменён только word range для короткого рабочего сообщения: 55–90 вместо 70–110, чтобы не награждать padding. Для каждого теста есть golden answer и adversarial contradiction case.

Остающиеся риски: regex-проверка смысла не заменяет blind human review; три seeds всё ещё дают широкую неопределённость; custom prompt без scorer не позволяет автоматически ранжировать качество.

Валидация: Python compile и offline regression `148/148` пройдены.

## Аудит актуального benchmark без оценки моделей

Пять приложенных артефактов согласованы по числу записей: 35 runs = 7 моделей × 5 тестов × 1 seed. Ошибок исполнения backend нет. Этот прогон пригоден для проверки pipeline и формата экспорта, но недостаточен для вывода об устойчивости качества: фактически использован только seed 42.

Найдены методологические дефекты v17.3.2:

- фиксированный порядок `model -> simpson -> funnel -> retention -> analytics -> instruction` делал `simpson` cold-нагрузкой для каждой модели, а остальные тесты — warm; скорость теста смешивалась с позицией;
- `primary_eval_warm_avg` отбрасывал первую позицию, а не классифицировал реальный `load_duration`;
- один run fingerprint показывался как идентичность группы нескольких seeds;
- отсутствовали SD, min/max, worst seed и rank stability;
- Pareto сравнивал только point estimates;
- launch settings и наблюдавшийся runtime назывались одним fingerprint;
- ULTIMATE suite с `fair_default` фактически выполнял primary в FAST, что корректно записано в effective config, но название режима в UI легко трактовать неверно;
- один recovery увеличил ответ примерно с 12 тыс. до 23 тыс. символов, усилил длинные повторы и снизил score с 0.05 до 0; внешний finalizer безусловно заменял предыдущего кандидата;
- generated-code scorers блокировали основные I/O API, но список не покрывал `read_fwf`, `read_clipboard`, HDF/Stata/SPSS/ORC/XML и другие обходные пути.

## Исправлено в v17.4.0

### Benchmark engine

- Добавлен `select_benchmark_candidate`: completed-кандидат имеет приоритет, затем score, затем меньшая повторяемость и меньшая длина. Recovery больше не выбирает длинный ответ только за длину.
- `benchmark_repetition_metrics` считает дубли строк и повторные 5-граммы; метрики сохраняются для native/final/recovery.
- Profile fingerprint исключает seed, run fingerprint сохраняет seed.
- Launch fingerprint отделён от observed runtime fingerprint, включающего telemetry и model digest.
- Cold/warm определяется порогом фактической загрузки 1.0 секунды.
- Summary v5 добавляет sample SD, min/max, 95% CI, worst seed, seed ranks, rank stability и uncertainty-aware Pareto.
- Balanced schedule детерминированно меняет порядок моделей и циклически вращает тесты, сохраняя model blocks ради разумного числа reload.
- Raw/summary JSON и CSV записываются atomically через `.tmp` + replace.

### Field audit BULL v0.24.0.0 · 2026-09-27

Прогон `chat_final` проверен без оценки качества моделей. Raw JSON, checkpoint и
CSV содержат 108 уникальных jobs: 3 модели × 12 тестов × 3 seeds. Все jobs
завершены с первой попытки, transport/retry/resume ошибок нет; summary JSON/CSV
содержат 36 согласованных групп, hashes всех шести финальных outputs совпадают.
HTML не содержит JavaScript, внешних URL, prompts, raw answers или домашнего пути.

Данные выявили три дефекта orchestration/export, не scorer:

- прежний `balanced` один раз перемешивал модели, после чего каждая модель занимала
  фиксированный блок; seeds 42/43/44 всегда были первой/второй/третьей попыткой;
- native effective config сохранял `recovery.enabled=true`, хотя runner правильно
  не запускал recovery, что делало provenance двусмысленным;
- tested-profile export создал 36 записей вместо 21 уникальной импортируемой
  конфигурации и переносил seed первого record в рабочий Client.

Новый job-level execution plan использует counterbalanced waves: позиции моделей и
тестов вращаются, а seeds распределяются по разным позициям внутри каждой волны.
Модель загружается один раз на волну. Старые checkpoints без `execution_plan`
продолжаются в исходном порядке. Tested profiles теперь группируются по canonical
Client payload, сохраняют plural evidence fingerprints и не импортируют seed.
Native config отдельно хранит requested/effective recovery и причину suppression.
Prompts, scorers, model answers и sampling/runtime options не изменены.

### Покрытие качества

Старые prompts/scorers оставлены без изменений как regression anchors. Добавлены независимые категории:

- `python_debug`: исполняемая функция на скрытых edge cases;
- `logic_constraints`: формальная логика и уникальность;
- `dialogue_state`: актуальность требований в диалоге;
- `russian_editing`: русская грамматика и сохранение защищённых токенов;
- `groundedness`: supported/contradicted/unknown и embedded prompt injection.

### Архитектура

Начата поэтапная декомпозиция без rewrite:

- отдельные entry points Client и Benchmark Lab;
- общий пакет `Shared/local_llm_shared` для schemas, tested profiles, telemetry fingerprints и backend protocol;
- основной runtime временно остаётся compatibility core;
- Benchmark Lab автоматически создаёт versioned `*_tested_profiles.json`, Client импортирует выбранный profile только явной командой.

### UX

Главное меню теперь описывает задачи, а не внутренние команды. Benchmark Lab использует progressive disclosure: quick run, compare, category suite, full matrix, resume, rescore, advanced. Тесты сгруппированы по категориям; результаты явно называют native quality и final system quality и показывают разброс/неопределённость.

## Оставшиеся риски

- Compatibility core всё ещё велик; Apps пока разделяют entry surface и контракты, но не все runtime-модули физически извлечены.
- Исполнение model-generated Python использует AST-политику, `python -I`, очищенное окружение и timeout, но не является Windows OS sandbox.
- При малом числе seeds CI и rank stability неинформативны; summary честно возвращает `insufficient_samples`.
- Balanced model blocks уменьшают order bias, но не заменяют рандомизированные повторы в разное время и контроль фоновой нагрузки.
- Автоматические scorers измеряют формализованные требования и не заменяют blind human review для качества объяснения.

## Проверка v17.4.0

- Python compile: passed;
- AST duplicate functions: passed;
- offline regression: 141/141 passed до release gate;
- forced cp1251, manifest и ZIP выполняются `Build-Release.ps1` перед публикацией.

## Хотфикс v17.3.2

После анализа первого реального `analytics_case` исправлены четыре связанные проблемы:

- контекст теста был фактически ограничен профилем `8192`, теперь действует test-local минимум `16384`;
- THINK мог потратить весь primary budget без final answer, теперь `force_final_answer` вызывает FAST-финализатор;
- scorer ошибочно требовал буквальные имена аргументов `users, orders`, теперь проверяется сигнатура из двух позиционных входов и фактическое использование обоих;
- единый try-блок связывал SQL и Python, теперь они исполняются и оцениваются независимо.

Execution policy и scorer получили новую provenance: `analytics_case v2` / `analytics_case_v2`. Режим THINK/FAST по-прежнему выбирается по capability конкретной модели.

## 1. Цель аудита

После серии крупных изменений были отдельно проверены:

- функциональные ошибки;
- маршрутизация команд и меню;
- backend abstraction Ollama / llama.cpp;
- SSH / WAN attack surface;
- tools и исполнение model-generated code;
- benchmark scorers;
- файловые операции;
- release integrity;
- повторный I/O и очевидные горячие места;
- UX терминального интерфейса;
- documentation discoverability.

## 2. Архитектурное состояние

Финальный v17.3.2 source содержит:

- 9681 строка;
- 339 top-level функций;
- `main()` длиной 1295 строк.

Это не performance bottleneck inference, но уже заметный maintainability risk.

Это пока приемлемо для single-file distribution, но является главным maintainability risk.

Полный модульный rewrite в v17.2 **не выполнялся**, потому что он одновременно изменил бы слишком много поведения и сделал regression suite менее полезным.

Вместо этого v17.2:

- усиливает command-router invariants;
- добавляет тесты на прошлые failure classes;
- выносит UX-правила в общие helpers;
- документирует план будущей модульной декомпозиции.

## 3. Найденные реальные дефекты

### F-01. Tools могли упасть с NameError

Серьёзность: High, functional.

`chat_agent()` использовал `silent`, которого не было в локальной области.

Исправление:

```text
chat_agent(..., silent=False)
```

Добавлен regression test, который реально проходит tools chat call.

### F-02. Неизвестная slash-команда могла стать prompt модели

Серьёзность: High, UX / correctness.

После цепочки command handlers оставался общий chat path. Неизвестная строка `/something` могла уйти активной модели.

Это объясняет класс предыдущих проблем Benchmark Lab.

Исправление:

```text
/unknown -> ошибка + /help
//foo    -> явный prompt /foo
```

То есть slash-command fallthrough теперь запрещён архитектурно.

### F-03. `safe` tools слишком широко читали файловую систему

Серьёзность: Medium, privacy.

`read_file`, `list_directory`, `search_files` могли читать путь вне Workspace без отдельного approval.

Исправление:

```text
Workspace -> разрешено
вне Workspace -> READ confirmation
```

### F-04. `python -I` ошибочно мог восприниматься как sandbox

Серьёзность: Medium, security model.

`-I` изолирует Python environment частично, но не является OS sandbox.

Исправление:

- UI прямо предупреждает об этом;
- child environment очищается;
- common credentials не наследуются;
- HF/Transformers network path отключается в scorer child;
- scorer AST deny-list расширен.

Оставшийся риск: пользовательский Python после `RUN` всё ещё выполняется с правами пользователя Windows.

### F-05. SSH host/user не имели достаточной validation

Серьёзность: Medium.

Поля конфигурации используются при построении SSH argv.

Исправление:

- host и user имеют whitelist validation;
- ведущий `-` запрещён;
- whitespace запрещён;
- user передаётся отдельным `ssh -l USER HOST`;
- shell interpolation не используется.

### F-06. External llama HTTP не имел безопасного default

Серьёзность: Medium.

Произвольный:

```text
http://PUBLIC-IP:8080
```

мог быть принят без предупреждения.

Исправление:

- HTTP разрешён по умолчанию только loopback;
- remote endpoint должен быть HTTPS;
- сознательный override: `allow_insecure_external=true`.

### F-07. llama.cpp capabilities falsely заявляли thinking

Серьёзность: Medium, correctness.

Backend code добавлял `thinking` любой llama.cpp модели.

Это ненадёжно: server capability и model/template capability не одно и то же.

Исправление:

- unconditional `thinking` удалён;
- backend сообщает только то, что может доказать консервативно.

### F-08. Release manifest имел stale SHA

Серьёзность: Medium, release integrity.

В v17.1.2 один `Docs/AI_CONTEXT.yaml` hash в `RELEASE_MANIFEST.json` не совпадал с фактическим файлом.

Причина: документ изменялся после формирования hash-set.

Исправление v17.2:

- manifest создаётся после финальных docs;
- каждый manifest hash перепроверяется до упаковки;
- packaging не изменяет входящие файлы после hash gate;
- obsolete-version check привязан к точному текущему version.

### F-09. External llama.cpp не требовал API key

Серьёзность: Medium, remote security.

Одного HTTPS недостаточно, если внешний endpoint доступен посторонним.

Исправление:

- upstream-supported Bearer API key;
- секрет берётся только из environment variable;
- default env name: `LOCAL_LLM_LLAMA_API_KEY`;
- ключ не сохраняется в `backend_settings.json`;
- non-loopback external endpoint без ключа блокируется;
- отдельный unsafe override требует явного включения.

### F-10. Benchmark menu говорил «несколько моделей», но скрыто выбирал all

Серьёзность: Medium, UX / benchmark cost.

Исправление:

- multi-model path теперь открывает реальный selector;
- `all` выбирается только явно;
- regression закрепляет canonical `/bench compare <test>` route.

### F-11. Generic errors не подсказывали recovery action

Серьёзность: Low/Medium, UX.

Добавлен `error_hint()` для:

- connection refused/reset/timeout;
- backend unavailable;
- unsupported THINK;
- external API key;
- SSH host-key verification;
- missing paths;
- context-window exhaustion.

Сообщение теперь содержит «Что сделать», а не только exception text.

### F-12. SSH probe раскрывал PowerShell expression в login shell

Серьёзность: High, startup correctness.

Probe передавал `$env:COMPUTERNAME` через `powershell.exe -Command` после SSH target. На некоторых Windows SSH-конфигурациях login shell сначала раскрывал expression в `LAB-PC`, после чего вложенный PowerShell пытался выполнить `LAB-PC` как команду. Клиент сообщал, что доступного SSH-профиля нет, хотя SSH-маршрут был рабочим.

Исправление:

- probe использует literal `-EncodedCommand`;
- PowerShell получает общий UTF-8 bootstrap;
- regression декодирует payload и проверяет, что expression не передаётся через `-Command`.

### F-13. Диагностика Windows декодировалась только как UTF-8

Серьёзность: High, startup diagnostics.

Windows PowerShell 5.1, OpenSSH и native console programs могут возвращать UTF-8, UTF-16LE, CP866 или CP1251. Принудительное `errors=replace` превращало полезный русский текст в `���`.

Исправление:

- SSH/PowerShell subprocess собирает bytes;
- decoder распознаёт BOM и UTF-16LE, затем UTF-8 и Windows Cyrillic code pages;
- удалённые PowerShell scripts принудительно настраивают UTF-8 stdout/stderr;
- clipboard PowerShell использует тот же безопасный путь.

### F-14. Managed llama extra_args могли изменить security invariants

Серьёзность: High, remote security.

Произвольные `extra_args` добавлялись после управляемых server flags. Опции `--host`, `--port`, auth/TLS, UI, agent/MCP или model path могли переопределить безопасную конфигурацию.

Исправление: managed `extra_args` запрещает сетевые, authentication, UI/agent/MCP, filesystem/media и дублирующие dedicated settings options. Для полностью самостоятельного server lifecycle остаётся `transport=external`.

### F-15. Bearer auth мог участвовать в HTTP redirect

Серьёзность: High, credential exposure.

Default urllib redirect behavior не является подходящей политикой для секретного inference endpoint.

Исправление: external llama opener полностью блокирует redirect и требует конечный `base_url`. Config/security ошибки health check больше не маскируются как generic offline.

### F-16. Portable backend import недостаточно проверял nested data

Серьёзность: Medium/High, configuration integrity.

Проверялись top-level keys, но неизвестные вложенные поля, secret-like fields и profile kind могли пройти merge.

Исправление:

- strict nested allow-list;
- запрет stored passwords/API keys/tokens;
- canonical kind по identity профиля;
- проверка ports, order, environment variable name и unsafe llama flags;
- UTF-8 BOM compatibility;
- strict JSON booleans, чтобы строка `"false"` не стала truthy security override.

### F-17. External backend ошибочно зависел от SSH doctor/signature

Серьёзность: Medium, correctness/UX.

External llama.cpp не должен требовать доступный SSH profile или строить signature из managed server args.

Исправление: doctor пропускает SSH для external transport, а runtime fingerprint/signature включают безопасный external URL и auth configuration. HTTP и HTTPS явно различаются в status.

### F-18. llama.cpp structured output использовал устаревшую форму schema

Серьёзность: Medium, upstream compatibility.

Текущий llama-server принимает `response_format` с `type=json_schema` и прямым полем `schema`. Клиент теперь преобразует пользовательский OpenAI-style nested input в актуальную upstream форму и сохраняет поддержку короткой schema-записи.

## 4. Производительность

### P-01. Повторное чтение JSON settings

`backend_settings.json` и `model_profiles.json` читались многократно.

Исправление:

- mtime cache;
- на cache hit возвращается deepcopy;
- save обновляет cache.

Это не ускорит inference, но уменьшает лишний disk I/O в меню/status/benchmark setup.

### P-02. Streaming progress

Ранее intermediate progress мог повторно суммировать длины chunks.

В прошлой ревизии уже переведено на O(1) counters:

```text
reasoning_chars
answer_chars
```

Сохранено.

### P-03. GPU telemetry benchmark

Сохраняется один долгоживущий `nvidia-smi --loop-ms=500`, а не отдельный process на каждый sample.

Сохранено.

### P-04. Не оптимизировать inference вслепую

Client-side micro-optimizations не должны подменять model/backend benchmark.

Основная latency по-прежнему определяется:

- model compute;
- CPU/GPU split;
- context;
- output tokens;
- rollover cycles;
- backend configuration.

### P-05. Полный regression suite выполнялся на каждом старте

114+ offline tests занимали около 10-15 секунд даже для неизменного release. Это выглядело как зависание до подключения backend.

Исправление:

- первый запуск выполняет полный fail-closed suite;
- успешный результат кэшируется только для точных SHA256 клиента и теста, Python executable и Python version;
- любое изменение автоматически инвалидирует cache;
- `Run-Tests.ps1` всегда выполняет полный suite;
- read-only bundle безопасно возвращается к полному прогону.

## 5. UX-аудит

Применены принципы:

- visibility of system status;
- recognition rather than recall;
- contextual help;
- plain-language errors with recovery action;
- progressive disclosure;
- consistent `0 = назад`;
- `? = помощь`;
- breadcrumbs/current location;
- visible mode/model/context in chat prompt;
- progress for long operations.

### Изменения

Главное меню теперь объясняет каждый раздел.

Пример:

```text
2. Benchmark Lab
   Сравнение моделей, analytics_case, resume, rescore
```

Breadcrumb:

```text
⌂  Главное меню > Backend > Remote
```

Chat prompt:

```text
Вы [THINK | qwen... | CTX 37%] ›
```

Контекстная помощь:

```text
/help modes
/help prompts
/help benchmark
/help backend
/help tools
/help remote
/help chat
```

## 6. Backend recovery UX

Добавлено:

```text
/backend setup
/backend doctor
/backend export
/backend import <path>
```

Это решает отдельный disaster-recovery сценарий: текущий inference-PC недоступен и нужно подключить совершенно другую Windows-машину.

## 6.1. Static audit snapshot

Финальный source проверен стандартным AST/текстовым аудитом:

```text
source lines:            9617
top-level functions:      337
largest main():          1295 lines
shell=True:                 0
direct eval():              0
direct exec():              0
```

Отсутствие `shell=True` и прямых `eval/exec` уменьшает attack surface, но не заменяет sandbox или полноценный security review.

## 7. Remaining risks

### R-01. Монолитный single-file client

Приоритет: High, maintainability.

Следующий крупный архитектурный шаг лучше делать отдельно:

```text
core/
backends/
benchmarks/
tools/
ui/
storage/
```

Не объединять это с model/backend optimization.

### R-02. Нет настоящей OS sandbox для model-generated Python

Приоритет: High, security if tools are enabled.

Текущий уровень:

```text
explicit RUN
python -I
scrubbed env
AST restrictions in benchmark scorers
Workspace cwd
timeout
```

Для сильной изоляции в будущем нужен отдельный low-privilege process/container/Windows Sandbox boundary.

### R-03. Managed backend setup ориентирован на Windows

Linux/macOS backend можно использовать как external/manual, но wizard probe использует PowerShell Windows.

### R-04. llama.cpp API/flags быстро развиваются

Нельзя считать захардкоженную документацию вечной.

При смене llama.cpp build всегда проверяй:

```text
llama-server --version
llama-server --help
```

### R-05. Terminal editor ограничен

Windows editor хорошо поддерживает paste, Backspace, Enter, Shift+Enter, но полноценного cursor editing/history пока нет.

### R-06. Модельные capabilities не всегда машиночитаемы

Ollama предоставляет capability data лучше, чем generic llama.cpp router.

Клиент намеренно использует conservative behavior.

## 8. Что специально не менялось

- thread count моделей;
- default context выше 8192;
- pagefile policy;
- benchmark references;
- scorer ground truth;
- WorkMatch models;
- model quantization;
- backend performance flags.

Аудит клиента не должен одновременно менять inference baseline.

## 9. Regression policy v17.3.2

Новые regression classes:

- tool `silent` scope;
- external file-read confirmation;
- Workspace read;
- child env secret stripping;
- SSH option injection;
- SSH PowerShell double expansion and OEM decoding;
- external HTTP guard;
- external redirect guard and API-key/config propagation;
- managed llama extra-argument override guard;
- strict portable backend import;
- exact-byte startup regression cache;
- conservative llama capabilities;
- unknown slash-command guard;
- help/backend migration discovery;
- settings cache behavior.

Также сохраняются все прежние benchmark/scorer/ULTIMATE/router tests.

## 10. UX references

Command Line Interface Guidelines:
https://clig.dev/

Nielsen Norman Group, usability heuristics:
https://www.nngroup.com/articles/ten-usability-heuristics/

Применённые идеи:

- timely status feedback;
- concise output;
- discoverability;
- examples;
- contextual help;
- recognition rather than recall;
- actionable errors;
- user control and clear exits.

## 11. Security references

Microsoft OpenSSH for Windows:
https://learn.microsoft.com/windows-server/administration/openssh/

Ollama:
https://docs.ollama.com/

llama.cpp server:
https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

## 12. Итог

v17.3.2 не делает программу "абсолютно безопасной". Это невозможно утверждать для клиента, который по желанию пользователя умеет исполнять Python и управлять SSH/backend.

Цель релиза другая:

- закрыть найденные concrete bugs;
- сделать dangerous actions explicit;
- уменьшить implicit trust;
- дать безопасные defaults;
- сделать состояние системы видимым;
- не позволять navigation errors превращаться в LLM prompts;
- зафиксировать remaining risks и дальнейший архитектурный путь.


## 13. Финальная validation

```text
normal regression:         122/122
forced cp1251 regression:  122/122
startup integration:       ok=True, 122/122
Python compile:             PASS
AST duplicate functions:   PASS
```

Release gate дополнительно проверяет:

- точную версию всех versioned root artifacts;
- обязательные документы;
- manifest SHA256 каждого исходного файла;
- тот же hash-set в staged payload;
- один top-level каталог ZIP;
- ZIP integrity;
- итоговый SHA256 bundle.
