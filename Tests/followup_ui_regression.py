"""User-reported terminal/navigation failures; no user profile or model API writes."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class FollowupUiTests(unittest.TestCase):
    core = None

    def setUp(self):
        from Shared.bull_llm.i18n import set_language
        set_language('ru')

    def test_terminal_mark_emits_bounded_complete_rows_before_wordmark(self):
        from Shared.bull_llm import terminal_ui as ui
        core = Mock(_COLOR_ENABLED=True, UI_THEME='bull_red')
        writes = []
        with patch.object(ui, 'print', side_effect=lambda *v, **kw: writes.append(
                ''.join(map(str, v)) + kw.get('end', '\n'))):
            ui.render_page_mark(core)
        self.assertLessEqual(max(map(len, writes)), 2048)
        expected = ui._theme_console_mark(ui._load_console_mark(), 'bull_red')
        self.assertEqual(''.join(writes), expected + ui._WORDMARK + '\n')
        self.assertEqual(len(writes), 25)

    def test_home_has_no_pack_readiness_but_keeps_integrity_and_connection(self):
        from Shared.bull_llm import terminal_ui as ui
        with patch.object(self.core, 'ui_header'), patch.object(self.core, 'ui_status_strip') as strip, \
                patch.object(self.core, 'read_user_input', return_value='0'):
            self.assertEqual(ui.home_menu(self.core, 'offline', '18/18'), 'exit')
        self.assertEqual([row[0] for row in strip.call_args.args[0]], ['Целостность', 'Соединение'])

    def test_empty_session_does_not_request_live_model_or_show_context(self):
        out = io.StringIO()
        with patch.object(self.core, 'ui_header'), \
                patch.object(self.core, 'telemetry_snapshot', side_effect=AssertionError('No active chat')), \
                contextlib.redirect_stdout(out):
            self.core.dashboard(None, 'think', {'model':'example','num_predict':3200}, True,
                ROOT/'unused.json', {}, [], '', [], {}, backend_ready=True)
        self.assertIn('Чат ещё не начат', out.getvalue())
        self.assertNotIn('КОНТЕКСТ', out.getvalue())
        self.assertNotIn('ТЕКУЩАЯ СЕССИЯ', out.getvalue())

    def test_repeated_result_menu_clears_but_first_draw_keeps_summary(self):
        with patch.object(self.core, 'read_user_input', side_effect=['','bad','0']), \
                patch.object(self.core, 'clear_console') as clear, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.core.benchmark_result_menu(), '/home')
        self.assertEqual(clear.call_count, 2)

    def test_author_workshop_route_is_executed_and_returns_to_library(self):
        from Shared.bull_llm import pack_library_ui as ui
        from Shared.bull_llm.evaluation.pack_library import PackLibrary
        with tempfile.TemporaryDirectory() as directory:
            core = Mock(__file__=str(ROOT/'client.py'))
            core.benchmark_pack_library.return_value = PackLibrary(Path(directory), self.core.benchmark_registry_policy())
            core.read_user_input.side_effect = ['6','0']
            with patch('Shared.bull_llm.author_workshop_ui.workshop_menu') as workshop:
                self.assertFalse(ui.library_menu(core))
            workshop.assert_called_once_with(core)

    def test_library_root_comes_from_current_user_not_bundled_settings(self):
        from Shared.bull_llm.evaluation.pack_library import default_pack_library_root
        for name in ('User_A','User_B'):
            with patch.dict(os.environ, {'LOCALAPPDATA':str(ROOT/name)}):
                self.assertEqual(default_pack_library_root(platform='win32'), ROOT/name/'BULL'/'BenchmarkPacks')

    def test_real_author_workshop_can_create_and_validate_from_library(self):
        from Shared.bull_llm.pack_library_ui import library_menu
        from Shared.bull_llm.evaluation.pack_library import PackLibrary
        with tempfile.TemporaryDirectory() as directory:
            core = Mock(__file__=str(ROOT/'client.py'))
            core.benchmark_pack_library.return_value = PackLibrary(Path(directory), self.core.benchmark_registry_policy())
            core.read_user_input.side_effect = ['6','1','ui_starter','','4','','0','0']
            self.assertFalse(library_menu(core))
            self.assertTrue((Path(directory)/'Workspaces').is_dir())
            rendered = ' '.join(str(c) for c in core.ui_print.call_args_list)
            self.assertIn('Создано:', rendered)
            self.assertIn('PASS', rendered)

    def test_pack_browser_never_changes_run_selection(self):
        from Shared.bull_llm.pack_library_ui import installed_pack_browser
        from Shared.bull_llm.evaluation.pack_library import PackLibrary
        from Shared.bull_llm.evaluation.pack_selection import PackSelection
        with tempfile.TemporaryDirectory() as directory:
            library = PackLibrary(Path(directory), self.core.benchmark_registry_policy())
            library.install_zip(ROOT/'BasePacks/bull_chat_core@1.0.0.zip')
            selection = PackSelection(library)
            selection.select('bull_chat_core','1.0.0')
            before = selection.path.read_bytes()
            core = Mock()
            core.benchmark_pack_library.return_value = library
            core.read_user_input.side_effect = ['1','n','p','0','0']
            installed_pack_browser(core)
            self.assertEqual(selection.path.read_bytes(), before)
            rendered = ' '.join(str(c) for c in core.ui_print.call_args_list)
            self.assertIn('dialogue_state', rendered)
            self.assertIn('Только просмотр', rendered)

    def test_diagnostics_back_never_runs_checks(self):
        from Shared.bull_llm.diagnostics_ui import diagnostics_menu
        core = Mock()
        core.read_user_input.return_value = '0'
        with patch('Shared.bull_llm.installer.InstallationServices') as services:
            diagnostics_menu(core)
        services.assert_not_called()
        core.selftest.assert_not_called()

    def test_diagnostics_basic_is_not_full_regression(self):
        from Shared.bull_llm.diagnostics_ui import diagnostics_menu
        core = Mock()
        core.read_user_input.side_effect = ['1','','0']
        with patch('Shared.bull_llm.installer.InstallationServices') as services:
            diagnostics_menu(core, 'owned-tunnel')
        core.selftest.assert_called_once_with('owned-tunnel')
        services.assert_not_called()

    def test_diagnostics_full_uses_installer_verification(self):
        from Shared.bull_llm.diagnostics_ui import diagnostics_menu
        core = Mock()
        core.read_user_input.side_effect = ['2','','0']
        with patch('Shared.bull_llm.installer.InstallationServices') as services:
            services.return_value.verify.return_value = {'ok':True,'summary':'1/1'}
            diagnostics_menu(core)
        services.return_value.verify.assert_called_once_with()
        core.selftest.assert_not_called()

    def test_russian_internal_bin_is_not_mislabelled_as_windows_recycle_bin(self):
        from Shared.bull_llm import pack_library_ui as ui
        from Shared.bull_llm.evaluation.pack_library import PackLibrary
        with tempfile.TemporaryDirectory() as directory:
            core = Mock(__file__=str(ROOT/'client.py'))
            core.benchmark_pack_library.return_value = PackLibrary(Path(directory), self.core.benchmark_registry_policy())
            core.read_user_input.return_value = '0'
            ui.library_menu(core)
        descriptions = '\n'.join(str(c) for c in core.ui_menu_item.call_args_list)
        self.assertIn('корзину BULL', descriptions)
        self.assertNotIn('Перенос в Trash', descriptions)


def run_suite(core):
    FollowupUiTests.core = core
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FollowupUiTests))
    if not result.wasSuccessful():
        raise AssertionError('Follow-up UI regression failed')
    return result.testsRun


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    from Apps._bootstrap import load_compat_core
    run_suite(load_compat_core())
