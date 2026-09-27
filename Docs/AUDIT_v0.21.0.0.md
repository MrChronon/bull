# Аудит v0.21.0.0: быстродействие, устойчивость и безопасность

Обновлено 26 сентября 2026. GPU Lab основана на проверенных по manifest исходниках
v0.20.0.0. Ниже сохранён аудит защитных исправлений и UI предыдущих версий.
Предыдущий bundle и замороженная v17.3.2 не изменены. Проверки выполнялись без
запросов к реальным моделям и без изменений сервера, служб, firewall или роутера.

## Новый экспериментальный раздел GPU

Данные подключения не копировались; рабочие службы, firewall и роутер не менялись.
Изолированный child environment, CUDA UUID, loopback bind, ownership-check порта,
Windows Job Object и named mutex, bounded HTTP, отключённый cloud/Vulkan,
private checkpoint + OS file lock, экранированный HTML и безопасные CSV cells.
Windows integration использует синтетические executable/API и проверяет обычное
завершение, дочерние процессы и аварийное закрытие супервизора без CIM/admin-зависимости.
Отдельные проверки: resume, изменённый workload hash, выбор UUID, N/A, статистика,
невозможность засчитать чужие процессы как выбранную карту и маршрутизация offline UI.

Ограничения: GPU residency — не измерение compute balance; общие датчики карты не
изолируют вклад модели; проверка простаивания не видит скрытую драйвером нагрузку;
опрос температуры не заменяет термозащиту. GPU Lab v1 не имеет quality scorer,
не выполняет произвольный код и не поддерживает Linux/llama.cpp. Реальное оборудование
RTX 3060/P100 и WAN ещё не проверены. Полные ограничения: `GPU_LAB.md`.

## Сохранённая область проверки v0.20.0.0

В v0.20.0.0 дополнительно проверялись навигация, команды с главной, SSH-мастер,
отмена до записи, несовпадение fingerprint, перенос настроек между билдами,
приватность ссылки на ключ и Agent-итоги. Новые UI-модули отделены от вычислительных
функций; промпты/скореры, generation options, Agent runner и verifier сохранены.
Адресная книга вне билда — явный opt-in, хранит метаданные без private-key bytes.
Реальная WAN-связь не проверялась. Подробный приёмочный сценарий: Docs/UI_GUIDE.md.

Проверены точки входа Client/Lab/Agent, Shared-модули, HTTP/SSH-границы,
streaming, tools, чтение вложений, checkpoint/resume, сохранение диалогов,
Agent configuration/history/reports, startup cache, PowerShell installers,
privacy/manifest/ZIP gates и регрессионное покрытие. Большой legacy core сохранён;
это целевой статический аудит опасных путей плюс fault-injection, не формальная
верификация каждой возможной ветви и не независимый penetration test.

## Подтверждённые проблемы и исправления

| Приоритет | Проблема | Исправление и проверка |
|---|---|---|
| P1 | EOF Ollama/llama.cpp без терминального события возвращал частичный ответ как обычный результат | ConnectionResetError; существующий checkpoint переводит suite на паузу. Тесты EOF, error chunk и done-before-EOF |
| P1 | Ollama API допускал redirects | Запрет переадресации для health/catalog/show/chat; loopback HTTP fixture подтверждает, что второй адрес не посещён |
| P1 | Неограниченный HTTP body/строка и бесконечный streaming | 16 MiB JSON, 1 MiB строка, 64 MiB stream, deadline тела ответа; отрицательные тесты размера и зависшего сокета |
| P1 | Server installer выполнял часть изменений при -WhatIf | Общий ShouldProcess до любых мутаций; реальный безопасный -LocalOnly -WhatIf и static ordering check |
| P1 | Privacy gate пропускал неизвестные форматы, текст >8 MiB и PKCS#8 markers | Fail-closed для непроверенных файлов, расширены key/token/path patterns; отрицательный тест gate |
| P2 | Source tree повторно перечислялся после manifest; ZIP проверял только имена | Упаковка точного manifest set; hash каждого распакованного ZIP entry и число файлов |
| P2 | Agent sampler синхронно опрашивал SSH/GPU при start/stop; stop мог ждать 15 секунд и запускать ещё один probe | Фоновый первый опрос, немедленный stop, поздние результаты отбрасываются; отсутствие данных остаётся null |
| P2 | Локальная GPU-телеметрия пыталась использовать SSH | Источник определяется выбранным transport. Для external backend неизвестное расположение не выдаётся за локальное железо |
| P2 | Ошибка редактирования Agent configuration меняла прежний объект; Enter мог сбросить context policy | Изменения в копии, commit после validate; Enter сохраняет текущие значения, подписи исправлены |
| P2 | Повреждённый Agent JSON ломал history/reports; NaN мешал финальному сохранению | Ограниченное чтение, validation envelopes/numeric fields/depth, finite metrics, corrupt run пропускается |
| P2 | Постоянный .tmp создавал коллизии; chat/report writes не имели fsync | Общий unique-temp + fsync + replace для checkpoint, chat, Agent JSON/CSV/HTML; rollback/двойной writer tests |
| P2 | Startup cache не учитывал часть Shared/Apps и golden fixtures | Hash имён и содержимого всех Python/JSON в Shared, Apps, Tests; add/change/remove инвалидируют cache |
| P2 | Модель могла печатать ESC/C1 terminal sequences | Display-only фильтр в streaming: raw текст для хранения/оценки не изменён |
| P2 | Ограничение вложения 2 MB проверялось после чтения всего файла | Читается не более 2 000 001 байта |
| P3 | Agent history удерживала до 100 полных telemetry records | В списке удерживаются краткие записи; полностью загружаются только выбранные runs |

## Производительность

Измерение start+stop ResourceSampler: 7 повторов, synthetic probe с задержкой
50 ms, interval=5 s. Медиана v0.19.0.0: **101,243 ms**, v0.21.0.0: **0,251 ms**.
Ожидание завершения фонового потока после замера использовалось только для cleanup.
Это накладные расходы клиента, а не прирост model tok/s. Реальный inference speed
не измерялся. Фоновая телеметрия всё ещё создаёт нагрузку на сервер; это не zero-cost
measurement. Последний sample не гарантированно совпадает с моментом завершения.

Не оптимизировались за счёт корректности: fsync checkpoints, verifier, raw outputs,
sampling, prompts, scorer formulas/thresholds/weights, compaction и recovery selection.
Полная сериализация длинного Agent record остаётся потенциальным O(n²) источником
накладных расходов; журналирование с append-only WAL требует отдельной миграции схемы.

## Высокий остаточный риск: старые исполняемые CODE-тесты

В legacy retention/analytics/code execution Python запускается отдельным процессом
с AST-фильтром, timeout и очищенным окружением. Это **не OS sandbox**.
Статический вызов `_retention_code_safety` пропустил обращение к
`numpy.lib.format.open_memmap`, способному работать с файлом. Проверялась только
реакция фильтра; candidate НЕ исполнялся и файл не создавался.

Дополнение deny-list одной функцией не устраняет класс обходов через большие
библиотеки. В этой версии scorer/executor policy сохранена отдельно от transport
исправлений, согласно правилам миграции проекта. До отдельного этапа изоляции
исполняемые CODE-наборы следует запускать лишь в disposable VM без секретов,
общих writable folders и сети. Это ограничение необходимо считать блокирующим
для заявления «безопасное выполнение произвольного модельного кода».

Чатовый python_exec также выполняется с правами пользователя после RUN.
Очищение environment и Python -I не запрещают доступ к диску/сети. Для этой функции
нет CPU/RAM/output/descendant-process OS limits. Не подтверждайте недоверенный код.
Agent Benchmark MVP устроен иначе: generated source проходит ограниченный
интерпретатор, без exec/import/attributes/host APIs; verifier/fixture здесь неизменны.

## Другие ограничения и следующий этап

- HTTP deadline прерывает тело ответа после получения headers. Соединение/headers
  используют idle socket timeout urllib; DNS/header slow-drip не получили полноценный
  process-isolated total deadline. Ограничения размеров могут остановить очень большой
  легитимный ответ; они не изменяют num_predict.
- Atomic replace предотвращает частично записанный JSON, но не блокирует два
  одновременно работающих процесса с одним checkpoint: последняя запись побеждает.
  Межпроцессный run lock — отдельный следующий шаг.
- Hardware probes ограничены по времени, но после stop фоновой задаче может
  потребоваться время, чтобы закончить SSH-вызов. Новые samples после stop не сохраняются.
- Multi-GPU accounting, аппаратные счётчики и long-duration leak/thermal тесты
  требуют настоящего backend. На внешнем generic endpoint hardware может быть неизвестно.
- AST/WhatIf проверки installer не заменяют установку в чистой Windows VM,
  проверку ACL/sshd effective config и внешний тест WAN после reboot.
- Privacy pattern scanner не доказывает отсутствие всех секретов. Бинарные icon assets
  сохранены побайтно. Не публикуйте private development Git history или runtime folders.

## Проверка и неизменность эксперимента

Сохранённый набор: 210 legacy regression + 31 Agent + 23 hardening = 264 теста.
В v0.20.0.0 добавлены 22 UX-теста: прежний набор — 286. GPU-набор добавляется поверх него. Сборка релиза требует прохождения
полного набора в UTF-8 и принудительном cp1251; manifest создаётся только после gates.
Release gates: compile, Run-Tests.ps1, forced cp1251, PowerShell parse,
startup integration/cache, source/staged privacy, manifest/ZIP hashes.
Новые сетевые проверки используют только временный HTTP server на loopback.
Task fixture/verifier, видимые benchmark prompts и scorer functions не изменены.
Ollama options/payload generation и native/recovery attribution сохранены.

Реальные Ollama/llama.cpp, WAN disconnect/reboot и установка сервера в этом аудите
не тестировались. Публичная публикация не выполнялась.
