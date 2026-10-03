# BULL v0.28.0.0 — модель безопасности

[Безопасность на русском](ru/SECURITY.md) · [Security in English](en/SECURITY.md)

## Результат аудита v0.28.0.0

v0.27 сохраняет границу BULL Evidence. `*_evidence_private.json`
содержит исходные records и считается приватным; `*_evidence_share_safe.json`
строится по allow-list полей и проходит автоматический privacy audit. Миграция
legacy artifacts создаёт новый файл и не переписывает источник. Имена моделей
остаются пользовательскими метаданными и требуют просмотра перед публикацией.

Пользовательские YAML-тесты используют безопасное ограниченное подмножество:
без tags, anchors, aliases, regex и исполняемого кода; действуют лимиты размера,
числа тестов и критериев. Это не делает сами prompts доверенными и не превращает
keyword checks в семантический verifier. `.txt` всегда требует ручной оценки.

См. `AUDIT_v0.28.0.0.md`. Предыдущий hardening сохранил блокировку redirects
Ollama, ограничения HTTP bodies,
неверное завершение stream, terminal controls при выводе модели, коллизии временных
файлов и обходы privacy gate через непроверенные форматы/размеры. Server -WhatIf
теперь защищает весь workflow; Windows ACL используют SID, а не локализуемые имена.

Высокий остаточный риск: legacy исполняемые CODE-тесты используют AST deny-list,
не OS sandbox. Статическая проверка обнаружила пропуск файлового API NumPy.
Не запускайте их на машине с секретами для недоверенных outputs; нужна disposable
VM без сети и общих writable folders. Отдельный этап изоляции обязателен перед
заявлениями о безопасном выполнении произвольного generated code. Agent MVP имеет
другую границу — ограниченный интерпретатор. Чатовый python_exec после RUN также
не изолирован от пользовательского диска/сети.

## Границы доверия

SSH-мастер получает ключ через `ssh-keyscan`, но не считает его
доверенным: пользователь должен независимо проверить SHA256 fingerprint на сервере.
Connection JSON импортируется только из доверенного источника после просмотра.
Замена существующего ID с другим endpoint/backend/host key запрещена. Проверка SSH
остаётся строгой; интерфейс не предлагает отключать host-key checking.

Быстрый мастер алиаса вызывает `ssh -G -- ALIAS` без shell и разрешает только
ограниченное имя `Host`. Он импортирует только прямой маршрут с существующим
`IdentityFile`; `ProxyCommand`, `ProxyJump`, option injection и неизвестные tokenized
paths блокируются. Сетевой host key автоматически принимается только при точном
совпадении с уже доверенной записью OpenSSH `known_hosts`, включая hashed host.
Иначе остаётся обязательная независимая проверка fingerprint. После импорта BULL
создаёт собственный per-connection `known_hosts` и не зависит от дальнейшей смены alias.

По отдельному подтверждению метаданные записываются в личную адресную книгу
`%LOCALAPPDATA%/BULL/connections`. Там хранится путь к приватному ключу, но не его
содержимое. Это незашифрованные личные данные: не публиковать и не копировать в ZIP.
Адресная книга не выбирает сервер автоматически. Удаление её записи не является
отзывом доступа: отзывайте ключ в authorized_keys на сервере. Смена SSH host key требует
проверки администратора; не исправляйте ошибку отключением StrictHostKeyChecking.

Agent Benchmark допускает tool calls только к файлам synthetic task, запись — в
pricing.py. Верификатор находится вне workspace и интерпретирует разрешённый AST с
бюджетами; generated source не выполняется через exec/import. Нет shell, network,
attributes или imports. Вердикт модели не считается проверкой успеха.

Agent result хранит метрики и события; аргументы/ответы tools и hidden reasoning
не журналируются. Правила для повторного запуска — отдельный приватный config.
Весь Benchmarks/Agents исключён из релиза. Существующий transport переиспользуется;
redirect на другой Ollama endpoint отвергается до передачи запроса.

```text
untrusted prompt / generated code
  -> BULL Client
  -> local loopback backend OR pinned SSH tunnel
  -> Ollama / llama.cpp on loopback
```

Доверенными считаются пользователь Windows, выбранный bundle, конкретный private key и администрируемый inference node. Model output, attachments, imported JSON и сеть считаются потенциально недоверенными.

## Безопасные defaults

- public target: `local`;
- public Ollama URL: `http://127.0.0.1:11434`;
- все remote profiles выключены;
- remote mode: `manual`;
- в bundle нет endpoint, username, identity path, model path или private key;
- Ollama/llama-server не публикуются в WAN;
- direct SSH использует BatchMode и key-only auth;
- connection import закрепляет SSH host key;
- external non-loopback llama.cpp требует HTTPS и Bearer key по умолчанию;
- tools, generated Python и external file read сохраняют прежние approval gates.

## Connection bundle и private key

`local-llm-connection v1` является публичной конфигурацией, а не секретом. Он содержит SSH host public key и fingerprint. Client вычисляет fingerprint самостоятельно; несовпадение закрывает импорт.

Private key:

- создаётся на Client;
- не копируется в connection JSON;
- не копируется в `backend_settings.json`;
- остаётся в пользовательской `.ssh` или другом выбранном защищённом каталоге;
- его путь записывается только в `Runtime/connections.json`;
- не входит в release ZIP.

Private key рекомендуется защищать passphrase и/или Windows ACL. При компрометации удалите public key на Server и выпустите новую пару.

## SSH host authentication

Server exporter читает реальный OpenSSH host public key и получает SHA-256 fingerprint через `ssh-keygen`. Client записывает отдельный per-connection `known_hosts` и передаёт:

```text
StrictHostKeyChecking=yes
UserKnownHostsFile=<Runtime pinned file>
IdentitiesOnly=yes
```

Это не заменяет безопасную передачу connection JSON. Для особо чувствительной системы сравните fingerprint с Server по независимому каналу.

## Server installer

Server installer требует администратора и публичный ключ разрешённого Client. Без `.pub` он завершается до включения OpenSSH. AllInOne без ключа работает только локально и не создаёт входящее SSH-правило. При удалённой установке Server глобально задаётся `AuthenticationMethods publickey`, а password и keyboard-interactive authentication отключаются для всех SSH-пользователей. Это намеренно влияет на существующие password-only SSH-сценарии машины. Затем installer:

- открывает только TCP 22;
- оставляет Ollama на `127.0.0.1:11434`;
- использует Windows OpenSSH authorized keys;
- для всех SSH-пользователей отключает password и keyboard-interactive authentication;
- проверяет новый `sshd_config` до применения;
- сохраняет одноразовый backup исходного config.

Installer не меняет router/NAT и не авторизуется в overlay-сети от имени пользователя.

## Internet access

Предпочтителен overlay VPN плюс SSH. Direct SSH повышает поверхность атаки и требует:

- key-only account;
- актуальную Windows/OpenSSH;
- ограниченный firewall/router rule;
- мониторинг попыток входа;
- отсутствие exposed `11434`/`8080`.

Direct route использует одно NAT-правило `TCP <external SSH port> -> Server:22`. UPnP/NAT-PMP не используются, DMZ запрещена. Внешний нестандартный порт уменьшает фоновый шум в логах, но не является средством аутентификации: безопасность обеспечивают private key, pinned host key, key-only OpenSSH и обновлённая ОС.

SSH client включает TCP keepalive и bounded ServerAlive-проверки, чтобы быстрее обнаруживать разрыв Интернет-соединения. После разрыва benchmark остаётся в checkpoint и возобновляется с начала только незавершённого run.

Public Ollama API без собственного authentication нельзя выставлять в Интернет.

## Generated code и tools

Сохранены правила v17.2+:

- unknown slash command не попадает в model prompt;
- external file read требует `READ`;
- Python tool требует `RUN`, запускается с `-I`, scrubbed environment и timeout;
- write tool требует `WRITE` и ограничен Workspace;
- benchmark executable scorers используют AST gates, isolated subprocess и scrubbed environment.

Это defense-in-depth, не полноценная OS sandbox. Запускайте Client без административных прав.

## Secrets

Не хранить в репозитории/ZIP:

- SSH private keys;
- `Runtime`;
- API keys/tokens/passwords;
- Chats, Benchmarks, Exports и Workspace;
- `client_debug.log`;
- environment dumps.

External llama Bearer secret хранится только в environment variable `BULL_LLAMA_API_KEY` или явно выбранной переменной.

## Benchmark packs

Benchmark Registry принимает только data-only packs. До inference он проверяет
visibility/root, engine range, license/provenance, taxonomy, case envelope,
allowlisted runner/scorer/verifier IDs, canonical content/gold hashes и lock.
Ссылки, абсолютные пути, `..` и executable extensions отклоняются. Pack не может
импортировать Python или расширить allowlist. Личные packs хранятся только в
`Runtime/BenchmarkPacks` и исключаются из релиза. Проверяйте packs командой
`/bench pack validate` до использования; подробности в
`BENCHMARK_PACK_AUTHORING.md`.

## Release gate

`Build-Release.ps1`:

1. валидирует local/manual public topology;
2. отвергает endpoint/user/key paths в public config;
3. отвергает machine-specific llama paths;
4. исключает runtime directories и common key/access filenames;
5. ищет private-key PEM/OpenSSH markers в payload;
6. ищет high-confidence GitHub/Hugging Face/OpenAI/AWS/Google token patterns;
7. отвергает реальные Windows/POSIX home paths, non-example e-mail, personal markers и timestamped benchmark results;
8. запускает одинаковый privacy audit для source и staged bundle;
9. перепроверяет source/staged manifest hashes;
10. проверяет единственный корень ZIP.

Отдельный запуск выполняется командой `Test-Public-Release.ps1`. Pattern scan снижает риск случайной публикации, но не распознаёт секреты произвольного формата. Перед GitHub release вручную проверьте diff, список файлов ZIP, screenshots, логи и лицензионный статус по `Docs/PUBLIC_RELEASE_CHECKLIST.md`.

## Benchmark HTML report

`*_report.html` является локальным derived artifact и не входит в release bundle. Генератор:

- экранирует model/test/category labels как HTML;
- не копирует prompts, reasoning или полные model answers;
- не использует JavaScript, CDN и внешние URL;
- показывает только агрегаты и безопасные per-run metrics.

Сам файл всё равно может содержать выбранные пользователем имена моделей и измерения частной машины. Не прикладывайте его к публичному issue без просмотра и обезличивания.

Offline rescore не записывает абсолютный путь исходного raw JSON в переносимые результаты: сохраняются basename и SHA-256. Сам raw JSON, score diff и summary всё равно могут раскрывать имена моделей, ответы и измерения, поэтому перед публикацией их нужно проверять вручную.

## Экспериментальная GPU Lab

GPU Lab v1 использует отдельную Ollama с child-only environment, loopback API и
проверкой PID слушателя (на сервере и для локального SSH forwarding). Windows Job Object
с kill-on-close, управляющий EOF/60-секундный lease и mutex ограничивают жизнь процесса.
Это не OS-песочница для самой Ollama: указывайте только доверенный executable;
она работает с правами выбранного Windows/SSH-пользователя. Драйвер и модели также
должны быть доверенными. `result.private.json` и `gpu_lab_settings.private.json`
приватны; release gate запрещает любые `*.private.json`. См. `GPU_LAB.md`.

## Incident response

При утечке private key:

1. удалить его public counterpart из authorized keys;
2. отключить соответствующий overlay device/ACL;
3. выпустить новую пару;
4. создать новый connection bundle, если изменился endpoint/host key;
5. проверить Windows OpenSSH event logs;
6. не публиковать debug/runtime files при создании issue.

При неожиданном host-key warning не отключайте проверку. Остановитесь, подтвердите причину изменения на Server и импортируйте заново доверенный connection bundle.
