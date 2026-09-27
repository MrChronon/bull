# Переход со старых сборок на BULL v0.24.0.0

## Что изменилось

Публичное имя продукта теперь **BULL — Benchmark Lab**. Launchers, installer,
служебные scripts и единственный импортный namespace используют BULL.

| Было | Стало |
|---|---|
| старый основной launcher | `BULL-v0.24.0.0.cmd` |
| старый Benchmark Lab launcher | `BULL-Benchmark-Lab-v0.24.0.0.cmd` |
| старый Agent Lab launcher | `BULL-Agent-Lab-v0.24.0.0.cmd` |
| старый installer | `Install-BULL-v0.24.0.0.cmd` |
| старый Python namespace | `Shared.bull_llm` |

## Что не изменилось

- benchmark prompts и scorers;
- inference/runtime pipeline;
- schema identifiers and versions of existing artifacts;
- factory backend defaults and SSH trust model;
- checkpoint rule: completed runs remain saved, interrupted run starts again.

## Безопасное обновление

1. Распакуйте BULL в новую папку; не распаковывайте поверх старой версии.
2. Запустите `Run-Tests.ps1`.
3. Запустите `BULL-v0.24.0.0.cmd`.
4. При необходимости откройте **Подключения → Дополнительно → Перенести из
   старой версии**. Перенос всегда требует явного выбора.
5. Проверяйте SSH fingerprint независимо на сервере.
6. Старую папку удаляйте только после проверки чатов, подключений и результатов.

## Совместимость автоматизации

С v0.24 старые aliases и внутренний legacy namespace не входят в bundle. Обновите
пути запуска и imports на BULL. Совместимость сохранена на уровне чтения прежних
JSON artifacts, а не через дублирующие исполняемые файлы или Python packages.

## Legacy artifacts

`bull_llm.compatibility.read_legacy_artifact()` только читает и классифицирует
поддерживаемый JSON. Он не изменяет исходный файл, не выполняет silent migration и
не разрешает resume checkpoint. Правила перечислены в `BULL_COMPATIBILITY_MATRIX.md`.
