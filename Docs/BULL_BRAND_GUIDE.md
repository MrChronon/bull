# BULL Brand Guide

**Статус:** действующий бренд BULL; канонический источник и производные релиза  
**Версия:** 1.1

## 1. Brand core

**Имя:** BULL  
**Расшифровка:** Benchmarking & Usage of Local Language Models
**Пояснение:** BULL Benchmark Lab

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

Канонический raster master — `Assets/Brand/bull-logo-canonical.png`. Хеш и
crop geometry закреплены в `brand-lock.json`. Геометрия не перерисовывается.
SVG-контейнеры содержат только локальные PNG, без внешних ресурсов.

## 3. Запрещённые ассоциации

Не использовать:

- биржевые свечи;
- стрелки роста;
- монеты, валюты и trading charts;
- агрессивный бычий маскот; красная фирменная палитра допустима;
- оружие, огонь и спортивную агрессию;
- Matrix code rain в основном бренде; тема BULL Matrix допустима;
- robot head и generic chat bubble;
- визуальное сходство с Bull/BullSequana и финансовым BULL Text-to-SQL benchmark.

## 4. Цветовая система

Рабочее направление:

- graphite / near-black — основа;
- bright off-white — фон и текст;
- BULL Red `#FF3C52` — фирменный акцент по умолчанию;
- BULL Matrix — альтернативная зелёная тема;
- green — только подтверждённый успех;
- yellow — предупреждение;
- красная диагностическая надпись ERROR/FAIL — ошибка; акцент меню не является статусом.

Accent не заменяет текстовый status. Все важные состояния дублируются словами и символами.

Успешная запись всегда зелёная независимо от темы. Версионный splash — отдельное
PNG-окно; он не меняет фон терминала.
В теме BULL Matrix загрузочный рисунок, рамка и прогресс используют зелёную
палитру. `startup-hero-matrix.png` сохраняет композицию красного `startup-hero.png`;
версия и текущая проверка отображаются отдельным живым слоем, не внутри рисунка.
Только Matrix-заставка содержит цифровой дождь на правом краю: спокойные зелёные
столбцы цифр и символов, без перекрытия быка, графиков и информационной панели.
Анимация использует ограниченный слой из 45 символов; при закрытии окна
останавливается. Красный бренд, меню и логи остаются без цифрового дождя.

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
- первое текстовое упоминание содержит `BULL Benchmark Lab`;
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

- `BULL — Benchmark Lab`;
- `BULL v0.29.0.1` после первого полного упоминания;
- `BULL RU Dialogue pack`;
- `bull_llm.evaluation`.

Неправильно:

- `BULL benchmark` в поисковом описании без qualifier;
- Python package `bull`;
- schema `bull-result`;
- `Bull AI Platform`;
- `BULL Trading Benchmark`.

