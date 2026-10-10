# ADR-0004: Benchmark Pack Registry

**Статус:** Accepted  
**Дата:** 2026-09-26

## Контекст

Встроенный каталог нельзя бесконечно расширять внутри центрального клиента. Benchmark content, runners и scorers должны иметь независимые версии, provenance и trust policy.

## Решение

BULL вводит registry versioned benchmark packs.

### Pack содержит

- manifest;
- cases или deterministic generator;
- runner type;
- scorer/verifier references;
- category taxonomy;
- license и provenance;
- minimum engine version;
- gold tests;
- documentation;
- maturity state.

### Maturity states

- `experimental`;
- `candidate`;
- `stable`;
- `deprecated`;
- `retired`.

### Trust boundary

- обычный pack является data-first и не исполняет произвольный Python;
- built-in scorer/verifier выбирается из registry по ID;
- внешний executable plugin устанавливается отдельно и требует явного доверия;
- pack path, archive members и referenced files проходят path validation;
- remote auto-install запрещён по умолчанию;
- dataset license/version/checksum обязательны.

### Identity

Запуск фиксирует:

- pack ID/version;
- case ID/version;
- compiled canonical JSON SHA-256;
- prompt SHA-256;
- generator ID/version/seed;
- scorer ID/version;
- verifier ID/version;
- engine compatibility version.

### Migrations

Обновление case создаёт новую version. Исправление scorer создаёт scorer version и допускает offline rescore только при совместимом prompt/output contract.

## Отклонённые варианты

### Динамически импортировать Python из каждого pack

Отклонено: нарушает security boundary публичного продукта.

### Использовать только один глобальный prompts.json

Отклонено: недостаточно для независимых versions, licenses и runners.

### Копировать все внешние datasets в release

Отклонено: создаёт license, size и contamination risks.

## Последствия

- Chat Core сначала переносится без изменения content;
- авторы получают validate/list/inspect workflow;
- external adapters устанавливаются отдельно;
- result identity не зависит от отображаемого имени pack.

