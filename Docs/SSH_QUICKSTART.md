# BULL v0.28.0.6 — быстрый вход по SSH-алиасу

Этот сценарий подходит, если обычная команда `ssh bull-home` уже подключается к
компьютеру с Ollama по ключу. После настройки в BULL достаточно открыть
**Подключения → Подключиться по SSH-алиасу** и ввести `bull-home`.

## 1. Создать отдельный ключ на Client

Из корня BULL выполните:

```powershell
.\Client\New-BULL-ClientKey.ps1
```

Скрипт создаёт пару `bull_access` / `bull_access.pub`. Приватный файл
`bull_access` остаётся только на Client. На Server передаётся только `.pub`.
Passphrase безопаснее; перед запуском BULL такой ключ можно один раз добавить в
`ssh-agent`:

```powershell
Set-Service ssh-agent -StartupType Automatic
Start-Service ssh-agent
ssh-add "$env:USERPROFILE\.ssh\bull_access"
```

Изменение службы может потребовать PowerShell от администратора.

## 2. Разрешить ключ на Server

Для нового Windows-узла используйте установщик BULL от администратора:

```powershell
.\Install-BULL-v0.28.0.6.ps1 `
  -Role Server `
  -AuthorizedKeyPath C:\Transfer\bull_access.pub `
  -PublicHost <SERVER-IP-OR-DNS>
```

Для уже настроенного OpenSSH добавьте содержимое `bull_access.pub` одной строкой
в `C:\Users\<SERVER_USER>\.ssh\authorized_keys` и сохраните корректные ACL.
Приватный ключ на Server не копируется.

## 3. Создать алиас OpenSSH

Создайте `%USERPROFILE%\.ssh\config` или добавьте в него:

```sshconfig
Host bull-home
    HostName 203.0.113.10
    User <SERVER_USER>
    Port 22
    IdentityFile ~/.ssh/bull_access
    IdentitiesOnly yes
```

Для доступа через роутер укажите внешний SSH-порт. Не указывайте здесь порт
Ollama. `11434` остаётся на loopback Server и передаётся внутри SSH-туннеля.

Быстрый мастер поддерживает прямые алиасы. Конфигурации с `ProxyJump` или
`ProxyCommand` требуют ручного сценария BULL, потому что после импорта приложение
использует собственный закреплённый tunnel и не должно молча менять маршрут.

## 4. Проверить OpenSSH до BULL

```powershell
ssh bull-home
```

При первом соединении независимо получите fingerprint на Server:

```powershell
ssh-keygen -lf C:/ProgramData/ssh/ssh_host_ed25519_key.pub -E sha256
```

Сравните его с запросом OpenSSH. Не подтверждайте неизвестный ключ вслепую.

## 5. Подключить BULL

1. Откройте **Подключения**.
2. Выберите **Подключиться по SSH-алиасу**.
3. Введите `bull-home`.
4. Проверьте найденные `HostName`, `User`, `Port`, `IdentityFile` и fingerprint.
5. Сохраните подключение для следующих версий или только для текущего bundle.

BULL вызывает `ssh -G` без shell, принимает только безопасное имя алиаса и не
читает содержимое приватного ключа. Если отсканированный host key уже совпадает с
записью OpenSSH `known_hosts`, повторный ручной ввод fingerprint не нужен. Если
совпадения нет, BULL требует независимую проверку. Затем приложение создаёт свой
per-connection `known_hosts` и всегда использует `StrictHostKeyChecking=yes`.

## Диагностика

- **IdentityFile не найден:** добавьте явный `IdentityFile` в alias; одного ключа
  только в агенте для быстрого импорта недостаточно.
- **Fingerprint не совпал:** ничего не сохраняйте; проверьте адрес и ключ Server.
- **Connection refused:** запустите `sshd`, проверьте порт/VPN/NAT и Windows Firewall.
- **SSH работает, Ollama нет:** на Server проверьте
  `Invoke-RestMethod http://127.0.0.1:11434/api/version`.
- **ProxyJump/ProxyCommand:** используйте ручной мастер или отдельный прямой/VPN
  alias; BULL намеренно не импортирует исполняемые SSH-команды.

Никогда не публикуйте `.ssh`, приватные ключи, `Runtime`, `known_hosts` или
connection vault. Не открывайте в Интернет Ollama `11434`, llama.cpp `8080` или
GPU Lab `11435`.
