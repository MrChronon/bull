# BULL security policy / Политика безопасности

## English

Security fixes are reviewed for the current development/release line. Older
versions have no promised backport schedule. v0.29.0.1 is a pre-release;
offline gates are not a security certification or live acceptance.

Do not disclose vulnerabilities in public Issues/Discussions. Use GitHub's
**Report a vulnerability** on the repository Security page **when enabled**.
If it is unavailable, ask the owner to enable a private reporting channel
without posting exploit details, credentials or affected private data. No
private mailbox or guaranteed response time is advertised by this repository.

Initially provide the version, component, required conditions, impact and a
sanitized minimal reproduction. Share additional details only through an
agreed private channel. Test only systems/data you own or are authorized to test.

### Operational boundaries

- Never expose Ollama/llama.cpp inference ports directly to the Internet;
  use the documented pinned SSH route for remote access.
- Pack ZIPs are data-only and hash-checked. Hashes are not publisher signatures.
- Engine-owned executable checks and chat tools are **not an OS sandbox**;
  use a disposable VM for untrusted generated code.
- Raw outputs, checkpoints, logs and author ZIPs may contain private content.
  Prefer reviewed share-safe artifacts, not a full configured installation.
- Native launchers are unsigned. Verify the matching release SHA-256; a checksum
  detects changes but does not by itself authenticate a publisher.

Read the [security model](Docs/en/SECURITY.md),
[installation](Docs/en/INSTALLATION.md) and [acceptance limits](Docs/RELEASE_READINESS.md).

## Русский

Исправления безопасности рассматриваются для текущей линии разработки/релиза.
График backport для старых версий не обещается. v0.29.0.1 — pre-release;
автотесты не являются сертификатом безопасности или live-приёмкой.

Не раскрывайте уязвимости в публичных Issues/Discussions. Используйте
**Report a vulnerability** на странице Security, **если этот канал включён**.
Если его нет, попросите владельца включить приватный канал, не публикуя exploit,
учётные данные или приватные сведения. Репозиторий не объявляет адрес приватной
почты и не гарантирует сроки ответа.

Сначала сообщите версию, компонент, условия, влияние и минимальное обезличенное
воспроизведение. Подробности передавайте только по согласованному приватному
каналу. Проверяйте лишь собственные системы или системы с явным разрешением.

### Границы эксплуатации

- Не открывайте inference-порты Ollama/llama.cpp в Интернет; используйте pinned SSH.
- Наборы — только данные; hashes не заменяют подпись издателя.
- Исполняемые проверки движка и tools чата **не являются OS-песочницей**.
- Raw-результаты, checkpoints, логи и ZIP автора могут содержать приватные данные.
- Launchers не подписаны. SHA-256 обнаруживает изменение файла, но сама
  по себе не удостоверяет издателя.

Читайте [модель безопасности](Docs/ru/SECURITY.md),
[установку](Docs/ru/INSTALLATION.md) и [границы приёмки](Docs/RELEASE_READINESS.md).
