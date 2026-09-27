"""Human-oriented terminal surface; saved results remain available offline."""
from __future__ import annotations

from pathlib import Path
from copy import deepcopy

from ..i18n import localized_print as print

from .contracts import AgentConfig, label, load_config, load_run, save_config
from .ollama import OllamaAgentBackend
from .reports import export_csv, save_report, terminal_comparison, terminal_summary
from .runner import run_benchmark
from .tasks import REQUIREMENTS, TASK_ID


def configure(core, backend, previous=None):
    models = backend.models()
    if not models:
        raise ValueError("На backend нет доступных моделей.")
    core.ui_header("AGENT CONFIGURATION", "Agent Benchmark > Настройки")
    core.show_models(models, current=previous.model if previous else None)
    choice = core.read_user_input("Номер модели (0 = отмена) › ").strip()
    if choice == "0":
        return previous
    model, _ = core.resolve_model_choice(choice, models)
    if not model:
        raise ValueError("Выберите номер модели из списка.")
    info = backend.describe(model)
    print(f"Контекст активной модели: {info.get('running_context') or 'нет данных'}; "
          f"num_ctx в профиле: {info.get('profile_context') or 'не указан'}")
    config = deepcopy(previous) if previous else AgentConfig(model=model)
    config.model = model
    def ask_number(title, default, convert=int):
        text = core.read_user_input(f"{title} [{default}] › ").strip()
        return convert(text) if text else default
    config.name = core.read_user_input(f"Название конфигурации [{config.name}] › ").strip() or config.name
    config.backend_context = ask_number("Backend context", config.backend_context)
    default_limit = min(config.agent_context, max(1024, config.backend_context - config.sampling["num_predict"]))
    config.agent_context = ask_number("Agent context limit", default_limit)
    print(f"Резерв: {config.reserve} токенов")
    if core.read_user_input("Sampling: Enter = оставить текущие; 1 = изменить › ").strip() == "1":
        for key, value in config.sampling.items():
            config.sampling[key] = ask_number(key, value, int if key in ("seed", "top_k", "num_predict") else float)
    config.timeout_seconds = ask_number("Лимит времени задачи, секунд", config.timeout_seconds)
    config.request_timeout_seconds = ask_number("Таймаут одного запроса, секунд", config.request_timeout_seconds)
    config.max_steps = ask_number("Максимум шагов", config.max_steps)
    current = "2" if config.context_strategy == "stop" else "1"
    strategy = core.read_user_input(f"При заполнении контекста: 1 = compaction; 2 = остановить [{current}] › ").strip() or current
    if strategy not in ("1", "2"):
        raise ValueError("Выберите 1 или 2.")
    config.context_strategy = "stop" if strategy == "2" else "compact"
    if core.read_user_input("Инструкции: Enter = оставить текущие; 1 = изменить › ").strip() == "1":
        config.rules_name = core.read_user_input(f"Название правил [{config.rules_name}] › ").strip() or config.rules_name
        config.rules_version = core.read_user_input(f"Версия правил [{config.rules_version}] › ").strip() or config.rules_version
        for key, title in (("system_prompt", "System prompt"), ("instructions", "Agent instructions"),
                           ("project_rules", "Project rules"), ("tool_safety_rules", "Tool safety rules")):
            print(f"{title}: {label(getattr(config, key))}")
            value = core.read_user_input("Новый текст одной строкой; Enter = оставить › ")
            if value.strip():
                setattr(config, key, value)
    config.validate()
    for warning in config.warnings():
        print(warning)
    return config


def configure_simple(core, backend, previous=None):
    """A draft screen, not a sequence of mandatory expert questions."""
    draft = deepcopy(previous) if previous else None
    while True:
        core.ui_header('Настройки агентского теста', 'Тесты / Агентская задача / Настройки')
        if draft:
            print(f'Модель: {label(draft.model)} · лимит {draft.timeout_seconds} с · {draft.max_steps} шагов')
            print(f'Контекст модели {draft.backend_context}; агента {draft.agent_context}; резерв {draft.reserve}.')
        else:
            print('Для первого запуска выберите модель. Остальные параметры уже имеют стандартные значения.')
        core.ui_menu_item('1', 'Выбрать модель')
        core.ui_menu_item('2', 'Контекст и лимиты', 'Размер контекста, время задачи, число шагов')
        core.ui_menu_item('3', 'Расширенные параметры', 'Sampling, инструкции, таймаут запроса и стратегия контекста')
        core.ui_menu_item('4', 'Применить стандартные настройки', 'Сбросить параметры выбранной модели; нужна отдельная проверка перед запуском')
        core.ui_menu_item('S', 'Сохранить настройки', 'Тест пока не запускается')
        core.ui_menu_item('0', 'Отменить изменения')
        choice = core.read_user_input('Выбор › ').strip().casefold()
        if choice == '0': return previous
        if choice in ('s', 'ы'):
            if draft:
                draft.validate()
                return draft
            print('Сначала выберите модель.'); continue
        try:
            if choice == '1':
                models = backend.models()
                if not models: raise ValueError('На сервере нет доступных моделей.')
                core.show_models(models, current=draft.model if draft else None)
                raw = core.read_user_input('Номер модели (0 — назад) › ').strip()
                if raw in ('', '0'): continue
                model, _ = core.resolve_model_choice(raw, models)
                if not model: raise ValueError('Выберите модель из списка.')
                if draft: draft.model = model
                else: draft = AgentConfig(model=model)
            elif choice in ('2', '3', '4') and draft is None:
                print('Сначала выберите модель.')
            elif choice == '2':
                changed = deepcopy(draft)
                print('Enter оставляет текущее значение; 0 отменяет редактирование.')
                fields = [('backend_context', 'Контекст модели, токенов'), ('agent_context', 'Порог контекста агента, токенов'),
                          ('timeout_seconds', 'Время всей задачи, секунд'), ('max_steps', 'Максимум шагов')]
                cancelled = False
                for key, title in fields:
                    raw = core.read_user_input(f'{title} [{getattr(changed,key)}] › ').strip()
                    if raw == '0': cancelled = True; break
                    if raw: setattr(changed, key, int(raw))
                if not cancelled:
                    changed.validate(); draft = changed
            elif choice == '3':
                # Preserve the complete advanced editor and its validation contracts.
                draft = configure(core, backend, draft)
            elif choice == '4':
                if core.read_user_input('Сбросить контекст, sampling, инструкции и лимиты? 1 — да; Enter — нет › ').strip() == '1':
                    draft = AgentConfig(model=draft.model)
            else:
                print('Выберите 1–4, S или 0.')
        except (ValueError, TypeError) as exc:
            print('Настройки не применены:', label(str(exc)))


def show_config(config, detailed=False):
    print(f"Конфигурация: {label(config.name)} | {label(config.model)}")
    print(f"Backend {config.backend_context} | Agent {config.agent_context} | Reserve {config.reserve}")
    if detailed:
        print("Sampling: " + ", ".join(f"{key}={value}" for key, value in config.sampling.items()))
        print(f"Rules: {label(config.rules_name)} v{label(config.rules_version)} | "
              f"SHA256 {config.public_snapshot()['instructions_sha256'][:16]}")
    print(f"Задача: {TASK_ID} | {config.max_steps} шагов | {config.timeout_seconds} с | {config.context_strategy}")


def history(core, storage):
    paths = sorted(Path(storage).glob("*/result.json"), reverse=True)
    available = []
    for path in paths[:100]:
        try:
            run = load_run(path)
            available.append((path, {key: run[key] for key in ("status", "timestamp", "config")}))
        except (ValueError, OSError, KeyError):
            continue
    if not available:
        print("Сохранённых Agent runs пока нет.")
        return None
    for index, (path, run) in enumerate(available, 1):
        state = "прерван / ещё работает" if run["status"] == "running" else run["status"]
        print(f"{index}. {label(run['timestamp'])} | {label(run['config']['model'])} | {label(state)}")
    raw = core.read_user_input("Номера через запятую для сравнения; 0 = назад › ").strip()
    if not raw or raw == "0":
        return None
    indices = list(dict.fromkeys(int(x.strip()) - 1 for x in raw.split(",")))
    if not indices or len(indices) > 12 or any(i < 0 or i >= len(available) for i in indices):
        raise ValueError("Выберите от 1 до 12 существующих запусков.")
    selected = [(available[i][0], load_run(available[i][0])) for i in indices]
    runs = [x[1] for x in selected]
    terminal_comparison(runs)
    action = core.read_user_input("1 = HTML; 2 = CSV; 3 = повторить первый run с начала; Enter = назад › ").strip()
    if action in ("1", "2"):
        report = Path(storage) / ("comparison.html" if action == "1" else "comparison.csv")
        if action == "1":
            save_report(report, runs)
            core.open_benchmark_visual_report(report)
        else:
            export_csv(report, runs)
        print("Сохранено:", report)
    elif action == "3":
        path, run = selected[0]
        config = load_config(path.parent / "configuration.private.json")
        # Repeat is a new clean attempt. An interrupted parent is explicit.
        interrupted = run["status"] in ("running", "interrupted", "backend_error", "failed", "timeout")
        return config, run["run_id"], "manual_retry" if interrupted else None
    return None


def menu(core, runtime_guard):
    storage = core.appdir() / "Benchmarks" / "Agents"
    config_path = core.appdir() / "Runtime" / "agent_configuration.json"
    config = None
    if config_path.exists():
        try:
            config = load_config(config_path)
        except (OSError, TypeError, ValueError):
            print("Сохранённая конфигурация недействительна. Создайте новую.")
    pending = None
    while True:
        try:
            core.ui_header("Агентская задача", "Тесты / Agent Benchmark",
                           "Агент исправляет код на чистой копии тестового проекта")
            if config:
                show_config(config)
            core.ui_menu_item("1", "Запустить агентскую задачу", "Проверить текущую конфигурацию на чистой копии проекта")
            core.ui_menu_item("2", "Настройки теста", "Выбрать модель; остальное — по желанию")
            core.ui_menu_item("3", "Посмотреть задачу", "Требования и независимая проверка результата")
            core.ui_menu_item("4", "История и сравнение", "Результаты, повтор запуска, HTML и CSV; доступны офлайн")
            core.ui_menu_item("0", "Назад", "К предыдущему экрану")
            choice = "1" if pending else core.read_user_input("Выбор [0-4] › ").strip()
            if choice == "0":
                return
            if choice == "3":
                print(REQUIREMENTS)
                print("MVP: Python-задача в ограниченном интерпретаторе. Произвольные Gradle/npm/shell команды не поддерживаются.")
                core.read_user_input("Enter = назад › ")
                continue
            if choice == "4":
                pending = history(core, storage)
                if pending:
                    config = pending[0]
                continue
            if choice not in ("1", "2"):
                continue
            if not runtime_guard("Agent Benchmark"):
                pending = None
                continue
            backend = OllamaAgentBackend(core)
            if config is None or choice == "2":
                config = configure_simple(core, backend, config)
                if config:
                    save_config(config_path, config)
                if choice == "2" or config is None:
                    continue
            show_config(config)
            print("Агент может менять только файлы тестовой задачи. Ctrl+C: остановка или ручное вмешательство.")
            if core.read_user_input("1 — запустить тест; Enter или 0 — назад › ").strip() != "1":
                pending = None
                continue
            def progress(phase, step, run):
                ctx = run["contexts"][-1]["tokens"]
                checks = sum(x.get('category') == 'build_test_failure' for x in run['errors'])
                print(f"Шаг {step}/{config.max_steps} · контекст ≈{ctx} · "
                      f"tools {len(run['tool_calls'])} · неудачных проверок кода {checks}", flush=True)
            def control(category):
                print(f"Запрос остановлен: {category}. Измерения сохранены.")
                answer = core.read_user_input("1 = повторить запрос; 2 = скорректировать задачу; 3 = ответить на вопрос; 0 = завершить › ").strip()
                if answer == "1" and runtime_guard("повтора Agent request"):
                    return "retry"
                if answer in ("2", "3"):
                    message = core.read_user_input("Текст для агента (в телеметрию не сохраняется) › ")
                    return {"kind": "manual_correction" if answer == "2" else "user_clarification", "message": message}
                return "stop"
            parent, intervention = (pending[1], pending[2]) if pending else (None, None)
            pending = None
            result, path = run_benchmark(config, backend, storage, progress, control,
                                         parent_run_id=parent, initial_intervention=intervention)
            terminal_summary(result)
            save_report(path.with_name("report.html"), [result])
            print("Результат:", path)
            while True:
                core.ui_menu_item('1', 'Открыть наглядный HTML-отчёт')
                core.ui_menu_item('2', 'Все показатели в окне программы')
                core.ui_menu_item('0', 'Назад к агентским тестам')
                action = core.read_user_input('Выбор › ').strip()
                if action in ('', '0'): break
                if action == '1': core.open_benchmark_visual_report(path.with_name('report.html'))
                elif action == '2': terminal_comparison([result])
                else: print('Выберите 1, 2 или 0.')
        except (KeyboardInterrupt, EOFError):
            return
        except Exception as exc:
            # Errors from user config/catalog are bounded and stripped of terminal controls.
            from .contracts import classify_error
            print("Agent Benchmark: " + (label(str(exc)) if isinstance(exc, ValueError) else classify_error(exc)))
            pending = None
            core.read_user_input("Enter = назад › ")
