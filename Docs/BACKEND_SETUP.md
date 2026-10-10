# Установка и соединение BULL

[Русский: установка](ru/INSTALLATION.md) · [English: installation](en/INSTALLATION.md)

Установщик `Setup.exe` создаёт только клиент BULL. Он последовательно предлагает язык, тему,
наборы тестов, полную внутреннюю регрессию и настройку существующего соединения.
Установка сервера, моделей, OpenSSH Server и firewall в этот процесс не входит.

```powershell
.\Setup.ps1 -Language ru -Theme bull_red -InstallDependencies
.\Setup.ps1 -Language en -Theme matrix_bright -InstallDependencies
```

Язык можно выбрать и без параметра. Python устанавливается через winget только
после отдельного подтверждения. Настройки и отчёты доступны без backend.

Поддерживаются локальная Ollama, сохранённый SSH-сервер, OpenSSH alias,
ручные параметры и существующий llama.cpp backend. Расширенные параметры движка
открываются в пункте 11 настроек соединения. Модели должны быть установлены
в выбранном backend отдельно.

[Подключения RU](ru/CONNECTIONS.md) · [Connections EN](en/CONNECTIONS.md) ·
[Удалённый доступ](REMOTE_ACCESS.md)

Ключи, `Runtime`, `Chats`, `Benchmarks`, debug logs и API tokens приватны
и не входят в публичный релиз.
