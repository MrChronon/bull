"""One route: Tests > Experimental GPU Lab. Rare path overrides stay advanced."""
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import uuid

from ..i18n import localized_print as print
from ..http_transport import decode_object
from ..storage import atomic_json
from ..presentation import terminal_text as safe_terminal_text
from .contracts import WORKLOADS, validate_config
from .transport import Worker, Session
from .runner import new_result, execute
from .reports import terminal, export
from .messages import explain


def ask(core, text): return core.read_user_input(text + ' › ').strip()


def choose(core, rows, title, many=False):
    print(title)
    for i, row in enumerate(rows, 1): core.ui_menu_item(str(i), safe_terminal_text(str(row)), '')
    while True:
        raw = ask(core, 'Номера через запятую, 0 — назад' if many else 'Номер, 0 — назад')
        if raw in ('0', ''): return []
        try:
            nums = [int(n.strip()) for n in raw.split(',')]
            if not nums or len(set(nums)) != len(nums) or (not many and len(nums) != 1) or any(n < 1 or n > len(rows) for n in nums): raise ValueError()
            return [n - 1 for n in nums]
        except ValueError: print('Выберите номера из списка без повторов.')


def read_private(root):
    path = root / 'Runtime/gpu_lab_settings.private.json'
    if not path.is_file(): return {}
    if path.stat().st_size > 16384: raise ValueError('GPU settings too large')
    data = decode_object(path.read_text(encoding='utf-8'))
    if set(data) - {'executable', 'models_dir'} or any(not isinstance(v, str) for v in data.values()): raise ValueError('Invalid GPU settings')
    return data


def configure(core, worker, private, inventory):
    for g in inventory:
        print(safe_terminal_text(f"{g['name']} · {g['memory_mib']} MiB · driver {g['driver']} · {g['uuid']}"))
    print('P100 требует подходящего CUDA-драйвера и направленного охлаждения: это не тест разгона.')
    print('Остановите другие задания/модели на выбранных GPU самостоятельно. Приложение их не завершает.')
    indices = choose(core, [g['name'] + ' · ' + g['uuid'][-8:] for g in inventory], 'Какие карты исследовать?', many=True)
    if not indices: return None
    selected = [inventory[i]['uuid'] for i in indices]
    combinations = [[u] for u in selected]
    if len(selected) > 1: combinations.append(selected)
    labels = [' + '.join(next(g['name'] for g in inventory if g['uuid'] == u) for u in ds) for ds in combinations]
    print('1 — сравнить каждую отдельно и все вместе; 2 — выбрать конкретные конфигурации; 0 — назад')
    mode = ask(core, 'Режим')
    if mode == '2':
        choices = choose(core, labels, 'Какие конфигурации запускать?', many=True)
        if not choices: return None
        combinations = [combinations[i] for i in choices]
    elif mode != '1': return None
    print('Для чтения каталога будет временно запущена отдельная Ollama, без загрузки модели и без скачивания.')
    if ask(core, '1 — прочитать каталог; 0 — отмена') != '1': return None
    with Session(worker, selected[:1], private) as session:
        catalog = session.api('/api/tags').get('models', [])
        models = sorted({r['name'] for r in catalog if r.get('name') and 'cloud' not in r['name'].casefold()})
    if not models:
        print('В каталоге этого Windows/SSH-пользователя нет моделей. Проверьте папку моделей в дополнительных настройках GPU Lab.'); return None
    choices = choose(core, models, 'Модели (они должны уже быть установлены на сервере)', many=True)
    if not choices: return None
    keys = list(WORKLOADS) + ['custom']
    choices_w = choose(core, [WORKLOADS[k][0] if k in WORKLOADS else 'Мой промпт (одна строка)' for k in keys], 'Сценарии производительности — без скорера качества', many=True)
    if not choices_w: return None
    cfg = dict(models=[models[i] for i in choices], devices=combinations, workloads=[keys[i] for i in choices_w])
    if 'custom' in cfg['workloads']: cfg['custom_prompt'] = ask(core, 'Введите промпт (сохранится только в приватном JSON результата)')
    print('1 — стандарт: 3 повтора, контекст 4096, выход ≤512 токенов; 2 — быстрый: 1 повтор; 3 — настроить; 0 — назад')
    preset = ask(core, 'Настройки')
    if preset == '2': cfg['repeats'] = 1
    elif preset == '3':
        for key, label, default in [('repeats','Повторов (1..10)',3), ('context','Контекст (4096..32768)',4096), ('tokens','Выход токенов (32..2048)',512), ('timeout','Таймаут запроса (30..1800 секунд)',600)]:
            cfg[key] = int(ask(core, f'{label}; Enter = {default}') or default)
    elif preset != '1': return None
    return validate_config(cfg)


def menu(core):
    root = Path(core.__file__).resolve().parent
    while True:
        core.clear_console(); core.ui_header('Экспериментальная GPU Lab', 'Тесты / GPU Lab', 'Windows + Ollama · выбор реальных карт · отдельно от рейтинга качества')
        core.ui_menu_item('1', 'Новый эксперимент', 'Карты → модели → сценарии → план → запуск')
        core.ui_menu_item('2', 'Результаты и продолжение', 'Таблицы, HTML; после сбоя начать незавершённую пару заново')
        core.ui_menu_item('3', 'Пути на сервере', 'Дополнительно: нестандартная ollama.exe или папка моделей')
        core.ui_menu_item('0', 'Назад', 'Вернуться к тестам')
        choice = ask(core, 'Выбор')
        if choice in ('0', ''): return
        try:
            private = read_private(root)
            if choice == '3':
                print('Пути относятся к выбранному серверу (или этому ПК в локальном режиме). Не вводите команды.')
                print('Enter оставляет автоопределение. Значения хранятся только в Runtime этого билда.')
                private = {k: ask(core, text).strip('"') for k, text in [('executable','Полный путь к ollama.exe'), ('models_dir','Полный путь к каталогу моделей Ollama')]}
                if ask(core, '1 — сохранить; 0 — отмена') == '1': atomic_json(root / 'Runtime/gpu_lab_settings.private.json', private)
                continue
            if choice == '2':
                paths = sorted((root / 'Benchmarks/GPU').glob('*/result.private.json'), reverse=True)
                if not paths: print('Результатов пока нет.'); ask(core, 'Enter — назад'); continue
                choices = choose(core, [p.parent.name for p in paths[:40]], 'Эксперименты')
                if not choices: continue
                path = paths[choices[0]]
                if path.stat().st_size > 64 * 1024 * 1024: raise ValueError('GPU result exceeds 64 MiB')
                result = decode_object(path.read_text(encoding='utf-8')); terminal(result)
                print('HTML:', export(result, path.parent))
                if result['status'] == 'completed' or ask(core, '1 — продолжить; 0 — назад') != '1':
                    ask(core, 'Enter — назад'); continue
                with Worker(core) as worker: result = execute(worker, result, path, private, lambda t: print(safe_terminal_text(t)))
            elif choice == '1':
                with Worker(core) as worker:
                    inventory = worker.rpc('inventory')['gpus']
                    cfg = configure(core, worker, private, inventory)
                    if cfg is None: continue
                    result = new_result(cfg, inventory)
                    count = len(result['jobs'])
                    print(f'План: {len(cfg["models"])} моделей × {len(cfg["devices"])} GPU-конфигураций × {len(cfg["workloads"])} сценариев × {cfg["repeats"]} повторов = {count * 2} запросов.')
                    print('Каждая пара: новая Ollama → первый запрос → повтор того же промпта → остановка только своего процесса.')
                    print('У обеих GPU включён запрос распределения; фактическое размещение будет проверено. Ctrl+C — пауза.')
                    if ask(core, '1 — запустить нагрузку; 0 — отмена') != '1': continue
                    directory = root / 'Benchmarks/GPU' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8])
                    path = directory / 'result.private.json'
                    result = execute(worker, result, path, private, lambda t: print(safe_terminal_text(t)))
            else: continue
            terminal(result); print('JSON (приватный):', path); print('HTML:', export(result, path.parent))
        except KeyboardInterrupt: print('Отменено. Сохранённые результаты остаются в Benchmarks/GPU.')
        except Exception as exc:
            print(safe_terminal_text('GPU Lab: ' + explain(exc)))
            print('Рабочее подключение не менялось. Проверьте Windows, nvidia-smi, SSH и пути Ollama в пункте 3.')
        ask(core, 'Enter — назад')
