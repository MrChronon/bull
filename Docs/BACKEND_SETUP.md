# BULL v0.28.0.4 — установка платформы

## Роли

Один bundle разворачивается в трёх вариантах:

| Роль | Client / Lab | OpenSSH Server | Ollama | Типичный сценарий |
| --- | --- | --- | --- | --- |
| Client | да | нет | optional local | ноутбук оператора |
| Server | файлы bundle остаются доступны | да | да | выделенный inference node |
| AllInOne | да | только если передан `.pub` | да | тесты и модели на одном ПК |

Запуск:

```text
Install-BULL-v0.28.0.4.cmd
```

CMD включает установку недостающего Python через `winget`. PowerShell entry point позволяет автоматизацию:

```powershell
.\Install-BULL-v0.28.0.4.ps1 -Role Client -InstallDependencies
.\Install-BULL-v0.28.0.4.ps1 -Role Server -AuthorizedKeyPath C:\Transfer\access.pub -PublicHost <VPN-IP-or-DNS>
.\Install-BULL-v0.28.0.4.ps1 -Role Server -Route direct -EndpointPort 48222 -AuthorizedKeyPath C:\Transfer\access.pub -PublicHost <PUBLIC-IP-or-DNS>
.\Install-BULL-v0.28.0.4.ps1 -Role AllInOne -InstallDependencies
```

Server и AllInOne требуют администратора; installer сам запрашивает UAC в интерактивном режиме. Server требует `.pub`-ключ и завершается без него. AllInOne без ключа не включает OpenSSH и входящее firewall-правило.

## Что входит и чего нет

Bundle содержит Client, Benchmark Lab, общие схемы, installers, тесты и документацию. Python, OpenSSH, Ollama и optional Tailscale ставятся из Windows/официальных package sources.

LLM weights не включены: они велики, зависят от hardware и имеют отдельные лицензии. После установки:

```powershell
ollama pull <model-name>
ollama list
```

## Client

Если `ssh ALIAS` уже работает по ключу, выберите **Подключения → Подключиться по
SSH-алиасу** и введите только alias. Для новой конфигурации используйте
**Настроить сервер вручную** или встроенную инструкцию по созданию ключа. Не нужно сначала
запускать локальную Ollama или вручную редактировать JSON. После настройки сервер
можно запомнить для следующих билдов в личной папке пользователя (без копирования
приватного ключа). Подробные шаги и перенос старой версии: `Docs/UI_GUIDE.md`.
Расширенное управление llama.cpp остаётся в **Настройки и помощь → Расширенные настройки движка**.

Client может использовать:

- локальный Ollama на `127.0.0.1:11434`;
- remote Ollama через SSH tunnel;
- llama.cpp как loopback `external` server;
- legacy managed remote llama.cpp workflow.

Локальный запуск:

```text
/connection local
```

Remote import:

```text
/connection import
```

## Server

Основной script:

```powershell
.\Server\Install-BULL-Node.ps1 `
  -InstallOllama `
  -AuthorizedKeyPath C:\Transfer\access.pub `
  -PublicHost my-node.example `
  -Route overlay
```

Он выполняет только следующие системные изменения:

1. ставит Windows OpenSSH Server/Client capability;
2. включает automatic `sshd`;
3. проверяет/создаёт firewall rule только для TCP 22;
4. добавляет конкретный client public key;
5. включает глобальный publickey-only режим и добавляет `Match User` block в `sshd_config` после backup и `sshd -t`;
6. ставит Ollama при `-InstallOllama`;
7. задаёт machine variable `OLLAMA_HOST=127.0.0.1:11434`;
8. запускает Ollama скрыто, если loopback listener отсутствует;
9. создаёт public connection JSON.

Для `-Route direct` значение `-EndpointPort` — внешний TCP-порт роутера. На Server `sshd` продолжает слушать внутренний порт `22`, поэтому правило NAT имеет вид `TCP <EndpointPort> -> <SERVER_LAN_IP>:22`. Установщик выводит эту схему, но намеренно не включает UPnP и не меняет роутер автоматически.

Installer не открывает firewall для `11434` или `8080`.

## AllInOne

AllInOne устанавливает Client и локальный Ollama, затем сохраняет `target_mode=local`. Без `.pub`-ключа это loopback-only узел: SSH и входящее правило не включаются. Если ключ передан явно, дополнительно выполняется Server-этап для других клиентов. Для chat/benchmark на этом же ПК SSH в любом случае не используется.

## llama.cpp

v0.28.0.4 сохраняет существующий llama.cpp backend. Публичные defaults безопасны:

```json
{
  "enabled": false,
  "transport": "external",
  "base_url": "http://127.0.0.1:8080",
  "server_path": "",
  "models_dir": ""
}
```

Для локального llama-server запустите его на loopback и используйте `transport=external`. Для managed remote workflow явно настройте `remote_ssh`, `server_path` и `models_dir`. Public release не содержит путей конкретной машины.

## Проверка после установки

Client:

```text
/backend doctor
/selftest
/model
```

Developer/release validation:

```powershell
.\Run-Tests.ps1
```

Server:

```powershell
Get-Service sshd
Get-NetFirewallRule -Name OpenSSH-Server-In-TCP
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/version
```

## Перенос

На новом Client переносите:

- чистый BULL v0.28.0.4 bundle;
- нужный connection JSON;
- private key отдельным защищённым каналом, если это ваш key;
- при необходимости пользовательские `model_profiles.json` и tested profiles.

Не переносите в публичную копию:

- `Runtime`;
- `Chats`;
- `Benchmarks`;
- `Exports`;
- private keys;
- API tokens;
- debug logs.

`Build-Release.ps1` проверяет это автоматически перед ZIP.
