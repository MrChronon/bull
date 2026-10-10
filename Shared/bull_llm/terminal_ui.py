"""Task-based terminal navigation. Returns commands; never invokes inference itself."""

import base64
from pathlib import Path
import re

from .i18n import localized_print as print
from .i18n import get_language
from .readiness import test_library_status


_CONSOLE_ASSET = (
    Path(__file__).resolve().parents[2]
    / 'Assets' / 'Brand' / 'bull-mark-console-48.ansi.b64'
)
_SGR_ESCAPE_RE = re.compile(r'\x1b\[[0-9;:]*m')
_PIXEL_RE = re.compile(r'\x1b\[48;2;(\d{1,3});(\d{1,3});(\d{1,3})m ')
_TRUECOLOR_RE = re.compile(r'(?P<kind>38|48);2;(?P<r>\d{1,3});(?P<g>\d{1,3});(?P<b>\d{1,3})')

BULL_PIXEL_ART = (
    '       /##            ##\\',
    '     /####            ####\\',
    '    / ####            #### \\',
    '   (  ####            ####  )',
    '    \\_____\\__  o  __/_____/',
    '       _____\\ o|o /_____',
    '        \\###\\ | /###/',
    '         |    \\|/    |',
    '          \\    |    /',
    '           \\ _____ /',
    '            ( _   _ )',
    '             \\___/',
)

_startup_mark_shown = False
_WORDMARK = '  B U L L  //  Benchmarking & Usage of Local Language Models'


def _load_console_mark():
    """Accept only fixed-size RGB background cells and explicit row resets."""
    try:
        encoded = ''.join(_CONSOLE_ASSET.read_text(encoding='ascii').split())
        if not encoded or len(encoded) > 40_000:
            return None
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 64 * 1024:
            return None
        rendered = raw.decode('ascii')
    except (OSError, ValueError, UnicodeError):
        return None

    lines = rendered.split('\n')
    if len(lines) != 25 or lines[-1] != '':
        return None
    for row in lines[:-1]:
        if not row.startswith('\x1b[0m') or not row.endswith('\x1b[0m'):
            return None
        body = row[4:-4]
        if re.fullmatch('(?:' + _PIXEL_RE.pattern + '){48}', body) is None:
            return None
        if any(int(channel) > 255 for cell in _PIXEL_RE.findall(body) for channel in cell):
            return None
    return rendered


def _render_text_mark(core):
    core.matrix()
    for row in BULL_PIXEL_ART:
        print(row)
    core.white()


def _theme_console_mark(rendered, theme):
    """Keep the canonical geometry while adapting saturated brand pixels."""
    theme = str(theme or 'bull_brand').strip().casefold()
    if theme == 'bull_brand':
        return rendered
    targets = {
        'matrix_bright': (54, 255, 115),
        'matrix_balanced': (45, 220, 105),
        'matrix_soft': (38, 176, 91),
        'bull_red': (255, 60, 82),
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


def _render_console_mark(core):
    rendered = _load_console_mark() if getattr(core, '_COLOR_ENABLED', False) else None
    if rendered is None:
        _render_text_mark(core)
        return False
    themed = _theme_console_mark(rendered, getattr(core, 'UI_THEME', 'bull_brand'))
    # Windows console hosts can cut a large ANSI write in the middle of an
    # escape sequence. Emit complete bounded rows, including their reset and
    # newline, so the following wordmark cannot attach to a partial pixel row.
    for row in themed.splitlines():
        print(row, flush=True)
    return True


def _render_wordmark(core):
    core.white()
    print(_WORDMARK)


def render_startup_mark(core):
    """Draw the font-independent colour mark once, with an ASCII fallback."""
    global _startup_mark_shown
    if _startup_mark_shown:
        return False
    _startup_mark_shown = True
    _render_console_mark(core)
    _render_wordmark(core)
    print()
    return True


def render_page_mark(core):
    """Draw the canonical bull and product expansion on every page."""
    _render_console_mark(core)
    _render_wordmark(core)


def selection(raw, rows):
    if not str(raw).isdigit():
        return None
    index = int(raw) - 1
    return rows[index] if 0 <= index < len(rows) else None


def pause(core):
    core.read_user_input('\nEnter — назад › ')


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




def additional_menu(core):
    """Flat access to supporting tools; selecting a row only returns its command."""
    while True:
        en = get_language() == 'en'
        def text(english, russian): return english if en else russian
        core.ui_header(text('ADDITIONAL','ДОПОЛНИТЕЛЬНО'),
                       text('Home / Additional','Главная / Дополнительно'))
        core.ui_menu_item('1', text('Session status','Состояние сессии'),
                          text('Connection and current session overview','Обзор соединения и текущей сессии'))
        core.ui_menu_item('2', text('Application diagnostics','Диагностика программы'),
                          text('Internal checks and API availability; no model generation',
                               'Внутренние проверки и доступность API; без генерации моделью'))
        core.ui_menu_item('3', text('How to use BULL','Как пользоваться BULL'))
        core.ui_menu_item('4', text('Command reference','Справочник команд'))
        core.ui_section(text('EXPERIMENTAL TOOLS','ЭКСПЕРИМЕНТАЛЬНЫЕ ИНСТРУМЕНТЫ'))
        core.ui_menu_item('5','Agent Benchmark',
                          text('Python repair task (MVP)','Исправление Python-проекта (MVP)'))
        core.ui_menu_item('0', text('Back','Назад'))
        choice = core.read_user_input(text('Choice [0–5] > ','Выбор [0–5] > ')).strip()
        if choice in ('','0'): return None
        command = {'1':'/dashboard','2':'/diagnostics','4':'/help all','5':'/agent'}.get(choice)
        if command: return command
        if choice == '3':
            core.helptext()
            core.read_user_input(text('Enter = back > ','Enter = назад > '))
        else:
            core.yellow(); core.ui_print(text('Choose an option 0–5.','Выберите пункт 0–5.')); core.white()


def home_menu(core, backend_version, regression_summary):
    en = get_language() == 'en'
    def text(english, russian): return english if en else russian
    while True:
        en = get_language() == 'en'
        core.clear_console()
        core.ui_header(f'BULL {core.APP_VERSION}', 'Главная', 'Выберите, что хотите сделать')
        offline = str(backend_version).casefold() in ('offline', 'недоступен', 'unavailable')
        core.ui_status_strip([
            (text('Integrity','Целостность'), regression_summary, 'ok'),
            (text('Connection','Соединение'), text('offline (section 4)','нет связи (раздел 4)') if offline else core.backend_label(), 'warn' if offline else 'ok'),
        ])
        core.ui_menu_item('1', text('Model testing','Тестирование моделей'), text('Run tests, resume or view results','Запуск тестов, продолжение и просмотр результатов'))
        core.ui_menu_item('2', text('Chat with a model','Чат с моделью'), text('New conversation or saved chat','Новый разговор или сохранённый чат'))
        core.ui_menu_item('3', text('Test settings','Настройки тестов'), text('Install packs, select tasks, manage your library','Установка наборов, выбор заданий и управление библиотекой'))
        core.ui_menu_item('4', text('Connection settings','Настройки соединения программы'), text('This computer or an existing LLM server','Этот компьютер или существующий LLM-сервер'))
        core.ui_menu_item('5', text('Program settings','Настройки программы'), text('Language and themes','Язык и цветовые темы'))
        core.ui_menu_item('6', text('Additional','Дополнительно'), text('Diagnostics, help and Agent Benchmark','Диагностика, справка и Agent Benchmark'))
        core.ui_menu_item('0', 'Выйти')
        raw = core.read_user_input(text('Choice [0–6] > ','Выбор [0–6] > ')).strip()
        if raw.startswith('/'):
            return core.normalize_console_command(raw)
        value = raw.casefold()
        if value in ('1', 'bench', 'benchmark'): return 'benchmark'
        if value == '2':
            action = chat_menu(core)
            if action: return action
        elif value in ('3', 'packs'): return 'packs'
        elif value in ('4', 'connection'): return 'connections'
        elif value == '5':
            command = core.appearance_menu()
            if command: return command
        elif value in ('6','additional'):
            command = additional_menu(core)
            if command: return command
        elif value in ('0', 'exit', 'quit'): return 'exit'
        # Named shortcuts remain compatible; old numeric shortcuts intentionally do not.
        elif value in ('chat', 'load', 'agent'): return value
        elif value in ('ui', 'theme', 'appearance'): return '/ui'
        elif value == 'backend': return '/backend'
        elif value == 'status': return '/dashboard'
        else:
            core.yellow(); core.ui_print(text('Enter an option number 0–6.','Введите номер 0–6.')); core.white()
