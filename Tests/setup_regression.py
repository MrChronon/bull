"""Installation and shallow navigation contracts; no real user or network writes."""
from __future__ import annotations
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class SetupTests(unittest.TestCase):
    core = None

    def setUp(self):
        from Shared.bull_llm.i18n import set_language
        set_language('ru')

    def menu(self, values):
        return patch.object(self.core, 'read_user_input', side_effect=values)

    def test_five_home_sections_have_requested_numbers(self):
        from Shared.bull_llm import terminal_ui
        out = io.StringIO()
        with patch.object(self.core, 'ui_header'), self.menu(['0']), \
             patch.object(terminal_ui, 'test_library_status', return_value={'count':0,'selected':None,'issues':0}), \
             contextlib.redirect_stdout(out):
            self.assertEqual(self.core.startup_home_menu('offline','18/18'), 'exit')
        for key, label in [('1','Тестирование моделей'),('2','Чат с моделью'),('3','Настройки тестов'),
                           ('4','Настройки соединения программы'),('5','Настройки программы')]:
            self.assertIn('[' + key + '] ' + label, out.getvalue())
        self.assertNotIn('[5] Дополнительно', out.getvalue())
        self.assertIn('[6] Дополнительно', out.getvalue())

    def test_additional_actions_return_existing_commands_without_backend_access(self):
        from Shared.bull_llm.terminal_ui import additional_menu
        with patch.object(self.core, 'ui_header'), \
             patch.object(self.core, 'connect_active_backend', side_effect=AssertionError('Menu must not connect')):
            for choice, command in [('1','/dashboard'),('2','/diagnostics'),('4','/help all'),
                                    ('5','/agent')]:
                with self.menu([choice]):
                    self.assertEqual(additional_menu(self.core), command)

    def test_additional_back_returns_to_home_without_starting_an_action(self):
        from Shared.bull_llm import terminal_ui
        with patch.object(self.core, 'ui_header'), self.menu(['6','0','0']), \
             patch.object(terminal_ui, 'test_library_status', return_value={'count':0,'selected':None,'issues':0}):
            self.assertEqual(self.core.startup_home_menu('offline','18/18'), 'exit')

    def test_program_settings_and_testing_do_not_duplicate_additional_actions(self):
        with patch.object(self.core, 'ui_header'), patch.object(self.core, 'ui_menu_item') as item:
            with self.menu(['0']): self.assertIsNone(self.core.appearance_menu())
            self.assertEqual([call.args[0] for call in item.call_args_list], ['1','2','3','0'])
            item.reset_mock()
            with self.menu(['0']): self.assertEqual(self.core.startup_benchmark_wizard(), ('/home',False))
            self.assertEqual([call.args[0] for call in item.call_args_list], ['1','2','3','4','5','P','L','?','0'])

    def test_additional_guide_stays_in_menu_and_uses_selected_language(self):
        from Shared.bull_llm.i18n import set_language
        from Shared.bull_llm.terminal_ui import additional_menu
        for language, title in [('en','How to use BULL'),('ru','Как пользоваться BULL')]:
            set_language(language)
            out = io.StringIO()
            with patch.object(self.core, 'ui_header'), patch.object(self.core, 'helptext') as help, \
                 self.menu(['3','','0']), contextlib.redirect_stdout(out):
                self.assertIsNone(additional_menu(self.core))
            help.assert_called_once_with()
            self.assertIn('[3] ' + title, out.getvalue())

    def test_home_pack_and_connection_routes_are_not_swapped(self):
        from Shared.bull_llm import terminal_ui
        with patch.object(self.core, 'ui_header'), patch.object(terminal_ui, 'test_library_status',
                return_value={'count':0,'selected':None,'issues':0}):
            with self.menu(['3']): self.assertEqual(self.core.startup_home_menu('offline','OK'), 'packs')
            with self.menu(['4']): self.assertEqual(self.core.startup_home_menu('offline','OK'), 'connections')

    def test_offline_home_has_explicit_warnings_not_fake_ready(self):
        from Shared.bull_llm import terminal_ui
        out = io.StringIO()
        with patch.object(self.core, 'ui_header'), self.menu(['0']), \
             patch.object(terminal_ui, 'test_library_status', return_value={'count':0,'selected':None,'issues':0}), \
             contextlib.redirect_stdout(out):
            self.core.startup_home_menu('offline','18/18')
        self.assertIn('нет связи', out.getvalue())
        self.assertNotIn('нет наборов', out.getvalue())

    def test_home_readiness_appears_once_above_menu_not_per_item(self):
        from Shared.bull_llm import terminal_ui
        cases = (
            ('1.0', {'count':4, 'selected':{'identity':'fixture@1.0.0'}, 'issues':0}, ('ok','ok','ok')),
            ('1.0', {'count':4, 'selected':None, 'issues':0}, ('ok','ok','warn')),
            ('offline', {'count':0, 'selected':None, 'issues':0}, ('ok','warn','warn')),
        )
        for backend, packs, levels in cases:
            out = io.StringIO()
            with patch.object(self.core, 'ui_header'), self.menu(['0']), \
                 patch.object(terminal_ui, 'test_library_status', return_value=packs), \
                 patch.object(self.core, 'ui_status_strip') as strip, \
                 contextlib.redirect_stdout(out):
                self.assertEqual(self.core.startup_home_menu(backend, '18/18'), 'exit')
            strip.assert_called_once()
            rows = strip.call_args.args[0]
            self.assertEqual([row[0] for row in rows], ['Целостность','Соединение'])
            self.assertEqual(tuple(row[2] for row in rows), levels[:2])
            self.assertNotIn('●', out.getvalue())
            self.assertNotIn('Связь доступна', out.getvalue())
            self.assertNotIn('Нет связи', out.getvalue())
            self.assertNotIn('fixture@1.0.0', out.getvalue())
            self.assertEqual(len(rows),2)

    def test_user_file_and_prompt_are_direct_test_actions(self):
        with patch.object(self.core, 'ui_header'), patch.object(self.core, 'benchmark_user_file_wizard', return_value='/bench file') as file, \
             patch.object(self.core, 'benchmark_custom_prompt_wizard', return_value='/bench prompt') as prompt:
            with self.menu(['2']): self.assertEqual(self.core.startup_benchmark_wizard(), ('/bench file',True))
            with self.menu(['3']): self.assertEqual(self.core.startup_benchmark_wizard(), ('/bench prompt',True))
        file.assert_called_once_with()
        prompt.assert_called_once_with()

    def test_saved_results_are_direct_and_do_not_require_backend(self):
        guard = Mock(side_effect=AssertionError('Offline report must not connect'))
        with patch.object(self.core, 'ui_header'), self.menu(['5']):
            self.assertEqual(self.core.startup_benchmark_wizard(runtime_guard=guard), ('/bench report',False))
        guard.assert_not_called()

    def test_startup_gate_is_forced_in_main(self):
        import ast
        tree = ast.parse(Path(self.core.__file__).read_text(encoding='utf-8-sig'))
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        call = next(n for n in ast.walk(main) if isinstance(n, ast.Call) and
                    isinstance(n.func, ast.Name) and n.func.id == 'run_startup_regression')
        self.assertTrue(any(k.arg == 'force' and isinstance(k.value, ast.Constant) and k.value.value is True for k in call.keywords))

    def test_missing_library_is_valid_unconfigured_state(self):
        from Shared.bull_llm.readiness import test_library_status
        library = SimpleNamespace(scan=lambda: [])
        with patch.object(self.core, 'benchmark_pack_library', return_value=library), \
             patch('Shared.bull_llm.readiness.PackSelection') as store:
            store.return_value.snapshot.return_value = None
            status = test_library_status(self.core)
        self.assertEqual(status['count'],0)
        self.assertIsNone(status['selected'])

    def test_invalid_selection_does_not_hide_valid_installed_packs(self):
        from Shared.bull_llm.readiness import test_library_status
        library = SimpleNamespace(scan=lambda: [SimpleNamespace(pack=SimpleNamespace(runnable=True))])
        with patch.object(self.core, 'benchmark_pack_library', return_value=library), \
             patch('Shared.bull_llm.readiness.PackSelection') as store:
            store.return_value.snapshot.side_effect = ValueError('invalid')
            status = test_library_status(self.core)
        self.assertEqual(status['count'],1)
        self.assertGreater(status['issues'],0)
        self.assertIsNone(status['selected'])

    def test_damaged_library_is_warning_not_application_failure(self):
        from Shared.bull_llm.readiness import test_library_status
        with patch.object(self.core, 'benchmark_pack_library', side_effect=OSError('unavailable')):
            status = test_library_status(self.core)
        self.assertEqual(status['count'],0)
        self.assertGreater(status['issues'],0)

    def test_installer_uses_one_client_workflow_no_roles(self):
        root = Path(self.core.__file__).parent
        script = (root / 'Setup.ps1').read_text(encoding='utf-8-sig')
        for retired in ('$Role','AllInOne','RunAs','Install-BULL-Node'):
            self.assertNotIn(retired, script)
        self.assertIn('Language', script)
        self.assertIn('install_bull.py', script)

    def picker(self, answers, *, active=None, rows=()):
        from Shared.bull_llm.pack_library_ui import select_for_run
        core = SimpleNamespace(ui_header=Mock(),ui_print=Mock(),ui_menu_item=Mock(),
                               yellow=Mock(),white=Mock(),read_user_input=Mock(side_effect=answers))
        store = Mock();store.snapshot.return_value=active;store.library.scan.return_value=rows
        return select_for_run(core,store)

    def test_fresh_python_dependencies_are_explicit_and_private(self):
        root = Path(self.core.__file__).parent
        script = (root/'Setup.ps1').read_text(encoding='utf-8-sig')
        for marker in ('Runtime\\Python','-m venv','--isolated','--only-binary=:all:',
                       '--index-url https://pypi.org/simple','regression-requirements.txt'):
            self.assertIn(marker,script)
        requirements = (root/'Setup/regression-requirements.txt').read_text()
        for package in ('numpy','pandas','scipy','matplotlib'):self.assertIn(package,requirements)

    def test_all_launchers_use_the_verified_interpreter(self):
        root = Path(self.core.__file__).parent
        source = (root/'BULL-v0.29.0.1.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('Runtime\\installation_state.json',source)
        self.assertIn('& $verifiedPython -u $client',source)
        for surface, name in [('benchmark','BULL-Benchmark-Lab'),('agent','BULL-Agent-Lab')]:
            wrapper = (root/f'{name}-v0.29.0.1.cmd').read_text()
            self.assertIn('-Surface ' + surface,wrapper)

    def test_standard_install_really_selects_only_safe_chat_pack(self):
        import tempfile
        from Shared.bull_llm.evaluation.pack_library import PackLibrary
        from Shared.bull_llm.evaluation.pack_selection import PackSelection
        from Shared.bull_llm.pack_library_ui import install_archives
        with tempfile.TemporaryDirectory() as tmp:
            library = PackLibrary(tmp,self.core.benchmark_registry_policy())
            store = PackSelection(library)
            ui = Mock();ui.read_user_input.return_value = 'y'
            self.assertTrue(install_archives(ui,store,sorted((Path(self.core.__file__).parent/'BasePacks').glob('*.zip')),select_default=True))
            self.assertEqual(len(library.scan()),4)
            selected = store.snapshot()
            self.assertEqual(selected['identity'],'bull_chat_core@1.0.0')
            self.assertEqual(store.read()['selection']['approved_code_cases'],[])

    def test_direct_picker_can_exit_without_entering_chat(self):
        self.assertFalse(self.picker(['0']))

    def test_direct_picker_reuses_exact_current_selection(self):
        self.assertTrue(self.picker([''],active={'identity':'pack@1','selected_cases':1,'total_cases':2}))

    def test_direct_picker_goes_straight_to_case_selection(self):
        pack = SimpleNamespace(runnable=True,title='Test',identity='pack@1',cases=[1])
        with patch('Shared.bull_llm.pack_library_ui.choose_cases',return_value=True) as choose:
            self.assertTrue(self.picker(['1'],rows=[SimpleNamespace(pack=pack)]))
        self.assertIs(choose.call_args.args[2],pack)

    def test_direct_picker_warns_about_no_packs_and_offers_settings(self):
        with patch('Shared.bull_llm.pack_library_ui.library_menu',return_value=True) as menu:
            self.assertTrue(self.picker(['t']))
        menu.assert_called_once()


class InstallerFlowTests(unittest.TestCase):
    def setUp(self):
        from Shared.bull_llm.i18n import set_language
        set_language('en')
        self.output = []
        self.prompts = []
        self.events = []

    def core(self, answers):
        values = iter(answers)
        def read(prompt):
            self.prompts.append(prompt)
            return next(values)
        def record(*args): self.output.extend(str(x) for x in args)
        return SimpleNamespace(APP_VERSION='v0.29.0.1',read_user_input=read,ui_print=record,
            ui_header=record,ui_menu_item=record,save_ui_language=lambda lang:self.events.append('language:' + lang),
            set_ui_theme=lambda value,**kwargs:None,
            green=lambda:None,white=lambda:None,yellow=lambda:None,red=lambda:None)

    def services(self, verified=True):
        def event(name, result=None):
            return lambda *args: self.events.append(name) or result
        return SimpleNamespace(install_base=event('base',True),import_pack=event('import',True),
            skip_packs=event('skip_packs'),verify=event('verify',{'ok':verified,'summary':'18/18'}),
            shortcuts=event('shortcuts'),connection_menu=event('connection'),
            status=event('status',{'connection':False,'packs':{'count':0,'selected':None,'issues':0}}),
            complete=event('complete'),launch=event('launch'))

    def run_flow(self, answers, *, verified=True, language='ru'):
        from Shared.bull_llm.installer import run_installer
        return run_installer(self.core(answers),self.services(verified),language=language,theme='bull_red')

    def test_skip_is_successfully_installed_ready_for_configuration(self):
        self.assertEqual(self.run_flow(['0','0','0']),0)
        self.assertEqual(self.events, ['language:ru','skip_packs','verify','status','complete','shortcuts'])
        self.assertNotIn('launch',self.events)

    def test_failed_regression_never_marks_installation_complete(self):
        self.assertNotEqual(self.run_flow(['0','0'],verified=False),0)
        self.assertNotIn('shortcuts',self.events)
        self.assertNotIn('connection',self.events)
        self.assertNotIn('complete',self.events)

    def test_full_verification_precedes_connection_and_completion(self):
        self.assertEqual(self.run_flow(['1','1','0']),0)
        self.assertLess(self.events.index('base'),self.events.index('verify'))
        self.assertLess(self.events.index('verify'),self.events.index('connection'))
        self.assertLess(self.events.index('connection'),self.events.index('complete'))

    def test_program_launch_is_explicit_and_only_after_completion(self):
        self.assertEqual(self.run_flow(['0','0','1']),0)
        self.assertLess(self.events.index('complete'),self.events.index('launch'))

    def test_language_choice_applies_before_pack_and_verification_prompts(self):
        self.assertEqual(self.run_flow(['2','0','0','0'],language=None),0)
        self.assertEqual(self.events[0],'language:ru')
        self.assertIn('Наборы', ' '.join(self.output))

    def test_english_installer_has_no_russian_instructions(self):
        self.assertEqual(self.run_flow(['0','0','0'],language='en'),0)
        rendered = ' '.join(self.output + self.prompts)
        self.assertFalse(any(('А' <= ch <= 'я') or ch in 'Ёё' for ch in rendered),rendered)

    def test_link_import_requires_explicit_source(self):
        services = self.services()
        services.import_pack = Mock(return_value=True)
        from Shared.bull_llm.installer import run_installer
        self.assertEqual(run_installer(self.core(['2','https://example.invalid/pack.zip','0','0']),services,language='en',theme='bull_red'),0)
        services.import_pack.assert_called_once_with('https://example.invalid/pack.zip')

    def test_declined_pack_install_can_be_skipped_without_false_failure(self):
        services = self.services()
        services.install_base = Mock(return_value=False)
        from Shared.bull_llm.installer import run_installer
        self.assertEqual(run_installer(self.core(['1','0','0','0']),services,language='en',theme='bull_red'),0)
        self.assertIn('skip_packs',self.events)
        self.assertIn('complete',self.events)

    def test_download_error_does_not_complete_or_fetch_again_implicitly(self):
        services = self.services()
        services.import_pack = Mock(side_effect=ValueError('PACK_DOWNLOAD_FAILED'))
        from Shared.bull_llm.installer import run_installer
        self.assertEqual(run_installer(self.core(['2','https://example.invalid/pack.zip','','0','0','0']),services,language='en',theme='bull_red'),0)
        self.assertEqual(services.import_pack.call_count,1)
        self.assertIn('skip_packs',self.events)

    def test_invalid_choices_do_not_advance_steps(self):
        self.assertEqual(self.run_flow(['wrong','0','wrong','0','wrong','0']),0)
        self.assertEqual(self.events.count('verify'),1)
        self.assertEqual(self.events.count('complete'),1)


class InstallerServicesTests(unittest.TestCase):
    def make_services(self):
        from Shared.bull_llm.installer import InstallationServices
        self.window = Mock()
        self.core = Mock(__file__=str(Path(__file__).resolve().parents[1]/'bull_client_v0.29.0.1.py'))
        self.core.open_startup_verification_window.return_value = self.window
        self.core.run_startup_regression.return_value = {'ok':True,'summary':'18/18'}
        self.core._STARTUP_TOTAL_MARKER = 'TOTAL'
        self.core._STARTUP_COMPLETE_MARKER = 'DONE'
        self.core._startup_count_from_output.side_effect = lambda line,key:int(line.split()[1]) if line.startswith(key+' ') else None
        self.core._startup_active_check_from_output.return_value = None
        self.services = InstallationServices(self.core)
        return self.services

    def stream(self, code=0, output='PASS 3/3', timeout=False, counts=True):
        def run(path,callback,**kwargs):
            self.assertEqual(path.name,'benchmark_regression.py')
            if counts:callback('TOTAL 3');callback('DONE 3')
            return code,output,timeout
        self.core._stream_startup_regression.side_effect = run

    def test_smoke_failure_does_not_run_full_suite(self):
        services = self.make_services();self.core.run_startup_regression.return_value={'ok':False}
        self.assertFalse(services.verify()['ok']);self.core._stream_startup_regression.assert_not_called()
        self.window.close.assert_called_once()

    def test_full_suite_requires_exit_and_exact_completed_count(self):
        services = self.make_services();self.stream()
        self.assertTrue(services.verify()['ok'])
        self.assertTrue(self.core.run_startup_regression.call_args.kwargs['force'])
        self.window.close.assert_called_once()

    def test_missing_progress_markers_cannot_fake_a_pass(self):
        services = self.make_services();self.stream(counts=False)
        self.assertFalse(services.verify()['ok'])

    def test_nonzero_timeout_or_incomplete_total_fail_closed(self):
        for options in ({'code':2},{'timeout':True},{'output':'PASS 2/3'},{'output':'PASS 4/4'}):
            services = self.make_services();self.stream(**options)
            self.assertFalse(services.verify()['ok'])

    def test_progress_window_closes_on_exception(self):
        services = self.make_services();self.core._stream_startup_regression.side_effect=OSError('fixture')
        with self.assertRaises(OSError):services.verify()
        self.window.close.assert_called_once()

    def test_optional_connection_failure_is_a_warning(self):
        services = self.make_services();self.core.initialize_backend_from_settings.side_effect=TimeoutError('fixture')
        with patch('Shared.bull_llm.installer.test_library_status',return_value={'count':0}):
            self.assertFalse(services.status()['connection'])

    def test_base_install_selects_default_through_existing_zip_gate(self):
        services = self.make_services()
        with patch('Shared.bull_llm.pack_library_ui.install_archives',return_value=True) as install, \
             patch('Shared.bull_llm.evaluation.pack_selection.PackSelection'):
            self.assertTrue(services.install_base())
        self.assertTrue(install.call_args.kwargs['select_default'])
        self.assertEqual(len(install.call_args.args[2]),4)

    def test_completion_uses_private_atomic_state_not_public_settings(self):
        services = self.make_services()
        with patch('Shared.bull_llm.storage.atomic_json') as write, patch('Shared.bull_llm.client_launcher.materialize'):
            services.complete({'ok':True,'summary':'3/3'},{'connection':False,'packs':{'count':0}})
        self.assertEqual(write.call_args.args[0].parts[-2:],('Runtime','installation_state.json'))
        self.assertEqual(write.call_args.args[1]['status'],'complete')
        import sys
        self.assertEqual(write.call_args.args[1]['python_executable'],sys.executable)


def run_suite(core):
    SetupTests.core = core
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in (SetupTests,InstallerFlowTests,InstallerServicesTests))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful(): raise AssertionError('Installation and navigation regression failed')
    return result.testsRun


if __name__ == '__main__':
    import importlib.util
    import sys
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root))
    spec = importlib.util.spec_from_file_location('bull_setup_test_core',root/'bull_client_v0.29.0.1.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    run_suite(core)
