"""Explicit quick/full diagnostics; a menu selection never generates with an LLM."""
from .i18n import get_language


def diagnostics_menu(core, tp=None):
    from .installer import InstallationServices
    def text(en, ru): return en if get_language() == 'en' else ru
    while True:
        core.ui_header(text('APPLICATION DIAGNOSTICS', 'ДИАГНОСТИКА ПРОГРАММЫ'),
                       text('Additional / Diagnostics', 'Дополнительно / Диагностика'))
        core.ui_menu_item('1', text('Basic checks', 'Базовые проверки'),
                          text('Quick internal checks and API availability; no inference',
                               'Быстрые внутренние проверки и доступность API; без генерации'))
        core.ui_menu_item('2', text('Full internal regression', 'Полная внутренняя регрессия'),
                          text('The same mandatory offline suite as Setup; may take several minutes',
                               'Тот же обязательный офлайн-набор, что в Setup; может занять несколько минут'))
        core.ui_menu_item('0', text('Back', 'Назад'))
        value = core.read_user_input(text('Choice [0–2] > ', 'Выбор [0–2] > ')).strip()
        if value in ('', '0'): return
        if value == '1':
            core.ui_header(text('BASIC CHECKS', 'БАЗОВЫЕ ПРОВЕРКИ'))
            core.selftest(tp)
        elif value == '2':
            core.ui_header(text('FULL REGRESSION', 'ПОЛНАЯ РЕГРЕССИЯ'))
            result = InstallationServices(core).verify()
            (core.green if result.get('ok') else core.red)()
            core.ui_print(text('Verification: ', 'Проверка: ') + result.get('summary', '?'))
            core.white()
        else:
            continue
        core.read_user_input(text('Enter = back > ', 'Enter = назад > '))
