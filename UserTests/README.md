# UserTests / Пользовательские тесты

Put reusable personal tasks in this directory. BULL discovers them when you
open **Compare models → My tasks and prompts → Task from UserTests**.

- Copy `simple_prompt.example.txt` to `my_task.txt` for a prompt-only test.
  BULL runs it on every selected model and reports speed, but does not invent a
  quality score. Compare the answers manually.
- Copy `structured_task.example.yaml` to `my_task.yaml` when the answer has
  deterministic facts or a terminal JSON contract that BULL can verify.

Read `Docs/USER_TESTS.md` before writing YAML criteria. Unsupported or invalid
files are isolated and shown as validation errors; they do not execute code.

## Русский

Помещайте в эту папку собственные повторяемые задачи. BULL находит их через
**Сравнить модели → Мои задачи и промпты → Задача из UserTests**.

- Скопируйте `simple_prompt.example.txt` в `my_task.txt`, если нужен тест с
  одним промптом. BULL запустит его на всех выбранных моделях и измерит
  скорость, но не станет придумывать оценку качества. Ответы сравниваются
  вручную.
- Скопируйте `structured_task.example.yaml` в `my_task.yaml`, если ответ
  содержит проверяемые факты или финальный JSON-контракт.

Перед созданием YAML-критериев прочитайте `Docs/ru/BENCHMARKS.md`. Неподдерживаемые
или некорректные файлы изолируются и показываются как ошибки проверки; код из
них не выполняется.
