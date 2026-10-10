# BULL v0.29.0.1 — Pack Library fixes

Current edition: **11 October 2026 stable**, with the 10 October fixes. Read the
[complete correction record](FOLLOWUP_2026_10_10.md), current
[English release notes](en/RELEASE_NOTES.md) / [описание на русском](ru/RELEASE_NOTES.md)
and [roadmap 1.10](BULL_TRANSITION_ROADMAP.md). Live terminal/folder-deletion
and model-inference acceptance remain open after automated release gates.

Documentation synchronized **11 October 2026** without prompt/scorer/runtime
changes. Stable promotion preserves the published ZIP/tag; `main` documentation
records the later status without replacing archive bytes. See
[release readiness](RELEASE_READINESS.md) for portable instructions, current
metadata and the manual acceptance boundary.

## English

- Test packs are accessible directly from Home, including installation,
  ZIP import, selection, removal and Author Workshop.
- Base ZIPs accept a number, comma-separated numbers or `all`. Installing
  several packs does not combine them into a benchmark run.
- The test list returns to benchmark navigation instead of dropping into Chat.
- Windows CPU/RAM use native counters without WMI or administrator rights.
  Missing readings show `N/A`; SSH readings belong to the inference server.
- Checkpoint replacement retries temporary Windows locks. Persistent failure
  stops testing, preserves the previous file and retains a complete recovery
  copy. Resume requires confirmation and writes a new checkpoint.
- The approved rich red startup artwork returns. Current version, active check
  and genuine percentage are displayed separately.
- Startup runs 18 essential checks. The complete 668-check offline suite
  remains mandatory for development and releases; compatibility fixtures remain.
- The terminal bull uses coloured background cells rather than rare font glyphs.
  Without colours, it falls back to an ASCII silhouette; every colour row resets.
- Integrity and connection appear once above Home's six sections, without
  repeated readiness labels. Pack status and read-only browsing belong to
  Model testing and Test settings.
- `Matrix BULL` and `matrix_bull` are recognised in theme settings and environment
  overrides instead of falling back to red. Theme selection is independent of language.
- UTF-8 and console colour support are re-established after startup checks and
  on theme selection; an unavailable output handle cannot retain a stale colour flag.
- BULL Matrix changes terminal styling immediately and uses a matching green
  startup illustration, frame and progress bar on the next launch. Selecting
  BULL Red restores the red variant. Both artwork files pass startup integrity checks.
- Matrix startup includes animated digital rain only along the right edge of the
  artwork. It does not cover the bull or live check panel; it stops when the window
  closes. Quiet checks remain responsive without inventing progress.
- Setup is now `Setup.exe`, with an install-arrow icon and language → theme
  selection before dependencies or packs. The unnecessary introductory phrase is removed.
- Only BULL Red / BULL Matrix remain; high contrast is retired. Theme selection
  also updates owned shortcut icons, preserving foreign links and launch targets.
- Installer launch and shortcuts use one `BULL.exe` and Terminal profile, with
  per-console Consolas fallback. The canonical terminal mark is now 48×24 cells.
  No global font/profile settings change; live clean-install visual acceptance is pending.
- Native launchers are compiled from shipped source during release construction;
  both are unsigned. Approved red/green splash artwork and animation are unchanged.

Existing reports without CPU/RAM retain their original data. Use a fresh
application directory; the shared pack library is retained automatically.
Built-in benchmark prompts and references are unchanged. Language pack 1.0.1/scorer v2 is a separate
correction; historical scorers, including v1, remain unchanged. Chat/runtime and report changes
were independently reviewed. Red/green concept art
is not included as an application theme.

## Русский

- «Наборы тестов» доступны прямо с главной: установка, импорт ZIP, выбор,
  удаление и мастерская автора.
- Базовые ZIP можно установить по номеру, списку номеров или `all`.
  Массовая установка не объединяет наборы в одном прогоне.
- Из списка тестов можно вернуться к меню бенчмарка без перехода в чат.
- CPU/RAM Windows измеряются штатными счётчиками без WMI и прав администратора.
  При отсутствии измерений показано `N/A`; через SSH измеряется сервер модели.
- Запись checkpoint повторяется при временной блокировке Windows. Постоянная
  блокировка останавливает тест: прежний файл и полная копия восстановления
  сохраняются. Resume требует подтверждения и создаёт новый checkpoint.
- Возвращено прежнее красное изображение запуска; версия, текущая проверка
  и реальный процент отображаются отдельными обновляемыми элементами.
- При запуске выполняются 18 обязательных проверок. Полная регрессия из
  668 проверок остаётся обязательной при разработке и сборке релиза.
- Терминальный бык использует цветные фоновые ячейки вместо редких символов шрифта.
  Без цвета выводится ASCII-силуэт; цвет сбрасывается в каждой строке.
- Целостность и соединение показаны один раз над шестью разделами главной,
  без повторов под пунктами. Статус и просмотр наборов находятся в тестировании
  и настройках тестов.
- Названия `Matrix BULL` и `matrix_bull` в настройках темы и переменной окружения
  распознаются как зелёная тема, а не заменяются красной. Выбор темы независим от языка.
- UTF-8 и режим цветов повторно настраиваются после проверки запуска и при выборе
  темы; недоступный вывод не оставляет устаревший флаг включённых цветов.
- BULL Matrix сразу меняет оформление терминала, а при следующем запуске использует
  зелёный загрузочный рисунок, рамку и прогресс. BULL Red возвращает красный вариант.
  Целостность обоих рисунков проверяется при запуске.
- В Matrix-заставке справа движутся цифры и символы. Бык, графики и панель
  проверок остаются читаемыми; при закрытии анимация останавливается. Во время
  тихой проверки окно остаётся отзывчивым, процент не увеличивается сам по себе.
- Установка начинается с `Setup.exe` со стрелкой установки: язык → тема до
  зависимостей и наборов. Ненужная вступительная фраза удалена.
- Остались BULL Red / BULL Matrix; высокая контрастность удалена. Смена темы
  обновляет значки своих ярлыков, не затрагивая чужие ссылки и путь запуска.
- Установщик и ярлыки используют один `BULL.exe` и профиль Terminal; обычная
  консоль — Consolas для своего окна. Канонический знак теперь имеет 48×24 ячейки.
  Глобальные настройки не меняются; визуальная приёмка чистой установки ещё нужна.
- Launchers собираются из поставляемого исходника и не подписаны. Одобренные
  красная/зелёная заставки и анимация сохранены.

Старые отчёты без CPU/RAM сохраняют исходные данные. Распакуйте приложение
в новую папку: общая библиотека наборов используется повторно. Prompts и эталоны
сохранены. Набор языка 1.0.1/scorer v2 исправлен отдельно; исторический v1 сохранён.
Runtime/chat и отчёты изменялись независимыми проверяемыми шагами. Красно-зелёные концепции не
включены в программу как тема.
