# ADR-0002: Legacy Schema Compatibility

**Статус:** Accepted  
**Дата:** 2026-09-26

## Контекст

Существуют benchmark results, checkpoints, tested profiles, custom prompts, Agent artifacts и GPU artifacts с `local-llm-*` identifiers. Переименование schema IDs уничтожит воспроизводимость, если будет выполнено in-place.

## Решение

1. Все известные legacy schemas читаются read-only.
2. BULL никогда не изменяет legacy artifact на месте.
3. Migration создаёт новый artifact рядом или в явно выбранной папке.
4. Новый artifact содержит source basename, source SHA-256, source schema и migration version.
5. Неизвестные поля legacy artifact сохраняются в compatibility envelope либо migration блокируется.
6. Checkpoint продолжается только engine, который доказал совместимость с его runtime contract.
7. При сомнении checkpoint анализируется read-only и завершается старой версией приложения.
8. Legacy schema IDs не переименовываются внутри исходных файлов.

## Поддерживаемый минимум

- benchmark config v3;
- benchmark spec v9;
- benchmark record v12;
- benchmark summary v11;
- benchmark checkpoint v9;
- tested profile v1;
- prompt index v2;
- user benchmark v1;
- Agent config/run v1;
- GPU experiment v1.

Полная политика приведена в `Docs/BULL_COMPATIBILITY_MATRIX.md`.

## Resume policy

Read compatibility не означает resume compatibility.

Для resume должны совпасть:

- checkpoint schema;
- prompt/test hashes;
- scorer/runtime policy fingerprints;
- model availability и digest rules;
- backend kind;
- plan identity;
- producer compatibility declaration.

`force` не используется для обхода неизвестного изменения семантики.

## Отклонённые варианты

### Переименовать все schema IDs автоматически

Отклонено: ломает hashes и происхождение результата.

### Поддерживать только последний формат

Отклонено: противоречит назначению воспроизводимого benchmark.

### Всегда разрешать resume

Отклонено: может смешать разные runtime semantics в одном результате.

## Последствия

- compatibility readers остаются отдельным модулем;
- migration tests используют immutable golden artifacts;
- support window документируется;
- удаление legacy reader требует major-version policy.

