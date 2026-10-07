# ADR-0001: Product Boundaries

**Статус:** Accepted  
**Дата:** 2026-09-26

## Контекст

BULL объединяет рабочий чат, Benchmark Lab, Agent Benchmark, GPU Lab, backend transports и shared schemas. При дальнейшем росте монолитное владение этими функциями создаёт риск скрытого изменения benchmark behavior и смешивания пользовательской работы с экспериментами.

## Решение

BULL является одним продуктом с несколькими независимыми приложениями поверх общего ядра.

### Benchmark Lab

Владеет benchmark content, planning, execution matrix, scoring, checkpoint/resume, statistics и reports.

Benchmark Lab не может:

- молча применять tested profile к рабочему Client;
- менять пользовательские чаты;
- считать client recovery native-quality метрикой;
- хранить private connection credentials в benchmark artifact.

### Client

Владеет chat sessions, FAST/THINK/ULTIMATE workflows и явным импортом tested profile.

Client не может:

- определять benchmark score;
- менять benchmark pack;
- публиковать пользовательскую сессию без явного действия.

### Agent Lab

Владеет agent tasks, tools, trajectories и isolated verifiers. Он использует core runtime и artifact contracts, но не CHAT score.

### GPU Lab

Владеет hardware experiments и performance telemetry. Он не изменяет рабочий backend и не объявляет performance workload quality benchmark.

### Shared core

Содержит contracts, validation, fingerprints, storage primitives и backend interfaces. Shared core не импортирует UI.

## Причины

- отдельные приложения развиваются с разной скоростью;
- benchmark result должен оставаться объяснимым;
- пользовательские настройки не должны становиться частью эксперимента неявно;
- Agent и GPU требуют других trust boundaries;
- общий core сохраняет единые schemas и fingerprints.

## Отклонённые варианты

### Удалить Client и оставить только benchmark

Отклонено: Client нужен для практической проверки выбранного профиля и является существующей функцией продукта.

### Оставить один главный Python-файл

Отклонено: затрудняет ownership, tests и независимое versioning.

### Немедленно разделить проект на несколько repositories

Отклонено на переходном этапе: увеличивает риск несовместимых релизов. Сначала стабилизируются internal package boundaries.

## Последствия

- UI может оставаться единым launcher, но вызывает независимые application services;
- artifacts каждого Lab имеют отдельные schema IDs;
- tested profile передаётся только через versioned explicit import;
- удаление legacy monolith возможно только после parity tests.

