# BULL Brand Guide

**Статус:** direction approved for T0; production assets deferred to T1  
**Версия:** 1.0

## 1. Brand core

**Имя:** BULL  
**Расшифровка:** Benchmarking & Usage of Local LLMs  
**Пояснение:** Local LLM Benchmark Lab

Характер бренда:

- точный;
- инженерный;
- уверенный, но не агрессивный;
- открытый и проверяемый;
- локальный и privacy-aware;
- ориентированный на evidence, а не маркетинговый рейтинг.

## 2. Смысл визуального знака

Основной знак объединяет:

- узнаваемую голову быка;
- рога как сравнительные шкалы или benchmark bars;
- минимальные neural/circuit nodes;
- симметрию как символ сопоставимых условий;
- отрицательное пространство и сильный силуэт.

Сгенерированный ранее bitmap является концептуальным направлением, а не production asset. В T1 знак должен быть вручную перерисован и очищен в SVG.

## 3. Запрещённые ассоциации

Не использовать:

- биржевые свечи;
- стрелки роста;
- монеты, валюты и trading charts;
- красный агрессивный бычий маскот;
- оружие, огонь и спортивную агрессию;
- Matrix code rain;
- robot head и generic chat bubble;
- визуальное сходство с Bull/BullSequana и финансовым BULL Text-to-SQL benchmark.

## 4. Цветовая система

Рабочее направление:

- graphite / near-black — основа;
- bright off-white — фон и текст;
- electric cyan-green — интерактивный акцент;
- green — только подтверждённый успех;
- yellow — предупреждение;
- red — ошибка или критическое состояние.

Accent не заменяет текстовый status. Все важные состояния дублируются словами и символами.

Финальные HEX-значения утверждаются в T1 после проверки контраста WCAG AA на поддерживаемых terminal themes и в HTML.

## 5. Typography

- uppercase `BULL` для wordmark;
- современный technical grotesk;
- без декоративных «цифровых» разрывов, ухудшающих чтение;
- subtitle набирается обычным регистром;
- системный UI продолжает использовать надёжные terminal fonts пользователя.

## 6. Обязательные assets T1

- source SVG;
- horizontal wordmark;
- icon-only;
- monochrome black;
- monochrome white;
- light-background variant;
- dark-background variant;
- 16, 32, 64, 128, 256 и 512 px PNG;
- multi-resolution Windows `.ico`;
- favicon;
- GitHub social preview;
- terminal-safe text lockup.

## 7. Acceptance tests T1

- силуэт читается при 16 px;
- wordmark читается при 100% Windows scaling;
- знак работает в одном цвете;
- нет мелких isolated details, исчезающих при rasterization;
- light/dark variants проходят contrast review;
- exact wordmark равен `BULL`;
- первое текстовое упоминание содержит `Local LLM Benchmark Lab`;
- assets не содержат metadata с личными путями или author e-mail;
- SVG не содержит scripts, external URLs или embedded private data.

## 8. Tone of voice

Предпочтительно:

- «наблюдаемый лидер этого прогона»;
- «результаты сопоставимы при указанных условиях»;
- «данных недостаточно для устойчивого ранжирования»;
- «native quality» и «final system quality» объясняются отдельно.

Запрещено:

- «абсолютно лучшая модель»;
- «научно доказано» без соответствующего дизайна эксперимента;
- «полностью безопасно»;
- «поддерживает контекст N» только по заявлению model metadata;
- маркетинговое скрытие recovery или failed contracts.

## 9. Naming examples

Правильно:

- `BULL — Local LLM Benchmark Lab`;
- `BULL v0.28.0.7` после первого полного упоминания;
- `BULL RU Dialogue pack`;
- `bull_llm.evaluation`.

Неправильно:

- `BULL benchmark` в поисковом описании без qualifier;
- Python package `bull`;
- schema `bull-result`;
- `Bull AI Platform`;
- `BULL Trading Benchmark`.

