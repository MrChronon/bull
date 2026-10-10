# BULL Extended Core 1.0.0

## English

Four existing tasks: funnel reasoning, exact-day retention, analytics evidence
and Python debugging. The prompts, reference data, output instructions, scorer
configuration and generation budgets retain their previous contracts.

This ZIP-ready pack contains data only, not executable plugins. It references
BULL's existing engine-owned scorers. Retention and Python debugging evaluate
model-generated code: the application's code-execution permission gate still
applies. Use a disposable VM for untrusted model code; this pack is not a sandbox.

Do not edit an installed version in place. Create a new version with validated
hashes and gold fixtures when changing a task or its criteria.

## Русский

Четыре существующих задания: анализ воронки, retention на точный день,
проверка выводов аналитики и отладка Python. Тексты, эталоны, инструкции
формата, настройки скореров и бюджеты генерации сохраняют прежние контракты.

Набор содержит только данные, а не исполняемые плагины. Проверки retention
и отладки Python оценивают код, созданный моделью: разрешение приложения на
выполнение кода по-прежнему обязательно. Для недоверенного кода используйте
одноразовую виртуальную машину; этот набор не является песочницей.

Не редактируйте установленную версию. Изменения задания или критериев
должны выпускаться новой версией с проверенными хешами и эталонными ответами.
