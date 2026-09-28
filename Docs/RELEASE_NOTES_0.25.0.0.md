# BULL v0.25.0.0 — BULL Evidence

Дата: 28 сентября 2026 года.

Этап T4 вводит единый доказательный формат benchmark-результатов. Релиз не
меняет CHAT prompts, scorers, recovery или runtime inference pipeline.

Measurement freeze: this release does not change benchmark prompts, scorers,
recovery behavior, or runtime inference options.

## Главное

- новые versioned schemas `bull-benchmark-record@1` и
  `bull-benchmark-summary@1`;
- immutable provenance с hashes engine, spec, prompt/pack, scorer, verifier и
  фактического порядка выполнения;
- launch, effective, observed и profile runtime fingerprints больше не
  смешиваются;
- native quality, assisted quality, contract, runtime, resources, recovery,
  reliability, security и human metrics находятся в отдельных пространствах;
- рядом с прежними файлами сохраняются private evidence record и privacy-audited
  share-safe summary;
- миграция legacy JSON создаёт новую копию и проверяет, что source не изменился;
- offline HTML использует те же summary data, что и terminal, и показывает
  confidence intervals, latency distributions, context curves и category heatmap.

## Новые файлы результата

- `*_evidence_private.json` — полный record с raw runs; не публиковать;
- `*_evidence_share_safe.json` — allow-listed метрики без prompts, raw answers,
  endpoints, e-mail и домашних путей.

Имена моделей сохраняются в share-safe summary, потому что без них сравнение
теряет смысл. Перед публичной отправкой проверьте, не раскрывают ли они вашу
локальную номенклатуру.

## Совместимость

Прежние raw, summary, checkpoint, CSV и tested-profile artifacts продолжают
создаваться. Compatibility layer распознаёт legacy schemas; исходники миграции
никогда не перезаписываются.

## Проверка

Релиз проходит 358/358 offline regressions. Release gate дополнительно проверяет
Python compile, PowerShell parsing, forced cp1251 startup, публичный состав,
manifest hashes и ZIP integrity.

## Известные ограничения

- один run не доказывает общее превосходство модели;
- confidence interval выводится только при достаточной выборке;
- context curve требует нескольких фактически протестированных context points;
- legacy CODE execution и подтверждённый chat `python_exec` не являются OS
  sandbox — используйте disposable VM без секретов и сети для недоверенного кода.
