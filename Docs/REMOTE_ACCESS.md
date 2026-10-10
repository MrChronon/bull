# BULL v0.29.0.1 — удалённый доступ

## Коротко

Публичная сборка не знает адресов серверов и не пытается подключаться к ним автоматически. По умолчанию Client использует локальный Ollama на `127.0.0.1:11434`.

В v0.29.0.1 рекомендуемый путь для уже настроенного OpenSSH —
**Подключения → Подключиться по SSH-алиасу**. Достаточно ввести `Host` из
`%USERPROFILE%\.ssh\config`; BULL безопасно разрешает его через `ssh -G`.
Если alias ещё не создан, используйте **Как создать SSH-ключ и алиас** или
`Docs/SSH_QUICKSTART.md`.

Ручной путь — **Подключения → Настроить сервер вручную**. Мастер просит адрес,
пользователя и путь к уже разрешённому приватному ключу,
получает публичный Ed25519 ключ и требует независимо проверенный fingerprint.
Подтверждение показанного сетью ключа без сверки небезопасно. Локальная Ollama не нужна.
Для Windows-сервера fingerprint можно получить локальной командой:
`ssh-keygen -lf C:/ProgramData/ssh/ssh_host_ed25519_key.pub -E sha256`.

Альтернативный импорт через **Настройки соединения программы → Импортировать Connection JSON** использует два файла:

1. `*.connection.json` - публичное описание endpoint и SSH host key;
2. private SSH key - секрет, который остаётся только у владельца Client.

Endpoint и путь к ключу после импорта хранятся в `Runtime\connections.json`. Папка `Runtime` не включается в релиз.
По явному выбору пользователя запись также сохраняется в `%LOCALAPPDATA%\BULL\connections`.
Эта приватная адресная книга переживает замену билда; ключ не копируется. Новый билд
предлагает сохранённые серверы, но не выбирает и не подключает их сам. Для переноса
старых настроек используйте «Перенести из старой версии»; для удаления только личной
записи — «Забыть сервер». Это не отзывает ключ на самом сервере.

## Быстрый импорт OpenSSH alias

Быстрый мастер принимает только безопасное имя `Host` без пробелов и опций. Команда
`ssh -G -- ALIAS` запускается без shell и не подключается к серверу. Из результата
используются только `HostName`, `User`, `Port`, существующий приватный
`IdentityFile` и пути `UserKnownHostsFile`.

Затем BULL получает публичный Ed25519 host key. Если он уже совпадает с записью в
OpenSSH `known_hosts` — в том числе hashed entry — доверие переиспользуется. Иначе
нужно вручную ввести fingerprint, независимо полученный на Server. В обоих случаях
BULL создаёт собственный закреплённый `known_hosts` и дальше использует
`StrictHostKeyChecking=yes`, `BatchMode=yes` и `IdentitiesOnly=yes`.

`ProxyCommand` и `ProxyJump` отклоняются: их молчаливое преобразование изменило бы
маршрут и модель доверия. Алиас только с ключом в `ssh-agent`, но без существующего
`IdentityFile`, также нельзя импортировать автоматически. Добавьте явный
`IdentityFile` или используйте ручной мастер.

## Рекомендуемая WAN-схема

```text
BULL Client
  -> Tailscale / WireGuard overlay
  -> Windows OpenSSH Server :22
  -> SSH local forwarding
  -> 127.0.0.1:11434 Ollama
```

Преимущества overlay-сети:

- обычно не нужен входящий port forwarding;
- она практичнее при динамическом адресе и NAT;
- Ollama не публикуется в Интернет;
- доступ можно отозвать на уровне overlay-сети и SSH key.

`-InstallTailscale` ставит официальный Windows-клиент через `winget`. Авторизация устройства и ACL tailnet выполняются отдельно: installer не получает и не хранит Tailscale credentials.

## Direct SSH

Direct route поддерживается как advanced вариант:

```text
Client -> public DNS/IP:SSH-port -> router/NAT -> Windows OpenSSH:22
```

Он требует публичного адреса или корректного port forwarding. При CGNAT входящее подключение может быть невозможно. Не открывайте наружу `11434` или `8080`.

### Белый IP и роутер

BULL не поддерживает автоматическое изменение настроек роутера. Это намеренное ограничение: UPnP/NAT-PMP не используются, а программа не хранит пароль администратора роутера. Для direct-маршрута настройте одно явное правило вручную:

```text
TCP <PUBLIC_IP>:<EXTERNAL_SSH_PORT> -> <SERVER_LAN_IP>:22
```

В Windows Firewall открывается только `LocalPort 22`. Порт в connection JSON — внешний порт роутера; он может отличаться от внутреннего `22`. Не создавайте правила для `11434`, `11435`, `8080` или RDP. Ollama и llama.cpp должны оставаться на loopback удалённого компьютера.

Перед настройкой NAT закрепите постоянный LAN-адрес за Server через DHCP reservation. Иначе после перезагрузки роутер может выдать другой адрес и перенаправление перестанет работать.

Подготовьте OpenSSH и модели на сервере отдельно. BULL не разворачивает сервер
и не меняет NAT. В настройках соединения клиента укажите внешний SSH-порт и
проверьте fingerprint независимым каналом.

Перед сохранением правила на роутере запустите на Server от администратора read-only проверку:

```powershell
.\Server\Test-BULL-RemoteReadiness.ps1 `
  -Route direct `
  -PublicHost <PUBLIC-IP-OR-DNS> `
  -EndpointPort 48222
```

Проверка блокирует готовность, если `sshd` не работает автоматически, password/keyboard login не отключены, Windows Firewall не разрешает SSH или inference-порт слушает не только loopback. Она ничего не изменяет.

### KeeneticOS / Keenetic Hopper

Названия пунктов могут немного отличаться между версиями KeeneticOS:

1. В разделе домашней сети найдите компьютер Server и закрепите за ним постоянный IPv4-адрес.
2. Откройте **Сетевые правила → Переадресация**.
3. Создайте правило для входящего интерфейса провайдера, протокол `TCP`.
4. Внешний порт: выбранный `EndpointPort`, например `48222`.
5. Устройство назначения: Server; внутренний порт: `22`.
6. Сохраните правило и убедитесь, что удалённое управление самим роутером не использует тот же внешний порт.

Не включайте DMZ для Server и не публикуйте все его порты. Если провайдер использует двойной NAT, bridge/modem-router перед Keenetic тоже должен перенаправлять выбранный TCP-порт либо работать в bridge-режиме.

### Обязательная внешняя проверка

Проверяйте direct SSH с другого подключения — например, раздав мобильный интернет на Client. Проверка публичного IP из домашнего Wi-Fi зависит от NAT loopback и может дать ложный отрицательный результат. После SSH-проверки запустите `/backend doctor`, затем короткий chat и только потом длительный benchmark.

## Подготовка Client key

```powershell
.\Client\New-BULL-ClientKey.ps1
```

С passphrase это интерактивная команда. Для полностью автоматизированной изолированной среды есть явный override:

```powershell
.\Client\New-BULL-ClientKey.ps1 -NoPassphrase -NonInteractive
```

Private key нельзя отправлять администратору или добавлять в репозиторий. На Server передаётся только `.pub`.

## Подготовка сервера

Сервер администрируется отдельно от BULL. Установите Ollama или llama.cpp,
настройте OpenSSH, отдельного пользователя и вход по ключам.
Inference-порты должны оставаться на loopback; для SSH настройте ограниченное
правило firewall и при необходимости overlay VPN. BULL не устанавливает эти
компоненты и не меняет настройки машины.

`Server/Test-BULL-RemoteReadiness.ps1` выполняет read-only проверку Windows-узла.
Для Connection JSON можно использовать существующий экспорт параметров;
приватный ключ передаётся отдельно и никогда не публикуется.

## Импорт на Client

Через интерфейс:

```text
Настройки соединения программы
-> Импортировать Connection JSON
```

Или:

```text
/connection import
```

Укажите connection JSON, затем private key. Client:

1. отвергает secret/password/token fields;
2. проверяет host, user и ports;
3. вычисляет fingerprint из `host_public_key` и сравнивает с JSON;
4. создаёт отдельный pinned `known_hosts`;
5. включает `StrictHostKeyChecking=yes`, `IdentitiesOnly=yes` и BatchMode для direct route;
6. сохраняет connection только в `Runtime`.

Выбор:

```text
/connection list
/connection use my-lab
/remote reconnect
```

Возврат к моделям этого компьютера:

```text
/connection local
```

После переключения уже запущенного Client выполните `/remote reconnect` или перезапустите приложение.

## Отзыв доступа

Для отзыва:

1. удалите соответствующую строку public key из server `authorized_keys`;
2. удалите устройство/ACL из overlay-сети, если применимо;
3. удалите local connection из `Runtime\connections.json` либо весь `Runtime`;
4. при компрометации private key создайте новую пару и новый connection access.

Connection JSON сам по себе не даёт доступ: нужен private key, соответствующий server-side public key.

## Диагностика

```text
/connection
/remote test
/backend doctor
/status
```

На Server:

```powershell
Get-Service sshd
Get-NetFirewallRule -Name OpenSSH-Server-In-TCP
Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 11434
ollama list
```

Для direct-маршрута дополнительно проверьте:

- WAN-адрес в Keenetic совпадает с выданным провайдером белым адресом;
- Server сохранил закреплённый LAN-IP;
- правило направляет внешний TCP-порт именно на внутренний `22`;
- connection JSON содержит тот же public host и внешний порт;
- тест выполняется не из той же домашней Wi-Fi-сети.

Если host key сервера законно изменился после переустановки, создайте новый connection bundle на доверенном Server и импортируйте его заново. Не отключайте `StrictHostKeyChecking` для обхода предупреждения.
