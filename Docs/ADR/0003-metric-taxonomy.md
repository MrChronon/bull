# ADR-0003: Metric Taxonomy

**Статус:** Accepted  
**Дата:** 2026-09-26

## Контекст

Один headline score не способен корректно представить качество ответа, соблюдение структуры, recovery, latency, hardware cost и безопасность. Смешивание этих величин создаёт ложные выводы о модели.

## Решение

Новые BULL records используют независимые namespaces.

### `quality.native`

Содержательная оценка первого ответа модели до recovery, finalizer или переписывания клиентом.

### `quality.assisted`

Содержательная оценка выбранного финального ответа после явно разрешённой помощи системы.

### `contract`

- generation completed;
- structural completion;
- terminal JSON validity;
- exact schema;
- task completed.

### `runtime`

- load duration;
- TTFT;
- prompt processing;
- generation duration;
- wall-clock duration;
- tokens/s;
- retry timing.

### `resources`

- CPU/RAM;
- GPU utilization/VRAM;
- temperature;
- power/energy, если источник надёжен;
- unavailable measurements как `null`.

### `recovery`

- reason;
- attempted strategy;
- result selection;
- client retries;
- transport retries;
- human intervention.

### `reliability`

- completion rates;
- checkpoint/resume correctness;
- duplicate prevention;
- cross-seed stability;
- fault-injection outcomes.

### `security`

Отдельные policy и boundary outcomes. Не включаются в общий CHAT score.

### `human`

Blind preference, rubric labels и comments. Не заменяются автоматически LLM judge.

## Агрегация

- универсальный общий score отсутствует;
- category scores допустимы внутри однородного pack;
- weighted decision profile определяется пользователем и маркируется как user-defined;
- confidence intervals и sample count показываются рядом с aggregate;
- recovery никогда не повышает `quality.native`;
- format failure не стирает корректное содержание, но отражается в `contract`;
- critical semantic failure может ограничивать semantic score по versioned rubric.

## LLM-as-a-judge

LLM judge допускается только как явная вспомогательная метрика с judge fingerprint, A/B order swap, повторной оценкой, disagreement и human-gold calibration.

## Последствия

- terminal и HTML reports строятся из одного summary;
- сравнение показывает несколько осей;
- Pareto является диагностикой с uncertainty, а не итоговым рейтингом;
- старые headline fields читаются через compatibility mapping, но не теряют исходное значение.

