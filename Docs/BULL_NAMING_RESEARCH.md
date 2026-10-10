# BULL Naming Research

**Статус:** preliminary, non-legal  
**Дата проверки:** 2026-09-26  
**Область:** web, academic benchmarks, GitHub/PyPI-visible names и public product names

## 1. Проверяемое имя

- BULL
- Benchmarking & Usage of Local Language Models
- BULL — Benchmark Lab
- `bull_llm`
- `bull-llm`
- `bull-benchmark-lab`

## 2. Найденные пересечения

### BULL Text-to-SQL benchmark

Имя BULL уже используется для финансового Text-to-SQL dataset/benchmark. Его публичная страница называет продукт `Bull 1.0 — A Big Bench for Text-to-SQLs in Financial Analysis`. Связанная работа FinSQL описывает BULL как практический финансовый Text-to-SQL benchmark с английской и китайской версиями.

Источники:

- [Bull 1.0 Benchmark](https://bull-text-to-sql-benchmark.github.io/)
- [FinSQL paper](https://arxiv.org/abs/2401.10506)

Вывод: нельзя позиционировать наш проект только как `BULL benchmark` без уточнения `BULL Benchmark Lab`.

### PyPI package `bull`

Имя `bull` занято существующим Python-проектом с 2014 года.

Источник: [bull on PyPI](https://pypi.org/project/bull/)

Вывод: distribution и CLI не должны называться просто `bull`.

### Bull / BullSequana AI

Bull является существующим технологическим брендом; BullSequana используется для AI/HPC hardware и AI platform.

Источник: [BullSequana AI Platform](https://www.bull.com/en/products/ai/bullsequana-ai-platform)

Вывод: визуальная идентичность не должна имитировать corporate Bull/BullSequana, а полное имя должно явно указывать на оценку локальных моделей.

## 3. Не найдено при предварительном поиске

Не найдено заметного проекта с точной расшифровкой `Benchmarking & Usage of Local Language Models` или точным полным названием `BULL — Benchmark Lab`.

Это не означает юридическую доступность имени. Web search не заменяет поиск по классам товарных знаков и юрисдикциям.

## 4. Решение по disambiguation

| Поверхность | Решение |
|---|---|
| Логотип | `BULL` допустимо |
| Первое упоминание | `BULL — Benchmark Lab` |
| Расшифровка | `Benchmarking & Usage of Local Language Models` |
| Python namespace | `bull_llm` |
| PyPI candidate | `bull-llm`, только после повторной проверки и reservation |
| Repository candidate | `bull-benchmark-lab` |
| CLI candidate | `bull-llm` |
| Schema prefix | `bull-llm-*` |
| Bundle | `BULL-vX.Y.Z-Bundle` |
| Benchmark packs | `bull_ru_dialogue`, `bull_local_system`, не `bull` |

## 5. Поисковое позиционирование

Обязательные metadata keywords:

- local language model benchmark;
- offline LLM evaluation;
- Ollama benchmark;
- llama.cpp benchmark;
- Russian LLM evaluation;
- local inference performance;
- agent benchmark;
- reproducible model evaluation.

Следует избегать доминирования слов finance, trading, stock, market и bullish, чтобы бренд не воспринимался как финансовый инструмент.

## 6. Оставшиеся проверки

До публичного BULL Bridge:

- проверить GitHub repository/org names непосредственно перед rename;
- проверить доступность `bull-llm` в package registries непосредственно перед публикацией;
- проверить домены, если будет выбран публичный сайт;
- выполнить поиск товарных знаков в целевых юрисдикциях и классах software/SaaS;
- проверить финальный логотип на визуальное сходство;
- зарезервировать выбранные identifiers одним согласованным выпуском.

## 7. Risk decision

Техническое решение: **GO WITH QUALIFIER**.

`BULL` сохраняется как display brand по решению владельца. Во всех неоднозначных технических и поисковых контекстах используется qualifier `BULL Benchmark Lab` или `bull_llm`. Юридическая clearance остаётся обязательным внешним gate перед коммерческим публичным релизом и не считается выполненной этим документом.

