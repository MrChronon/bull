"""Task-based terminal navigation. Returns commands; never invokes inference itself."""

import base64
from pathlib import Path
import re

from .i18n import localized_print as print


_CHAFA_ASSET = (
    Path(__file__).resolve().parents[2]
    / 'Assets' / 'Brand' / 'bull-mark-chafa-full-30.ansi.b64'
)
_SGR_ESCAPE_RE = re.compile(r'\x1b\[[0-9;:]*m')
_CHAFA_CURSOR_RE = re.compile(r'\x1b\[\?25[hl]')
_TRUECOLOR_RE = re.compile(r'(?P<kind>38|48);2;(?P<r>\d{1,3});(?P<g>\d{1,3});(?P<b>\d{1,3})')

BULL_PIXEL_ART = (
    '       ▗▆            ▆▖',
    '     ▖▇┃▉            ▏┃▇▗',
    '   ▘╵▌▏┃▉            ▏┃▉▍╷▝',
    '   ▏╷▆╵▅╷▅▖▆▆▆▃▄▆▆▆▗▅╷▅╷▆▇▉',
    '    ▄▂▁▁▁▁▚▁▃▉▖▗┈▃▉▚╵▁▁▁▂▄',
    '      ▆▆▆▆┈▇▅╾▋▎▚▅╷╷▆▆▆▆',
    '       ▆▆▌▝▅▃┈▋▍┈▃▆▘▍▆▇',
    '         ▝╵╷▗▎▘▊▉▆╷▁▘',
    '          ▝▃▚┈▁▁┈▚▂▘',
    '           ▋▍━▆▆━▌▍',
    '            ▅▇▁▁▇▅',
)

_startup_mark_shown = False
_WORDMARK = '  B U L L  //  Benchmarking & Usage of Local Language Models'


def _load_chafa_mark():
    """Load the bounded, build-time Chafa render without trusting arbitrary escapes."""
    try:
        encoded = ''.join(_CHAFA_ASSET.read_text(encoding='ascii').split())
        if not encoded or len(encoded) > 30_000:
            return None
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 64 * 1024:
            return None
        rendered = _CHAFA_CURSOR_RE.sub('', raw.decode('utf-8'))
    except (OSError, ValueError, UnicodeError):
        return None

    plain = _SGR_ESCAPE_RE.sub('', rendered)
    # Cursor visibility emitted by Chafa is stripped above. Only SGR colour
    # controls may remain; reject OSC, movement and other terminal controls.
    if '\x1b' in plain or any(ord(char) < 32 and char not in '\r\n' for char in plain):
        return None
    lines = plain.splitlines()
    if not 10 <= len(lines) <= 18 or any(len(line) > 40 for line in lines):
        return None
    return rendered


def _render_text_mark(core):
    core.matrix()
    for row in BULL_PIXEL_ART:
        print(row)
    core.white()


def _theme_chafa_mark(rendered, theme):
    """Keep the canonical Chafa geometry while adapting saturated brand pixels."""
    theme = str(theme or 'bull_brand').strip().casefold()
    if theme == 'bull_brand':
        return rendered
    targets = {
        'matrix_bright': (54, 255, 115),
        'matrix_balanced': (45, 220, 105),
        'matrix_soft': (38, 176, 91),
        'bull_red': (255, 60, 82),
        'classic': (36, 214, 255),
    }
    target = targets.get(theme)
    if target is None:
        return rendered

    def replace(match):
        red, green, blue = (int(match.group(name)) for name in ('r', 'g', 'b'))
        # Preserve the neutral graphite face and background. Only the original
        # saturated turquoise/green brand pixels are recoloured.
        if max(red, green, blue) - min(red, green, blue) < 24:
            return match.group(0)
        intensity = max(red, green, blue) / 255.0
        mapped = tuple(max(0, min(255, round(channel * intensity))) for channel in target)
        return f'{match.group("kind")};2;{mapped[0]};{mapped[1]};{mapped[2]}'

    return _TRUECOLOR_RE.sub(replace, rendered)


def _render_chafa_mark(core):
    rendered = _load_chafa_mark()
    if rendered is None:
        _render_text_mark(core)
        return False
    themed = _theme_chafa_mark(rendered, getattr(core, 'UI_THEME', 'bull_brand'))
    print(themed, end='' if themed.endswith('\n') else '\n')
    return True


def _render_wordmark(core):
    core.white()
    print(_WORDMARK)


def render_startup_mark(core):
    """Draw the full-colour Chafa product mark once, with a safe text fallback."""
    global _startup_mark_shown
    if _startup_mark_shown:
        return False
    _startup_mark_shown = True
    _render_chafa_mark(core)
    _render_wordmark(core)
    print()
    return True


def render_page_mark(core):
    """Draw the canonical Chafa bull and product expansion on every page."""
    _render_chafa_mark(core)
    _render_wordmark(core)


def selection(raw, rows):
    if not str(raw).isdigit():
        return None
    index = int(raw) - 1
    return rows[index] if 0 <= index < len(rows) else None


def pause(core):
    core.read_user_input('\nEnter — назад › ')


def command_menu(core):
    core.ui_header('Команды', 'Главная / Команды', 'Введите команду целиком. Аргументы и пути сохраняют регистр.')
    print('  /model          выбрать модель     /bench         открыть тесты')
    print('  /connection     подключения        /status        состояние чата')
    print('  /help all       все команды        /home          главная')
    print('  /gpu            экспериментальная GPU Lab (Windows + Ollama)')
    print('  Пример: /bench list\n  Здесь вводятся команды, а сообщения модели — в разделе «Чат».')
    while True:
        raw = core.read_user_input('Команда /… (0 — назад) › ').strip()
        if raw in ('0', ''):
            return None
        command = core.normalize_console_command(raw)
        if command.startswith('/'):
            return command
        core.yellow(); print('Начните команду с /, например /help all.'); core.white()


def chat_menu(core):
    while True:
        core.clear_console()
        core.ui_header('Чат', 'Главная / Чат')
        core.ui_menu_item('1', 'Открыть чат', 'Выбрать модель; текущий диалог сохраняется')
        core.ui_menu_item('2', 'Открыть сохранённый диалог', 'Выбрать сессию из истории')
        core.ui_menu_item('0', 'Назад')
        value = core.read_user_input('Выбор › ').strip()
        if value == '1': return 'chat'
        if value == '2': return 'load'
        if value in ('', '0'): return None
        print('Выберите 1, 2 или 0.')


def experimental_menu(core):
    while True:
        core.clear_console()
        core.ui_header('Экспериментальные функции', 'Главная / Дополнительно / Эксперименты')
        print('  Эти режимы полезны для опытных пользователей, но не нужны для обычного сравнения.')
        core.ui_menu_item('1', 'Agent Benchmark', 'Многошаговые задачи с инструментами')
        core.ui_menu_item('2', 'GPU Lab', 'Аппаратные сценарии для Windows + Ollama')
        core.ui_menu_item('3', 'Расширенные настройки движка', 'Ollama, llama.cpp, пути и серверные инструменты')
        core.ui_menu_item('0', 'Назад')
        value = core.read_user_input('Выбор › ').strip()
        if value == '1': return 'agent'
        if value == '2': return '/gpu'
        if value == '3': return core.backend_runtime_menu()
        if value in ('', '0'): return None
        print('Выберите пункт 0–3.')


def more_menu(core):
    while True:
        core.clear_console()
        core.ui_header('Дополнительно', 'Главная / Дополнительно', 'Редкие и экспертные действия')
        core.ui_menu_item('1', 'Сохранённые результаты', 'Посмотреть краткую сводку или открыть HTML')
        core.ui_menu_item('2', 'Язык и внешний вид', 'Язык интерфейса, BULL, Matrix, красная и контрастная темы')
        core.ui_menu_item('3', 'Состояние текущей сессии', 'Сохранённые настройки; live-метрики только при соединении')
        core.ui_menu_item('4', 'Как пользоваться', 'Короткий маршрут и справка')
        core.ui_menu_item('5', 'Команды для опытных', 'Точные /bench и служебные команды')
        core.ui_menu_item('6', 'Экспериментальные функции', 'Agent Benchmark, GPU Lab и настройки сервера')
        core.ui_menu_item('0', 'Назад')
        value = core.read_user_input('Выбор › ').strip()
        if value == '1': return '/bench report'
        if value == '2': core.appearance_menu()
        elif value == '3': return '/dashboard'
        elif value == '4':
            print('\nЧат — переписка с моделью. Тесты — сравнение и агентские задачи.')
            print('Подключения — где запущены модели: здесь или на сервере по SSH.')
            print('В каждом меню 0 возвращает на предыдущий экран. В чате /home открывает главную.')
            print('Управление выделено голубым; успех — зелёным; предупреждение — жёлтым.')
            print('Настройки подключения и результаты приватны: не публикуйте Runtime и Benchmarks.')
            pause(core)
        elif value == '5':
            command = command_menu(core)
            if command: return command
        elif value == '6':
            action = experimental_menu(core)
            if action: return action
        elif value in ('', '0'): return None
        else: print('Выберите пункт 0–6.')


def home_menu(core, backend_version, regression_summary):
    while True:
        core.clear_console()
        core.ui_header(f'BULL {core.APP_VERSION}', 'Главная', 'Выберите, что хотите сделать')
        offline = str(backend_version).casefold() in ('offline', 'недоступен', 'unavailable')
        core.ui_status_strip([('Модели', 'нет связи' if offline else core.backend_label(), 'warn' if offline else 'ok')])
        if offline:
            print('  Чат и запуск теста требуют подключения. Настройки и отчёты доступны.')
        core.ui_menu_item('1', 'Сравнить модели', 'Выбрать лучшую для ваших задач по качеству, скорости и памяти', 'ГЛАВНОЕ')
        core.ui_menu_item('2', 'Чат с моделью', 'Выбрать модель и начать или продолжить диалог')
        core.ui_menu_item('3', 'Подключение', 'Модели на этом компьютере или на сохранённом SSH-сервере')
        core.ui_menu_item('4', 'Дополнительно', 'Результаты, справка, диагностика и эксперименты')
        core.ui_menu_item('0', 'Выйти')
        raw = core.read_user_input('Выбор [0–4] › ').strip()
        if raw.startswith('/'):
            return core.normalize_console_command(raw)
        value = raw.casefold()
        if value in ('1', 'bench', 'benchmark'): return 'benchmark'
        if value == '2':
            action = chat_menu(core)
            if action: return action
        elif value in ('3', 'connection'): return 'connections'
        elif value == '4':
            command = more_menu(core)
            if command: return command
        elif value in ('0', 'exit', 'quit'): return 'exit'
        # Named shortcuts remain compatible; old numeric shortcuts intentionally do not.
        elif value in ('chat', 'load', 'agent'): return value
        elif value in ('ui', 'theme', 'appearance'): return '/ui'
        elif value == 'backend': return '/backend'
        elif value == 'status': return '/dashboard'
        else:
            core.yellow(); print('Введите номер 0–4.'); core.white()
