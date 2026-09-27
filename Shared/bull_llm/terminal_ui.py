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


def render_startup_mark(core):
    """Draw the full-colour Chafa product mark once, with a safe text fallback."""
    global _startup_mark_shown
    if _startup_mark_shown:
        return False
    _startup_mark_shown = True
    rendered = _load_chafa_mark()
    if rendered:
        print(rendered, end='' if rendered.endswith('\n') else '\n')
    else:
        core.matrix()
        for row in BULL_PIXEL_ART:
            print(row)
    core.white()
    print('  B U L L  //  Benchmarking & Usage of Local LLMs\n')
    return True


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


def settings_menu(core):
    while True:
        core.clear_console()
        core.ui_header('Настройки', 'Главная / Настройки')
        core.ui_menu_item('1', 'Внешний вид', 'Яркость и цветовая тема')
        core.ui_menu_item('2', 'Состояние программы', 'Подключение, ресурсы и диагностика')
        core.ui_menu_item('3', 'Расширенные настройки движка', 'Ollama, llama.cpp, пути, запуск сервера и импорт конфигурации')
        core.ui_menu_item('4', 'Как пользоваться', 'Короткая инструкция и справочник команд')
        core.ui_menu_item('0', 'Назад')
        value = core.read_user_input('Выбор › ').strip()
        if value == '1': core.appearance_menu()
        elif value == '2': return '/dashboard'
        elif value == '3': return core.backend_runtime_menu()
        elif value == '4':
            print('\nЧат — переписка с моделью. Тесты — сравнение и агентские задачи.')
            print('Подключения — где запущены модели: здесь или на сервере по SSH.')
            print('В каждом меню 0 возвращает на предыдущий экран. В чате /home открывает главную.')
            print('На главной можно сразу набрать /команду; весь справочник: /help all.')
            print('Управление выделено голубым; успех — зелёным; предупреждение — жёлтым.')
            print('Настройки подключения и результаты приватны: не публикуйте Runtime и Benchmarks.')
            pause(core)
        elif value in ('', '0'): return None
        else: print('Выберите пункт 0–4.')


def home_menu(core, backend_version, regression_summary):
    while True:
        core.clear_console()
        render_startup_mark(core)
        core.ui_header(f'BULL {core.APP_VERSION}', 'Главная', 'Чем займёмся?')
        offline = str(backend_version).casefold() in ('offline', 'недоступен', 'unavailable')
        core.ui_status_strip([('Модели', 'нет связи' if offline else core.backend_label(), 'warn' if offline else 'ok')])
        if offline:
            print('  Чат и запуск теста требуют подключения. Настройки и отчёты доступны.')
        core.ui_menu_item('1', 'Чат', 'Выбрать модель или продолжить сохранённый диалог')
        core.ui_menu_item('2', 'Тесты и результаты', 'Сравнение моделей, свой промпт, агентские задачи')
        core.ui_menu_item('3', 'Подключения', 'Этот компьютер или сервер по SSH')
        core.ui_menu_item('4', 'Настройки и помощь', 'Внешний вид, диагностика, расширенные параметры')
        core.ui_menu_item('5', 'Ввести команду', 'Открыть строку команд и примеры')
        core.ui_menu_item('0', 'Выйти')
        core.cyan(); print('\n  Команда /… доступна прямо здесь, например /bench list.'); core.white()
        raw = core.read_user_input('Номер или /команда › ').strip()
        if raw.startswith('/'):
            return core.normalize_console_command(raw)
        value = raw.casefold()
        if value == '1':
            action = chat_menu(core)
            if action: return action
        elif value in ('2', 'bench', 'benchmark'): return 'benchmark'
        elif value in ('3', 'connection'): return 'connections'
        elif value == '4':
            command = settings_menu(core)
            if command: return command
        elif value in ('5', '?', 'help'):
            command = command_menu(core)
            if command: return command
        elif value in ('0', 'exit', 'quit'): return 'exit'
        # Named shortcuts remain compatible; old numeric shortcuts intentionally do not.
        elif value in ('chat', 'load', 'agent'): return value
        elif value in ('ui', 'theme', 'appearance'): return '/ui'
        elif value == 'backend': return '/backend'
        elif value == 'status': return '/dashboard'
        else:
            core.yellow(); print('Введите номер 0–5 или команду с /.'); core.white()
