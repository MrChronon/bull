"""Sequential client setup. Uses existing pack, trust and verification boundaries."""
from __future__ import annotations
import os
from pathlib import Path
import re
import sys

from .i18n import get_language, set_language
from .readiness import test_library_status


def text(english,russian):
    return english if get_language() == 'en' else russian


def choose_language(core):
    core.ui_print('BULL · installation language / язык установки')
    core.ui_print('[1] English  [2] Русский')
    while True:
        value = core.read_user_input('Language / Язык [1–2] > ').strip().casefold()
        if value in ('1','en'):return 'en'
        if value in ('2','ru'):return 'ru'


def choose_theme(core):
    core.ui_header(text('COLOUR SCHEME', 'ЦВЕТОВАЯ СХЕМА'))
    core.ui_menu_item('1', 'BULL Red')
    core.ui_menu_item('2', 'BULL Matrix')
    while True:
        choice = core.read_user_input(text('Theme [1–2] > ', 'Тема [1–2] > ')).strip().casefold()
        if choice in ('1', 'red', 'bull red'): return 'bull_red'
        if choice in ('2', 'matrix', 'bull matrix'): return 'matrix_bright'


def run_installer(core,services,*,language=None,theme=None):
    set_language(language if language in ('en','ru') else choose_language(core))
    core.save_ui_language(get_language())
    selected_theme = theme if theme in ('bull_red', 'matrix_bright') else choose_theme(core)
    core.set_ui_theme(selected_theme, persist=True)
    while True:
        core.ui_header(text('INSTALLATION · 1/3 · TEST PACKS','УСТАНОВКА · 1/3 · НАБОРЫ ТЕСТОВ'))
        core.ui_print(text('Packs are optional and survive BULL updates. No models are installed.',
                           'Наборы необязательны и сохраняются при обновлении BULL. Модели не устанавливаются.'))
        core.ui_menu_item('1',text('Install standard packs','Установить стандартные наборы'))
        core.ui_menu_item('2',text('Import a pack: HTTPS archive link or local ZIP','Добавить свой набор: HTTPS-ссылка на архив или локальный ZIP'))
        core.ui_menu_item('0',text('Continue without installing tests','Продолжить без установки тестов'))
        choice = core.read_user_input(text('Choice [0–2] > ','Выбор [0–2] > ')).strip()
        try:
            if choice == '0':services.skip_packs();break
            if choice == '1' and services.install_base():break
            if choice == '2':
                source = core.read_user_input(text('HTTPS link or ZIP path [Enter=back] > ','HTTPS-ссылка или путь к ZIP [Enter=назад] > ')).strip()
                if source and services.import_pack(source):break
        except (OSError,ValueError,KeyError) as error:
            core.yellow()
            core.ui_print(text('The pack was not activated. Check the ZIP/link or skip this step.',
                               'Набор не включён. Проверьте ZIP/ссылку или пропустите этот шаг.'))
            core.white()
            if hasattr(core,'append_client_debug'):core.append_client_debug('INSTALL_PACK_FAILED ' + type(error).__name__)
            core.read_user_input(text('Enter = retry > ','Enter = повторить > '))

    core.ui_header(text('INSTALLATION · 2/3 · FULL VERIFICATION','УСТАНОВКА · 2/3 · ПОЛНАЯ ПРОВЕРКА'))
    core.ui_print(text('Internal application regression; no LLM inference or model scoring.',
                       'Внутренняя регрессия программы; без запросов к LLM и оценки моделей.'))
    while True:
        result = services.verify()
        if result.get('ok'):break
        core.red();core.ui_print(text('Verification failed. Installation is not complete.',
                                     'Проверка не пройдена. Установка не завершена.'));core.white()
        if core.read_user_input(text('[1] Retry  [0] Exit > ','[1] Повторить  [0] Выйти > ')).strip() != '1':return 2

    core.ui_header(text('INSTALLATION · 3/3 · CONNECTION','УСТАНОВКА · 3/3 · СОЕДИНЕНИЕ'))
    core.ui_print(text('Connect to existing models now or configure them later in section 4.',
                       'Подключитесь к существующим моделям сейчас или настройте связь позже в разделе 4.'))
    core.ui_menu_item('1',text('Configure connection','Настроить соединение'))
    core.ui_menu_item('0',text('Configure later','Настроить позже'))
    while True:
        value = core.read_user_input(text('Choice [0–1] > ','Выбор [0–1] > ')).strip()
        if value == '1':services.connection_menu();break
        if value == '0':break
    status = services.status()
    services.complete(result,status)
    services.shortcuts()
    core.ui_header(text('INSTALLATION COMPLETE','УСТАНОВКА ЗАВЕРШЕНА'))
    core.ui_print(text('BULL is installed. Change tests, connection and preferences in sections 3–5.',
                       'BULL установлен. Наборы, соединение и параметры можно изменить в разделах 3–5.'))
    core.green();core.ui_print(text('Application integrity: OK · ','Целостность программы: OK · ') + result['summary']);core.white()
    for ready, good, missing in [
        (status['connection'],text('● LLM connection available','● Связь с LLM доступна'),text('⚠ No connection. Configure section 4.','⚠ Нет связи. Настройте раздел 4.')),
        (status['packs']['count'] > 0,text('● Test packs installed','● Наборы тестов установлены'),text('⚠ No test packs. Install them in section 3.','⚠ Нет наборов тестов. Установите их в разделе 3.')),
    ]:
        (core.green if ready else core.yellow)();core.ui_print(good if ready else missing);core.white()
    core.ui_menu_item('1',text('Launch BULL','Запустить BULL'))
    core.ui_menu_item('0',text('Exit installer','Выйти из установщика'))
    while True:
        choice = core.read_user_input(text('Choice [0–1] > ','Выбор [0–1] > ')).strip()
        if choice == '1':services.launch();return 0
        if choice == '0':return 0


class InstallationServices:
    def __init__(self,core,*,desktop='',programs=''):
        self.core = core
        self.root = Path(core.__file__).resolve().parent
        self.desktop = desktop
        self.programs = programs

    def skip_packs(self):
        from .evaluation.pack_selection import PackSelection
        PackSelection(self.core.benchmark_pack_library()).finish_onboarding()

    def install_base(self):
        from .evaluation.pack_selection import PackSelection
        from .pack_library_ui import install_archives
        store = PackSelection(self.core.benchmark_pack_library())
        return install_archives(self.core,store,sorted((self.root/'BasePacks').glob('*.zip')),select_default=True)

    def import_pack(self,source):
        from .evaluation.pack_selection import PackSelection
        from .pack_library_ui import install
        from .pack_download import archive_source
        with archive_source(source) as archive:
            return install(self.core,PackSelection(self.core.benchmark_pack_library()),archive)

    def verify(self):
        core = self.core
        window = core.open_startup_verification_window()
        try:
            smoke = core.run_startup_regression(force=True,progress_callback=lambda stage,current,total:
                window.update(core._startup_stage_for_ui(stage),current,total) if window is not None else None)
            if not smoke['ok']:return smoke
            completed = 0
            total = None
            def progress(line):
                nonlocal completed,total
                declared = core._startup_count_from_output(line,core._STARTUP_TOTAL_MARKER)
                if declared is not None:total = declared
                count = core._startup_count_from_output(line,core._STARTUP_COMPLETE_MARKER)
                if count is not None:completed = count
                active = core._startup_active_check_from_output(line)
                if active:
                    label = text('Current check: ','Текущая проверка: ') + active
                    core.ui_print(label)
                    if window is not None:window.update(label,completed,total or 0)
                elif count is not None:
                    core.ui_print(text('Completed: ','Завершено: ') + f'{completed}/{total or "?"}')
                    if window is not None:window.update(text('Internal regression','Внутренняя регрессия'),completed,total or 0)
            code,output,timed_out = core._stream_startup_regression(self.root/'Tests/benchmark_regression.py',progress,timeout=600)
            matches = re.findall(r'PASS\s+(\d+)\s*/\s*(\d+)',output)
            passed,final_total = map(int,matches[-1]) if matches else (0,0)
            ok = code == 0 and not timed_out and final_total > 0 and passed == final_total == total and completed == total
            if not ok:core.append_client_debug('INSTALL_REGRESSION_FAILED\n' + output)
            return {'ok':ok,'summary':f'{passed}/{final_total}','passed':passed,'total':final_total}
        finally:
            if window is not None:window.close()

    def shortcuts(self):
        import subprocess
        command = ['powershell.exe','-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',
                   str(self.root/'Tools/Update-BULL-Shortcuts.ps1'),'-Quiet','-Theme',self.core.UI_THEME]
        if self.desktop:command += ['-DesktopDirectory',self.desktop]
        if self.programs:command += ['-ProgramsDirectory',self.programs]
        env = {key:value for key,value in os.environ.items() if key.casefold() != 'psmodulepath'}
        result = subprocess.run(command,check=False,timeout=30,capture_output=True,env=env,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise ValueError('INSTALL_SHORTCUT_FAILED')

    def connection_menu(self):
        from .connections_ui import connection_menu
        connection_menu(self.core,setup=True)

    def status(self):
        core = self.core
        connection = False
        transport = None
        try:
            core.initialize_backend_from_settings()
            transport,_ = core.connect_active_backend()
            connection = bool(core.version(2))
        except Exception as error:
            core.append_client_debug('INSTALL_CONNECTION_UNAVAILABLE ' + type(error).__name__)
        finally:
            from .owned_processes import reap
            reap(transport)
        return {'connection':connection,'packs':test_library_status(core)}

    def complete(self,verification,status):
        from .storage import atomic_json
        from .client_launcher import materialize,verified_payload
        if not verification.get('ok'):raise ValueError('INSTALL_VERIFICATION_REQUIRED')
        existed = (self.root/'BULL.exe').exists()
        executable = materialize(self.root)
        try:
            atomic_json(self.root/'Runtime/installation_state.json',{
                'schema':'bull-installation-state','schema_version':1,'status':'complete',
                'language':get_language(),'verification':verification['summary'],
                'python_executable':sys.executable,
                'connection_available':status['connection'],'installed_pack_count':status['packs']['count'],
            })
        except Exception:
            # Failed fresh setup must not leave a launchable half-installation.
            # Never remove a pre-existing or concurrently changed executable.
            if not existed:
                try:
                    if executable.read_bytes() == verified_payload(self.root):executable.unlink()
                except (OSError,ValueError):pass
            raise

    def launch(self):
        os.startfile(str(self.root/'BULL.exe'))
