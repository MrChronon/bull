"""Presentation changes: no inference, real desktop writes or visible windows."""
import contextlib
import ctypes
import io
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class ThemeSetupTests(unittest.TestCase):
    core = None

    def test_exact_two_theme_labels(self):
        self.assertEqual(self.core.UI_THEME_LABELS,
                         {'bull_red': 'BULL Red', 'matrix_bright': 'BULL Matrix'})
        self.assertEqual(set(self.core.UI_THEME_PALETTES), {'bull_red', 'matrix_bright'})

    def test_new_names_and_old_matrix_preferences_are_compatible(self):
        for value in ('BULL Matrix', 'Matrix BULL', 'matrix_bull', 'matrix_soft', 'matrix_balanced'):
            self.assertEqual(self.core.normalize_ui_theme(value), 'matrix_bright')
        self.assertEqual(self.core.normalize_ui_theme('BULL Red'), 'bull_red')

    def test_retired_contrast_migrates_but_cannot_be_selected(self):
        self.assertEqual(self.core.normalize_ui_theme('classic'), 'bull_red')
        self.assertIsNone(self.core.normalize_ui_theme('classic', default=None))
        self.assertIsNone(self.core.normalize_ui_theme('high_contrast', default=None))

    def test_menu_exposes_only_two_schemes(self):
        with patch.object(self.core, 'ui_header'), patch.object(self.core, 'ui_menu_item') as item, \
             patch.object(self.core, 'read_user_input', side_effect=['0']):
            self.core.appearance_menu()
        self.assertEqual([call.args[0] for call in item.call_args_list], ['1', '2', '3', '0'])
        self.assertEqual([call.args[1] for call in item.call_args_list][1:3], ['BULL Red', 'BULL Matrix'])

    def test_persisted_theme_refreshes_owned_shortcuts(self):
        previous = self.core.UI_THEME
        try:
            with patch.object(self.core, 'save_ui_theme'), patch.object(self.core, 'refresh_theme_shortcuts') as refresh:
                self.core.set_ui_theme('BULL Matrix')
                refresh.assert_called_once_with('matrix_bright')
        finally:
            self.core.set_ui_theme(previous, persist=False)

    def test_loading_theme_does_not_create_shortcuts(self):
        previous = self.core.UI_THEME
        try:
            with patch.object(self.core, 'refresh_theme_shortcuts') as refresh:
                self.core.set_ui_theme('BULL Red', persist=False)
                refresh.assert_not_called()
        finally:
            self.core.set_ui_theme(previous, persist=False)

    def installer(self, answers, language='en', theme=None):
        from Shared.bull_llm.installer import run_installer
        events = []
        core = Mock()
        core.read_user_input.side_effect = answers
        core.save_ui_language.side_effect = lambda value: events.append(('language', value))
        core.set_ui_theme.side_effect = lambda value, **kwargs: events.append(('theme', value))
        services = Mock()
        services.skip_packs.side_effect = lambda: events.append(('packs', None))
        services.verify.return_value = {'ok': True, 'summary': '18/18'}
        services.status.return_value = {'connection': False, 'packs': {'count': 0}}
        self.assertEqual(run_installer(core, services, language=language, theme=theme), 0)
        return core, events

    def test_installer_chooses_theme_before_packs(self):
        core, events = self.installer(['2', '0', '0', '0'])
        self.assertEqual(events[:3], [('language', 'en'), ('theme', 'matrix_bright'), ('packs', None)])

    def test_supplied_theme_is_not_prompted_twice(self):
        core, events = self.installer(['0', '0', '0'], theme='bull_red')
        self.assertEqual(events[1], ('theme', 'bull_red'))
        self.assertEqual(core.read_user_input.call_count, 3)

    def test_invalid_theme_choice_cannot_advance_setup(self):
        core, events = self.installer(['classic', '4', '1', '0', '0', '0'])
        self.assertEqual(events[1], ('theme', 'bull_red'))
        self.assertEqual(core.read_user_input.call_count, 6)

    def test_language_precedes_theme_in_unlocalized_start(self):
        core, events = self.installer(['2', '2', '0', '0', '0'], language=None)
        self.assertEqual(events[:2], [('language', 'ru'), ('theme', 'matrix_bright')])

    def test_setup_bootstrap_has_theme_before_python_preflight(self):
        source = (ROOT / 'Setup.ps1').read_text(encoding='utf-8-sig')
        self.assertLess(source.index("if (-not $Theme)"), source.index('function Find-Python'))
        self.assertIn("'--theme',$Theme", source)
        self.assertNotIn('без установки сервера и прав администратора', source)
        self.assertNotIn('no server installation or administrator rights', source)

    def test_native_setup_and_client_have_portable_entrypoints(self):
        for name in ('Setup.exe', 'Setup/BULL.launcher.bin'):
            self.assertEqual((ROOT / name).read_bytes()[:2], b'MZ')
        # Full diagnostics also runs after Setup has materialized the client.
        # Archive layout is checked separately by the public release audit.
        from Shared.bull_llm.client_launcher import verify_installed
        if (ROOT/'BULL.exe').exists() or (ROOT/'Runtime/installation_state.json').is_file():
            verify_installed(ROOT)
        self.assertIn('Setup.exe', (ROOT / 'Setup.cmd').read_text())
        self.assertFalse((ROOT / 'Install-BULL-v0.29.0.1.cmd').exists())

    def test_native_launcher_has_one_terminal_policy_for_both_roles(self):
        source = (ROOT / 'Tools/BullLauncher.cs').read_text()
        self.assertIn('"--window new --size 120,52 new-tab', source)
        self.assertIn('"Setup.ps1"', source)
        self.assertIn('"BULL-v0.29.0.1.ps1"', source)
        self.assertNotIn('Verb = "runas"', source)
        console_source = (ROOT / 'BULL-v0.29.0.1.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('[Math]::Min(52, $max.Height)', console_source)

    def test_installer_launches_same_executable_as_shortcut(self):
        from Shared.bull_llm.installer import InstallationServices
        core = Mock(__file__=str(ROOT / 'bull_client_v0.29.0.1.py'))
        with patch('Shared.bull_llm.installer.os.startfile') as start:
            InstallationServices(core).launch()
        start.assert_called_once_with(str(ROOT / 'BULL.exe'))

    def test_console_font_configuration_is_shared(self):
        core_source = (ROOT / 'bull_client_v0.29.0.1.py').read_text(encoding='utf-8-sig')
        installer_source = (ROOT / 'Tools/install_bull.py').read_text()
        self.assertTrue('configure_console_presentation()' in core_source, 'Main must normalize the console')
        self.assertIn('core.configure_console_presentation()', installer_source)

    def test_console_font_never_changes_redirected_output(self):
        from Shared.bull_llm import console_presentation
        with patch.object(console_presentation.sys, 'stdout', io.StringIO()):
            self.assertFalse(console_presentation.configure_font())

    def test_console_font_never_overrides_windows_terminal_profile(self):
        from Shared.bull_llm import console_presentation
        stream = Mock(); stream.isatty.return_value = True
        with patch.dict(os.environ, {'WT_SESSION': 'fixture'}), patch.object(console_presentation.sys, 'stdout', stream):
            self.assertFalse(console_presentation.configure_font())

    def test_console_font_api_failure_is_optional(self):
        from Shared.bull_llm import console_presentation
        stream = Mock(); stream.isatty.return_value = True
        with patch.dict(os.environ, {'WT_SESSION': ''}), patch.object(console_presentation.sys, 'stdout', stream), \
             patch.object(ctypes.windll, 'kernel32', SimpleNamespace()):
            self.assertFalse(console_presentation.configure_font())

    def test_console_mark_resolution_and_escape_budget(self):
        from Shared.bull_llm import terminal_ui
        art = terminal_ui._load_console_mark()
        plain = terminal_ui._SGR_ESCAPE_RE.sub('', art)
        self.assertEqual(len(plain.splitlines()), 24)
        self.assertTrue(all(row == ' ' * 48 for row in plain.splitlines()))
        self.assertLess(len(art), 32 * 1024)

    def test_shortcut_sync_uses_fixed_script_and_no_shell(self):
        from Shared.bull_llm.desktop_theme import sync_shortcuts
        with patch('Shared.bull_llm.desktop_theme.subprocess.run') as run:
            run.return_value.returncode = 0
            self.assertTrue(sync_shortcuts(ROOT, 'matrix_bright'))
        args = run.call_args.args[0]
        self.assertIn('-UpdateExistingOnly', args)
        self.assertEqual(args[args.index('-Theme') + 1], 'matrix_bright')
        self.assertFalse(run.call_args.kwargs.get('shell', False))

    def test_shortcut_sync_failure_cannot_break_application(self):
        from Shared.bull_llm.desktop_theme import sync_shortcuts
        with patch('Shared.bull_llm.desktop_theme.subprocess.run', side_effect=OSError('fixture')):
            self.assertFalse(sync_shortcuts(ROOT, 'bull_red'))

    def test_shortcut_script_updates_only_owned_links(self):
        source = (ROOT / 'Tools/Update-BULL-Shortcuts.ps1').read_text()
        self.assertIn('$UpdateExistingOnly', source)
        self.assertIn('$ownedTargets', source)
        self.assertIn('SHChangeNotify', source)
        self.assertNotIn('IconCache.db', source)


def run_suite(core):
    ThemeSetupTests.core = core
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ThemeSetupTests))
    if not result.wasSuccessful():
        raise AssertionError('Theme / Setup presentation contracts failed')
    return result.testsRun


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    from Apps._bootstrap import load_compat_core
    run_suite(load_compat_core())
