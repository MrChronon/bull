# BULL v0.29.0.0 — Pack Library

[English release notes](en/RELEASE_NOTES.md) · [Описание релиза на русском](ru/RELEASE_NOTES.md)

Independent optional ZIP packs, persistent library, one exact version per run,
selected-case coverage, editable author sources and complete private run snapshots.

Независимые необязательные ZIP-наборы, общая библиотека, одна версия на прогон,
выбор заданий, редактируемые исходники и полные приватные снимки.

## Measurement compatibility / Совместимость измерений

Built-in benchmark prompts, scorers and runtime inference/recovery behavior are
unchanged. Existing base tasks are distributed as optional packs; moving their
definitions does not introduce a new quality metric. Model-native quality and
client-assisted recovery remain separate. Compare runs only when the exact pack
version, selected tasks and generation settings are compatible.

Базовые промпты, скореры и поведение генерации/восстановления не изменены.
Перенос заданий в необязательные наборы не создаёт новую метрику качества.
Качество самой модели и восстановление средствами клиента оцениваются отдельно.
Сопоставлять прогоны следует при совместимых версиях наборов, выбранных заданиях
и параметрах генерации.

The matching archive checksum and RELEASE_MANIFEST.json define the verified
release payload. GitHub publication is a separate explicit operation.
