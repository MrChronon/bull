# BULL v0.28.0.7 — Исправление сравнения Ollama-профилей

Benchmark Lab теперь сравнивает модели с их Ollama Modelfile, не принимая
унаследованные различия sampler за ошибку строгого сравнения. Встроенные prompts,
scorers, recovery и inference runtime не менялись.

- Profile-owned различия sampler фиксируются отдельно в evidence.
- Контекст, threads, лимит ответа, reasoning, recovery и prompt остаются строгими.
- План перед запуском сначала читает `/api/show`, поэтому показывает реальные
  параметры профиля.
- Релиз проходит 400 offline regression checks.

Перед выбором источника sampling прочитайте [«Бенчмарки»](BENCHMARKS.md).
Публичный bundle не содержит модели, чаты, benchmark results, runtime state,
частные подключения, ключи, tokens, endpoints и локальные логи.
