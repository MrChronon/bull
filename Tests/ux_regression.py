"""Offline UX contracts: navigation, explicit trust and release-independent settings."""
import contextlib
import base64
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class _RainFixture:
    """Event-loop/canvas fixture: no desktop, random generator or model needed."""

    def __init__(self):
        self.items = {}; self.timers = {}; self.cancelled = []; self.destroyed = False

    def create_text(self, *coords, **options):
        item = len(self.items) + 1
        self.items[item] = dict(coords=coords, **options)
        return item

    def coords(self, item, *coords): self.items[item]['coords'] = coords
    def itemconfigure(self, item, **options): self.items[item].update(options)
    def after(self, delay, callback):
        token = f'timer-{len(self.timers)}'
        self.timers[token] = (delay, callback)
        return token
    def after_cancel(self, token):
        self.cancelled.append(token); self.timers.pop(token, None)
    def update_idletasks(self): pass
    def update(self): pass
    def destroy(self): self.destroyed = True


class UXTests(unittest.TestCase):
    core = None

    def setUp(self):
        # Existing behavior contracts are asserted in the original Russian UI.
        # Dedicated tests below cover the new English interface explicitly.
        from Shared.bull_llm.i18n import set_language
        set_language('ru')

    def inputs(self, values):
        return patch.object(self.core, 'read_user_input', side_effect=values)

    def test_home_exposes_five_primary_tasks_and_additional_tools(self):
        out = io.StringIO()
        with patch.object(self.core, 'clear_console'), self.inputs(['/backend import "C:/My Config.JSON"']), contextlib.redirect_stdout(out):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), '/backend import "C:/My Config.JSON"')
        text=out.getvalue()
        for label in ('Тестирование моделей','Чат с моделью','Настройки соединения программы','Настройки тестов','Настройки программы'):
            self.assertIn(label,text)
        self.assertNotIn('Команда /',text)
        self.assertNotIn('MATRIX NODE', out.getvalue())
        self.assertIn('[5]', out.getvalue())
        self.assertIn('[6] Дополнительно', out.getvalue())

    def test_home_routes_chat_and_connections(self):
        with patch.object(self.core, 'clear_console'), self.inputs(['2', '2']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'load')
        with patch.object(self.core, 'clear_console'), self.inputs(['4']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'connections')

    def test_empty_home_input_never_starts_chat(self):
        with patch.object(self.core, 'clear_console'), self.inputs(['', 'unknown text', '0']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'exit')

    def test_selection_rejects_zero_negative_and_out_of_range(self):
        from Shared.bull_llm.terminal_ui import selection
        for value in ('0', '-1', '4', 'foo', ''):
            self.assertIsNone(selection(value, ['a', 'b', 'c']))
        self.assertEqual(selection('2', ['a', 'b']), 'b')

    def test_additional_status_and_command_reference_offline(self):
        with patch.object(self.core, 'clear_console'), self.inputs(['6','1']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), '/dashboard')
        with patch.object(self.core, 'clear_console'), self.inputs(['6','4']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), '/help all')
        with patch.object(self.core, 'clear_console'), self.inputs(['/profile import-tested "C:/Test A.JSON"']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), '/profile import-tested "C:/Test A.JSON"')

    @contextlib.contextmanager
    def menu_items(self, values):
        items = []
        with patch.object(self.core, 'clear_console'), patch.object(self.core, 'ui_header'), \
             patch.object(self.core, 'ui_menu_item', side_effect=lambda key, *args: items.append(str(key))), \
             self.inputs(values), contextlib.redirect_stdout(io.StringIO()):
            yield items

    def test_compare_has_one_pack_run_and_no_duplicate_library_entry(self):
        with self.menu_items(['0']) as items:
            self.assertEqual(self.core.startup_benchmark_wizard(), ('/home', False))
        self.assertEqual(items, ['1', '2', '3', '4', '5', 'P', 'L', '?', '0'])

    def test_advanced_keeps_unique_tools_not_legacy_suites_or_command_prompt(self):
        with self.menu_items(['0']) as items:
            self.assertEqual(self.core.benchmark_advanced_menu(), ('__benchmark_menu__', False))
        self.assertEqual(items, ['1', '2', '3', '4', '5', '6', '7', 'S', 'L', '?'])
        with self.menu_items(['hello model', '2']), patch.object(self.core.time, 'sleep'):
            self.assertEqual(self.core.benchmark_advanced_menu(), ('/bench single', True))

    def test_home_named_shortcuts_share_the_slash_dispatcher(self):
        for shortcut, command in [('backend', '/backend'), ('status', '/dashboard'), ('appearance', '/ui')]:
            with self.menu_items([shortcut]):
                self.assertEqual(self.core.startup_home_menu('offline', 'OK'), command)

    def test_backend_menu_keeps_runtime_tools_without_duplicate_connections(self):
        with self.menu_items(['0']) as items:
            self.assertIsNone(self.core.backend_runtime_menu())
        self.assertEqual(items, [str(index) for index in range(1, 12)] + ['0'])
        with self.menu_items(['8']), patch.object(self.core, 'backend_setup_wizard', return_value=True) as wizard:
            self.assertEqual(self.core.backend_runtime_menu(), '/remote reconnect')
            wizard.assert_called_once_with()
        with self.menu_items(['9', '', '0']), patch.object(self.core, 'backend_doctor') as doctor:
            self.assertIsNone(self.core.backend_runtime_menu())
            doctor.assert_called_once_with()

    def test_backend_renumbered_portable_actions_preserve_paths(self):
        with self.menu_items(['10', '', '0']), patch.object(self.core, 'backend_export_config', return_value=Path('portable.json')) as export:
            self.assertIsNone(self.core.backend_runtime_menu())
            export.assert_called_once_with()
        with self.menu_items(['11', '"C:/My Config.JSON"', '', '0']), \
             patch.object(self.core, 'backend_import_config', return_value=Path('portable.json')) as import_config:
            self.assertIsNone(self.core.backend_runtime_menu())
            import_config.assert_called_once_with('C:/My Config.JSON')

    def test_library_has_dense_numbers_and_workshop_route(self):
        from Shared.bull_llm import pack_library_ui
        store = SimpleNamespace(library=SimpleNamespace(root=Path('SyntheticPacks'),scan=lambda:[]), snapshot=lambda: None)
        with patch.object(pack_library_ui, 'PackSelection', return_value=store), \
             patch.object(self.core, 'benchmark_pack_library', return_value=store.library):
            for choose, expected in [(False, ['1', '2', '3', '4', '5', '6', '7', '0']),
                                     (True, ['T', '0'])]:
                with self.menu_items(['0']) as items:
                    self.assertFalse(pack_library_ui.library_menu(self.core, choose=choose))
                self.assertEqual(items, expected)
            with self.menu_items(['6', '0']), \
                 patch('Shared.bull_llm.author_workshop_ui.workshop_menu') as workshop:
                self.assertFalse(pack_library_ui.library_menu(self.core))
                workshop.assert_called_once_with(self.core)
            store.snapshot = lambda: {'identity': 'fixture@1.0.0', 'selected_cases': 1, 'total_cases': 1}
            with self.menu_items(['']):
                self.assertTrue(pack_library_ui.library_menu(self.core, choose=True))

    def test_onboarding_cannot_run_hidden_library_actions(self):
        from Shared.bull_llm import pack_library_ui
        from unittest.mock import Mock
        library = SimpleNamespace(root=Path('SyntheticPacks'), scan=Mock(side_effect=AssertionError('hidden removal')))
        store = SimpleNamespace(library=library, snapshot=lambda: None,
                                read=lambda: {'onboarding_complete': False}, finish_onboarding=Mock())
        with patch.object(pack_library_ui, 'PackSelection', return_value=store), \
             patch.object(self.core, 'benchmark_pack_library', return_value=library), \
             self.menu_items(['4', '', '5', '', '6', '', '0']) as items, \
             patch('Shared.bull_llm.author_workshop_ui.workshop_menu') as workshop:
            self.assertFalse(pack_library_ui.library_menu(self.core, onboarding=True))
        library.scan.assert_not_called()
        workshop.assert_not_called()
        store.finish_onboarding.assert_called_once_with()
        self.assertEqual(set(items), {'0', '1', '2', '3'})

    def test_removed_menu_functions_have_no_stale_entry_points(self):
        from Shared.bull_llm import connections_ui, terminal_ui
        self.assertFalse(hasattr(self.core, 'menu_text'))
        self.assertFalse(hasattr(terminal_ui, 'command_menu'))
        self.assertFalse(hasattr(connections_ui, 'advanced_menu'))

    def test_simplified_menu_prompts_are_english(self):
        self.core.set_language('en')
        try:
            for menu in (self.core.startup_benchmark_wizard, self.core.benchmark_advanced_menu,
                         self.core.backend_runtime_menu):
                out = io.StringIO()
                prompts = []
                answers = iter(['invalid choice', '0'])
                with patch.object(self.core, 'clear_console'), patch.object(self.core.time, 'sleep'), \
                     patch.object(self.core, 'read_user_input', side_effect=lambda prompt: prompts.append(self.core.tr(prompt)) or next(answers)), \
                     contextlib.redirect_stdout(out):
                    menu()
                rendered = out.getvalue() + ''.join(prompts)
                self.assertFalse(any(('А' <= char <= 'я') or char in 'Ёё' for char in rendered), rendered)
            for choice, suite in [('1', 'language_ru'), ('2', 'language_en'), ('3', 'bilingual')]:
                answers = iter(['L', choice])
                prompts = []
                out = io.StringIO()
                def read(prompt):
                    prompts.append(self.core.tr(prompt))
                    return next(answers)
                with patch.object(self.core, 'clear_console'), patch.object(self.core, 'read_user_input', side_effect=read), \
                     patch('Shared.bull_llm.pack_library_ui.choose_language_pack', return_value=True), \
                     patch.object(self.core, 'benchmark_chat_wizard', return_value='/bench ' + suite + ' all') as wizard, \
                     contextlib.redirect_stdout(out):
                    self.assertEqual(self.core.benchmark_advanced_menu(), ('/bench ' + suite + ' all', True))
                    wizard.assert_called_once_with(suite_override=suite)
                rendered = out.getvalue() + ''.join(prompts)
                self.assertFalse(any(('А' <= char <= 'я') or char in 'Ёё' for char in rendered), rendered)
        finally:
            self.core.set_language('ru')

    def test_startup_pixel_bull_is_compact_and_drawn_once(self):
        from Shared.bull_llm import terminal_ui
        out = io.StringIO()
        with patch.object(self.core, '_COLOR_ENABLED', True), patch.object(terminal_ui, '_startup_mark_shown', False), patch.object(
                self.core, 'matrix'), patch.object(self.core, 'white'), contextlib.redirect_stdout(out):
            self.assertTrue(terminal_ui.render_startup_mark(self.core))
            self.assertFalse(terminal_ui.render_startup_mark(self.core))
        text = out.getvalue()
        plain = terminal_ui._SGR_ESCAPE_RE.sub('', text)
        self.assertIn('\x1b[', text)
        self.assertEqual(text.count('B U L L  //  Benchmarking & Usage of Local Language Models'), 1)
        self.assertNotIn('\x1b', plain)
        art = terminal_ui._load_console_mark()
        self.assertIsNotNone(art)
        art_plain = terminal_ui._SGR_ESCAPE_RE.sub('', art)
        self.assertLessEqual(len(art_plain.splitlines()), 24)
        self.assertLessEqual(max(map(len, art_plain.splitlines())), 48)
        self.assertLessEqual(len(plain.splitlines()), 27)

    def test_console_bull_uses_only_spaces_for_coloured_pixels(self):
        from Shared.bull_llm import terminal_ui
        art = terminal_ui._load_console_mark()
        self.assertIsNotNone(art)
        plain = terminal_ui._SGR_ESCAPE_RE.sub('', art)
        self.assertEqual(len(plain.splitlines()), 24)
        self.assertTrue(all(row == ' ' * 48 for row in plain.splitlines()))
        self.assertTrue(art.isascii())

    def test_console_bull_resets_background_at_every_row_boundary(self):
        from Shared.bull_llm import terminal_ui
        for row in terminal_ui._load_console_mark().splitlines():
            self.assertTrue(row.startswith('\x1b[0m'))
            self.assertTrue(row.endswith('\x1b[0m'))
            self.assertIn('\x1b[48;2;', row)
        for theme in ('bull_red', 'matrix_bright', 'classic'):
            art = terminal_ui._theme_console_mark(terminal_ui._load_console_mark(), theme)
            self.assertTrue(all(row.endswith('\x1b[0m') for row in art.splitlines()))

    def test_console_bull_without_colours_has_portable_ascii_silhouette(self):
        from Shared.bull_llm import terminal_ui
        out = io.StringIO()
        with patch.object(self.core, '_COLOR_ENABLED', False), contextlib.redirect_stdout(out):
            terminal_ui.render_page_mark(self.core)
        text = out.getvalue()
        self.assertNotIn('\x1b', text)
        self.assertTrue(text.isascii())
        self.assertIn('#', text)
        self.assertIn('B U L L', text)

    def test_console_bull_rejects_untrusted_controls_and_invalid_pixels(self):
        from Shared.bull_llm import terminal_ui
        valid = terminal_ui._load_console_mark()
        self.assertIsNotNone(valid)
        for payload in ('\x1b]0;untrusted\x07' + valid,
                        valid.replace(' ', '\u2588', 1),
                        valid.replace('48;2;', '38;2;', 1),
                        valid.replace('\n', '\v', 1),
                        valid.replace('\x1b[0m', '', 1),
                        valid.replace('48;2;', '48;2;999;', 1)):
            fake = SimpleNamespace(read_text=lambda **kwargs: base64.b64encode(payload.encode('utf-8')).decode('ascii'))
            with patch.object(terminal_ui, '_CONSOLE_ASSET', fake):
                self.assertIsNone(terminal_ui._load_console_mark())

    def test_startup_pixel_bull_falls_back_if_console_asset_is_missing(self):
        from Shared.bull_llm import terminal_ui
        out = io.StringIO()
        with patch.object(self.core, '_COLOR_ENABLED', True), patch.object(terminal_ui, '_startup_mark_shown', False), patch.object(
                terminal_ui, '_load_console_mark', return_value=None), patch.object(
                self.core, 'matrix'), patch.object(self.core, 'white'), contextlib.redirect_stdout(out):
            self.assertTrue(terminal_ui.render_startup_mark(self.core))
        text = out.getvalue()
        for row in terminal_ui.BULL_PIXEL_ART:
            self.assertIn(row, text)
        self.assertTrue(text.isascii())

    def test_versioned_startup_window_uses_png_and_truthful_stage_progress(self):
        from Shared.bull_llm import startup_window

        self.assertEqual(startup_window.splash_image_path('v0.29.0.1').name, 'splash-v0.29.0.1.png')
        self.assertEqual(startup_window._progress(2, 3), (2, 3, 2 / 3))
        self.assertEqual(startup_window._progress(9, 3), (3, 3, 1.0))
        self.assertEqual(startup_window._stage_label('run\n\tregression'), 'run regression')
        self.assertEqual(
            startup_window._stage_parts('Run suite\nCurrent suite: Tests/benchmark_regression.py'),
            ('Run suite', 'Current suite: Tests/benchmark_regression.py'),
        )
        self.assertEqual(
            startup_window._stage_parts('Running offline regression\nCurrent check: scorer contract'),
            ('Running offline regression', 'Current check: scorer contract'),
        )
        self.core.set_language('en')
        self.assertEqual(
            self.core._startup_stage_for_ui('Запуск офлайн-регрессии\nТекущая проверка: scorer contract'),
            'Running offline regression\nCurrent check: scorer contract',
        )
        self.core.set_language('ru')

        events = []
        class FakeWindow:
            def update(self, stage, current, total):
                events.append(('update', stage, current, total)); return True
            def close(self):
                events.append(('close',))
        with patch.object(startup_window, '_create_window', return_value=FakeWindow()) as create:
            splash = startup_window.open_startup_window('v0.29.0.1', 'Run regression', 2, 3)
        create.assert_called_once_with('v0.29.0.1', 'Run regression', 2, 3, theme='bull_red')
        splash.update('Regression passed', 3, 3)
        splash.close()
        self.assertEqual(events, [('update', 'Regression passed', 3, 3), ('close',)])

    def test_startup_artwork_selection_is_theme_bound_and_cannot_accept_paths(self):
        from Shared.bull_llm import startup_window
        for theme in ('matrix_bright', 'matrix_balanced', 'matrix_soft'):
            self.assertEqual(startup_window.splash_image_path('v0.29.0.1', theme).name,
                             'splash-matrix-v0.29.0.1.png')
        for theme in ('bull_red', 'classic', None, '../../matrix', 'https://example.invalid/image.png'):
            path = startup_window.splash_image_path('../v0.29.0.1', theme)
            self.assertEqual(path.parent, startup_window._ASSET_DIR)
            self.assertNotIn('matrix', path.name)

    def test_saved_matrix_theme_and_live_red_switch_reach_the_startup_window(self):
        from Shared.bull_llm import startup_window
        previous = self.core.UI_THEME
        try:
            with tempfile.TemporaryDirectory() as tmp, \
                 patch.object(self.core, 'ui_settings_path', return_value=Path(tmp)/'ui_settings.json'), \
                 patch.dict(os.environ, {'BULL_UI_THEME': ''}), \
                 patch.object(startup_window, 'open_startup_window') as opened:
                self.core.set_ui_theme('Matrix BULL')
                self.core.set_ui_theme('bull_red', persist=False)
                self.core.initialize_ui_theme()
                self.core.open_startup_verification_window()
                self.assertEqual(opened.call_args.kwargs['theme'], 'matrix_bright')
                self.core.set_ui_theme('bull_red')
                self.core.open_startup_verification_window()
                self.assertEqual(opened.call_args.kwargs['theme'], 'bull_red')
                with patch.dict(os.environ, {'BULL_UI_THEME': 'matrix-soft'}):
                    self.core.initialize_ui_theme()
                    self.core.open_startup_verification_window()
                    self.assertEqual(opened.call_args.kwargs['theme'], 'matrix_bright')
        finally:
            self.core.set_ui_theme(previous, persist=False)

    def test_matrix_native_splash_styles_image_frame_and_real_progress_together(self):
        from Shared.bull_llm import startup_window
        widgets = []
        class Widget:
            def __init__(self, *args, **kwargs):
                self.options = kwargs; self.rect = {}; self.destroyed = False
                widgets.append(self)
            def configure(self, **kwargs): self.options.update(kwargs)
            def pack(self, **kwargs): pass
            def overrideredirect(self, *args): pass
            def attributes(self, *args): pass
            def update_idletasks(self): pass
            def update(self): pass
            def geometry(self, *args): pass
            def winfo_screenwidth(self): return 1920
            def winfo_screenheight(self): return 1080
            def winfo_reqwidth(self): return 640
            def winfo_reqheight(self): return 800
            def width(self): return 1254
            def height(self): return 1254
            def subsample(self, *args): return self
            def create_rectangle(self, *args, **kwargs): self.rect = kwargs
            def create_image(self, *args, **kwargs): return 'image'
            def create_text(self, *args, **kwargs): return 'glyph'
            def itemconfigure(self, *args, **kwargs): pass
            def delete(self, *args): pass
            def after(self, *args): return 'timer'
            def after_cancel(self, *args): pass
            def coords(self, *args): self.coordinates = args
            def destroy(self): self.destroyed = True
        tk = SimpleNamespace(**{name: Widget for name in ('Tk', 'Frame', 'Label', 'PhotoImage', 'Canvas')})
        for theme, accent in (('bull_red', '#FF3C52'), ('matrix_bright', '#36FF73'),
                              ('matrix_balanced', '#2DDC69'), ('matrix_soft', '#26B05B')):
            widgets.clear()
            with patch.dict('sys.modules', {'tkinter': tk}), patch.object(Path, 'is_file', return_value=True):
                splash = startup_window.open_startup_window('v0.29.0.1', 'Integrity\nCurrent check: schemas', 9, 18, theme=theme)
            self.assertIsNotNone(splash)
            frame = next(w for w in widgets if 'highlightbackground' in w.options)
            self.assertEqual(frame.options['highlightbackground'], accent)
            self.assertEqual(splash._bar.rect['fill'], accent)
            self.assertEqual(splash._rain is not None, theme != 'bull_red')
            image = next(w for w in widgets if 'file' in w.options)
            self.assertEqual(Path(image.options['file']), startup_window.splash_image_path('v0.29.0.1', theme))
            self.assertIn('50% (9/18)', splash._stage.options['text'])
            self.assertEqual(splash._detail.options['text'], 'Current check: schemas')
            self.assertEqual(splash._bar.coordinates, ('fill', 0, 0, round(splash._width/2), 8))
            self.assertTrue(splash.update('Integrity\nCurrent check: imports', 18, 18))
            self.assertIn('100% (18/18)', splash._stage.options['text'])
            splash.close()
            self.assertTrue(splash._root.destroyed)

    def test_matrix_rain_is_confined_fixed_size_and_independent_of_random_state(self):
        import random
        from Shared.bull_llm import startup_window
        root = canvas = _RainFixture()
        state = random.getstate()
        with patch.object(startup_window.time, 'monotonic', return_value=10):
            rain = startup_window._MatrixRain(root, canvas, width=627, height=627, accent='#36FF73')
        initial = [dict(item) for item in canvas.items.values()]
        self.assertEqual(len(initial), 45)
        for elapsed in (0, 0.4, 1, 10, 10000):
            rain._draw(elapsed)
            self.assertEqual(len(canvas.items), 45)
            for item in canvas.items.values():
                x, y = item['coords']
                self.assertGreaterEqual(x, 627 * .90)
                self.assertLess(x, 627)
                if item['state'] == 'normal':
                    self.assertGreaterEqual(y, 627 * .04)
                    self.assertLessEqual(y, 627 * .94)
                self.assertTrue(item['text'].isascii())
        self.assertNotEqual(initial, list(canvas.items.values()))
        self.assertEqual(random.getstate(), state)
        rain.close()

    def test_matrix_rain_cancels_owned_timer_and_stops_on_render_failure(self):
        from Shared.bull_llm import startup_window
        for failed in (False, True):
            root = canvas = _RainFixture()
            rain = startup_window._MatrixRain(root, canvas, width=627, height=627, accent='#26B05B')
            self.assertEqual(len(root.timers), 1)
            token = rain._timer
            if failed:
                with patch.object(canvas, 'itemconfigure', side_effect=RuntimeError('closed canvas')):
                    rain._tick()
            else:
                rain.close()
            self.assertFalse(root.timers)
            self.assertIn(token, root.cancelled)
            rain._tick(); rain.close()
            self.assertFalse(root.timers)
            self.assertEqual(len(canvas.items), 45)

    def test_splash_idle_pump_keeps_progress_unchanged_and_cleans_up_closed_gui(self):
        from Shared.bull_llm import startup_window
        root = canvas = _RainFixture()
        rain = startup_window._MatrixRain(root, canvas, width=627, height=627, accent='#36FF73')
        stage = SimpleNamespace(configure=lambda **kwargs: None)
        bar = SimpleNamespace(coords=lambda *args: None)
        splash = startup_window._DesktopSplash(root, stage, stage, bar, width=600, rain=rain)
        self.assertTrue(splash.pump())
        self.assertFalse(root.destroyed)
        with patch.object(root, 'update', side_effect=RuntimeError('window closed')):
            self.assertFalse(splash.pump())
        self.assertTrue(root.destroyed)
        self.assertFalse(root.timers)
        self.assertFalse(splash.update('Integrity', 9, 18))
        splash.close()

    def test_startup_stream_pumps_quiet_child_without_inventing_check_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp)/'quiet-check.py'
            child.write_text("import time\ntime.sleep(.35)\nprint('PASS 1/1',flush=True)\n", encoding='utf-8')
            idle = []; lines = []
            code, output, timed_out = self.core._stream_startup_regression(
                child, lines.append, timeout=5, on_idle=lambda: idle.append('pump'))
        self.assertEqual(code, 0)
        self.assertEqual(output, 'PASS 1/1')
        self.assertFalse(timed_out)
        self.assertGreaterEqual(len(idle), 2)
        self.assertEqual(lines, ['PASS 1/1\n'])

    def test_startup_idle_gui_failure_cannot_fail_verification(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp)/'quiet-check.py'
            child.write_text("import time\ntime.sleep(.15)\nprint('PASS 1/1',flush=True)\n", encoding='utf-8')
            callback = Mock(side_effect=RuntimeError('presentation unavailable'))
            code, output, timed_out = self.core._stream_startup_regression(child, timeout=5, on_idle=callback)
        self.assertEqual((code, output, timed_out), (0, 'PASS 1/1', False))
        self.assertTrue(callback.called)

    def test_startup_gate_forwards_idle_pump_without_advancing_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp)/'quiet-check.py'
            child.write_text(
                "import time\nprint('BULL_STARTUP_TOTAL\\t2',flush=True)\n"
                "print('BULL_STARTUP_TEST\\tquiet check',flush=True)\ntime.sleep(.3)\n"
                "print('BULL_STARTUP_COMPLETE\\t1',flush=True)\nprint('PASS 2/2',flush=True)\n",
                encoding='utf-8',
            )
            idle = []; updates = []
            with patch.object(self.core, '_startup_regression_path', return_value=child), \
                 patch.object(self.core, '_startup_regression_cache_path', return_value=Path(tmp)/'cache.json'), \
                 contextlib.redirect_stdout(io.StringIO()):
                result = self.core.run_startup_regression(force=True, progress_callback=lambda *args: updates.append(args),
                                                          idle_callback=lambda: idle.append('pump'))
        self.assertTrue(result['ok'])
        self.assertGreaterEqual(len(idle), 2)
        self.assertEqual([event[1:] for event in updates], [(1, 3), (2, 3), (0, 2), (0, 2), (1, 2), (2, 2)])

    def test_themed_splash_unavailable_does_not_fall_back_to_red_or_block_checks(self):
        from Shared.bull_llm import startup_window
        with patch.object(Path, 'is_file', return_value=False):
            self.assertIsNone(startup_window.open_startup_window('v0.29.0.1', theme='matrix_bright'))
        with patch.dict('sys.modules', {'tkinter': SimpleNamespace(Tk=lambda: (_ for _ in ()).throw(RuntimeError('headless')))}), \
             patch.object(Path, 'is_file', return_value=True):
            self.assertIsNone(startup_window.open_startup_window('v0.29.0.1', theme='matrix_bright'))

    def test_matrix_artwork_is_bundled_and_startup_gate_rejects_its_damage(self):
        from Shared.bull_llm import startup_checks, startup_window
        root = Path(__file__).resolve().parents[1]
        green = startup_window.splash_image_path(self.core.APP_VERSION, 'matrix_bright')
        self.assertEqual(green.read_bytes(), (root/'Assets/Brand/startup-hero-matrix.png').read_bytes())
        self.assertNotEqual(green.read_bytes(), startup_window.splash_image_path(self.core.APP_VERSION).read_bytes())
        gates = dict(startup_checks.checks(root, self.core.APP_VERSION, 'bull_client_v0.29.0.1.py'))
        with patch.object(startup_checks, 'verify_files') as verify:
            gates['Interface and splash asset integrity']()
        self.assertIn(green.relative_to(root).as_posix(), verify.call_args.args[2])
        gates['Startup artwork format']()
        original_read = Path.read_bytes
        def damaged(path):
            return b'invalid PNG' if path == green else original_read(path)
        with patch.object(Path, 'read_bytes', damaged), self.assertRaisesRegex(RuntimeError, 'Splash PNG invalid'):
            gates['Startup artwork format']()

    def test_console_clear_resets_terminal_background_before_main_menu(self):
        out = io.StringIO()
        old_color = self.core._COLOR_ENABLED
        try:
            self.core._COLOR_ENABLED = True
            with contextlib.redirect_stdout(out):
                self.core.clear_console()
            self.assertIn('\033[0m\033[2J\033[3J\033[H', out.getvalue())
        finally:
            self.core._COLOR_ENABLED = old_color

    def test_home_is_english_after_language_choice_and_model_text_is_untouched(self):
        from Shared.bull_llm.i18n import set_language, tr
        out = io.StringIO()
        set_language('en')
        try:
            with patch.object(self.core, 'clear_console'), self.inputs(['0']), contextlib.redirect_stdout(out):
                self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'exit')
            text = out.getvalue()
            self.assertIn('Choose what you want to do', text)
            self.assertIn('Model testing', text)
            self.assertIn('Program settings', text)
            self.assertNotIn('Чем займёмся', text)
            model_text = 'Уникальный ответ модели, который нельзя переводить автоматически.'
            self.assertEqual(tr(model_text), model_text)
        finally:
            set_language('ru')

    def test_english_task_and_connection_menus_do_not_mix_languages(self):
        from Shared.bull_llm.i18n import set_language
        has_cyrillic=lambda value:any(('А' <= char <= 'я') or char in 'Ёё' for char in value)
        set_language('en')
        try:
            out=io.StringIO()
            with patch.object(self.core, 'clear_console'), self.inputs(['0']), contextlib.redirect_stdout(out):
                self.assertEqual(self.core.startup_benchmark_wizard(), ('/home', False))
            self.assertFalse(has_cyrillic(out.getvalue()), out.getvalue())

            out=io.StringIO()
            with patch.object(self.core, 'clear_console'), self.inputs(['0']), contextlib.redirect_stdout(out):
                self.assertIsNone(self.core.connection_menu())
            self.assertFalse(has_cyrillic(out.getvalue()), out.getvalue())
        finally:
            set_language('ru')

    def test_english_more_experimental_and_result_menus_do_not_mix_languages(self):
        from Shared.bull_llm.i18n import set_language
        has_cyrillic=lambda value:any(('А' <= char <= 'я') or char in 'Ёё' for char in value)
        set_language('en')
        try:
            for menu in (self.core.appearance_menu,):
                out=io.StringIO()
                with patch.object(self.core, 'clear_console'), self.inputs(['0']), contextlib.redirect_stdout(out):
                    self.assertIsNone(menu())
                self.assertFalse(has_cyrillic(out.getvalue()), out.getvalue())

            out=io.StringIO()
            with self.inputs(['0']), contextlib.redirect_stdout(out):
                self.assertEqual(self.core.benchmark_result_menu(), '/home')
            self.assertFalse(has_cyrillic(out.getvalue()), out.getvalue())
        finally:
            set_language('ru')

    def test_first_language_menu_persists_english_and_russian(self):
        from Shared.bull_llm.i18n import get_language, set_language
        from Shared.bull_llm import terminal_ui
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / 'ui_settings.json'
            old_path = self.core.ui_settings_path
            try:
                self.core.ui_settings_path = lambda: settings
                for choice, expected in (('1', 'en'), ('2', 'ru')):
                    settings.unlink(missing_ok=True)
                    with patch.object(self.core, 'clear_console'), patch.object(
                            terminal_ui, '_startup_mark_shown', False), patch.object(
                            terminal_ui, 'render_startup_mark', return_value=True), self.inputs([choice]):
                        self.assertEqual(self.core.select_ui_language(), expected)
                    self.assertEqual(get_language(), expected)
                    document = json.loads(settings.read_text(encoding='utf-8'))
                    self.assertEqual(document['language'], expected)
                    self.assertEqual(document['version'], 4)
            finally:
                self.core.ui_settings_path = old_path
                set_language('ru')

    def test_saved_language_skips_startup_question(self):
        from Shared.bull_llm.i18n import get_language, set_language
        with tempfile.TemporaryDirectory() as tmp:
            settings = Path(tmp) / 'ui_settings.json'
            settings.write_text(json.dumps({
                'schema': self.core.UI_THEME_SCHEMA, 'version': 3,
                'theme': 'bull_brand', 'language': 'en',
            }), encoding='utf-8')
            old_path = self.core.ui_settings_path
            try:
                self.core.ui_settings_path = lambda: settings
                with patch.object(self.core, 'read_user_input', side_effect=AssertionError('language prompt repeated')):
                    self.assertEqual(self.core.select_ui_language(), 'en')
                self.assertEqual(get_language(), 'en')
            finally:
                self.core.ui_settings_path = old_path
                set_language('ru')

    def test_english_offline_startup_notice_has_no_russian_fallback(self):
        from Shared.bull_llm.i18n import set_language
        out = io.StringIO()
        set_language('en')
        try:
            with patch.object(self.core, 'load_backend_settings', return_value={'target_mode': 'local'}), \
                    contextlib.redirect_stdout(out):
                self.core.render_startup_connection_result(False)
            text = out.getvalue()
            self.assertIn('No model connection', text)
            self.assertIn('This computer', text)
            self.assertFalse(any(('А' <= char <= 'я') or char in 'Ёё' for char in text), text)
        finally:
            set_language('ru')

    def test_english_connection_and_action_errors_hide_legacy_russian_text(self):
        from Shared.bull_llm.i18n import set_language
        has_cyrillic=lambda value:any(('А' <= char <= 'я') or char in 'Ёё' for char in value)
        out=io.StringIO()
        set_language('en')
        try:
            with patch.object(self.core,'append_client_debug'), patch.object(
                    self.core,'backend_label',return_value='Ollama'), contextlib.redirect_stdout(out):
                self.core.render_runtime_connection_failure(
                    'benchmark',RuntimeError('Локальный Ollama не отвечает на 127.0.0.1:11434.')
                )
                self.core.show_actionable_error(
                    'Ошибка benchmark',RuntimeError('Служебная ошибка старого backend-кода')
                )
            text=out.getvalue()
            self.assertIn('Could not connect to Ollama for the benchmark.',text)
            self.assertIn('Benchmark error:',text)
            self.assertIn('client_debug.log',text)
            self.assertFalse(has_cyrillic(text),text)
        finally:
            set_language('ru')

    def test_english_appearance_and_offline_status_do_not_mix_languages(self):
        from Shared.bull_llm.i18n import set_language
        has_cyrillic=lambda value:any(('А' <= char <= 'я') or char in 'Ёё' for char in value)
        set_language('en')
        try:
            out=io.StringIO()
            with self.inputs(['0']), contextlib.redirect_stdout(out):
                self.assertIsNone(self.core.appearance_menu())
            self.assertFalse(has_cyrillic(out.getvalue()), out.getvalue())

            out=io.StringIO()
            session=self.core.new_session_meta('fixture-model')
            cfg=dict(self.core.THINK,model='fixture-model')
            with patch.object(self.core,'load_backend_settings',return_value={'target_mode':'local'}), \
                    contextlib.redirect_stdout(out):
                self.core.dashboard(None,'think',cfg,True,Path('chat.json'),session,
                                    [],'',[],{},backend_ready=False)
            self.assertFalse(has_cyrillic(out.getvalue()), out.getvalue())
        finally:
            set_language('ru')

    def test_unknown_home_text_not_sent_as_prompt(self):
        with patch.object(self.core, 'clear_console'), self.inputs(['hello model', '0']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'exit')

    def fixture_connection(self):
        import base64, hashlib
        blob = b'public synthetic host key fixture' * 2
        return dict(schema='bull-connection', version=1, id='fixture', name='Fixture',
                    route='direct', transport='ssh', endpoint=dict(host='example.invalid', user='tester', port=22),
                    backend=dict(type='ollama', remote_port=11434),
                    host_public_key='ssh-ed25519 ' + base64.b64encode(blob).decode(),
                    host_key_fingerprint='SHA256:' + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('='))

    def test_vault_is_explicit_and_does_not_copy_key(self):
        from Shared.bull_llm.connections_ui import remember_connection, saved_connections
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = root / 'identity'; key.write_text('DO NOT COPY THIS CONTENT')
            entry = self.fixture_connection(); entry['identity_file'] = str(key)
            with patch('Shared.bull_llm.connections_ui.vault_dir', return_value=root / 'vault'):
                self.assertEqual(saved_connections(self.core), [])
                remember_connection(self.core, entry)
                rows = saved_connections(self.core)
                self.assertEqual(len(rows), 1)
                content = (root / 'vault/fixture.json').read_text(encoding='utf-8')
                self.assertNotIn('DO NOT COPY', content)
                self.assertNotIn('active', content)
                self.assertEqual(rows[0]['identity_file'], str(key))

    def test_changed_host_key_cannot_overwrite_remembered_server(self):
        from Shared.bull_llm.connections_ui import remember_connection
        with tempfile.TemporaryDirectory() as tmp:
            entry = self.fixture_connection(); entry['identity_file'] = str(Path(tmp)/'key')
            Path(entry['identity_file']).touch()
            with patch('Shared.bull_llm.connections_ui.vault_dir', return_value=Path(tmp)/'vault'):
                remember_connection(self.core, entry)
                changed = dict(entry, endpoint=dict(host='other.invalid', port=22, user='tester'))
                with self.assertRaises(ValueError):
                    remember_connection(self.core, changed)

    def test_new_ssh_cancel_does_not_change_settings(self):
        from Shared.bull_llm.connections_ui import new_ssh_connection
        with self.inputs(['0']), patch.object(self.core, 'save_backend_settings') as write:
            self.assertIsNone(new_ssh_connection(self.core))
            write.assert_not_called()

    def test_key_scan_validation_and_fingerprint(self):
        from Shared.bull_llm.connections_ui import scan_host_key
        raw = self.fixture_connection()
        with patch('Shared.bull_llm.connections_ui.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = ('example.invalid '+raw['host_public_key']+'\n').encode()
            key, fingerprint = scan_host_key(self.core, 'example.invalid', 22)
            self.assertEqual(fingerprint, raw['host_key_fingerprint'])
            self.assertEqual(key, raw['host_public_key'])
            self.assertFalse(run.call_args.kwargs.get('shell', False))
            self.assertLessEqual(run.call_args.kwargs['timeout'], 12)
        with self.assertRaises(ValueError):
            scan_host_key(self.core, '-oProxyCommand=bad', 22)

    def test_ssh_alias_resolves_direct_key_profile_without_shell(self):
        from Shared.bull_llm.connections_ui import resolve_ssh_alias
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / 'id_ed25519'; key.touch()
            known = Path(tmp) / 'known_hosts'; known.touch()
            output = (f'host lab\nuser tester\nhostname example.invalid\nport 2222\n'
                      f'identityfile {key}\nuserknownhostsfile {known}\n').encode()
            with patch('Shared.bull_llm.connections_ui.subprocess.run', return_value=SimpleNamespace(
                    returncode=0, stdout=output, stderr=b'')) as run:
                result = resolve_ssh_alias(self.core, 'lab')
            self.assertEqual(result['host'], 'example.invalid')
            self.assertEqual(result['user'], 'tester')
            self.assertEqual(result['port'], 2222)
            self.assertEqual(Path(result['identity_file']), key)
            self.assertEqual(run.call_args.args[0], ['ssh', '-G', '--', 'lab'])
            self.assertFalse(run.call_args.kwargs.get('shell', False))

    def test_ssh_alias_rejects_option_injection_and_proxy_jump(self):
        from Shared.bull_llm.connections_ui import resolve_ssh_alias
        with patch('Shared.bull_llm.connections_ui.subprocess.run') as run:
            with self.assertRaises(ValueError):
                resolve_ssh_alias(self.core, '-oProxyCommand=bad')
            run.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / 'key'; key.touch()
            output = (f'user tester\nhostname example.invalid\nport 22\nidentityfile {key}\n'
                      'proxyjump gateway\n').encode()
            with patch('Shared.bull_llm.connections_ui.subprocess.run', return_value=SimpleNamespace(
                    returncode=0, stdout=output, stderr=b'')):
                with self.assertRaises(ValueError):
                    resolve_ssh_alias(self.core, 'lab')

    def test_known_hosts_match_supports_hashed_entries(self):
        from Shared.bull_llm.connections_ui import known_host_key_matches
        public = self.fixture_connection()['host_public_key']
        line = ('|1|synthetic|hash ' + public + '\n').encode()
        with tempfile.TemporaryDirectory() as tmp:
            known = Path(tmp) / 'known_hosts'; known.touch()
            with patch('Shared.bull_llm.connections_ui.subprocess.run', return_value=SimpleNamespace(
                    returncode=0, stdout=line, stderr=b'')) as run:
                self.assertTrue(known_host_key_matches(public, 'example.invalid', 22, [known]))
            self.assertEqual(run.call_args.args[0][:3], ['ssh-keygen', '-F', 'example.invalid'])
            self.assertFalse(run.call_args.kwargs.get('shell', False))

    def test_ssh_alias_wizard_reuses_open_ssh_trust(self):
        from Shared.bull_llm.connections_ui import new_ssh_alias_connection
        fixture = self.fixture_connection()
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / 'key'; key.touch()
            resolved = dict(alias='lab', host='example.invalid', user='tester', port=22,
                            identity_file=str(key), known_hosts_files=[])
            with self.inputs(['lab', '1']), patch(
                    'Shared.bull_llm.connections_ui.configured_ssh_aliases', return_value=['lab']), patch(
                    'Shared.bull_llm.connections_ui.resolve_ssh_alias', return_value=resolved), patch(
                    'Shared.bull_llm.connections_ui.scan_host_key', return_value=(
                        fixture['host_public_key'], fixture['host_key_fingerprint'])), patch(
                    'Shared.bull_llm.connections_ui.known_host_key_matches', return_value=True), patch(
                    'Shared.bull_llm.connections_ui.install_entry', return_value=fixture) as install:
                self.assertEqual(new_ssh_alias_connection(self.core), fixture)
            self.assertTrue(install.call_args.kwargs['remember'])

    def test_ssh_alias_without_known_host_requires_fingerprint(self):
        from Shared.bull_llm.connections_ui import new_ssh_alias_connection
        fixture = self.fixture_connection()
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / 'key'; key.touch()
            resolved = dict(alias='lab', host='example.invalid', user='tester', port=22,
                            identity_file=str(key), known_hosts_files=[])
            answers = ['lab', fixture['host_key_fingerprint'], '2']
            with self.inputs(answers), patch(
                    'Shared.bull_llm.connections_ui.configured_ssh_aliases', return_value=[]), patch(
                    'Shared.bull_llm.connections_ui.resolve_ssh_alias', return_value=resolved), patch(
                    'Shared.bull_llm.connections_ui.scan_host_key', return_value=(
                        fixture['host_public_key'], fixture['host_key_fingerprint'])), patch(
                    'Shared.bull_llm.connections_ui.known_host_key_matches', return_value=False), patch(
                    'Shared.bull_llm.connections_ui.install_entry', return_value=fixture) as install:
                self.assertEqual(new_ssh_alias_connection(self.core), fixture)
            self.assertFalse(install.call_args.kwargs['remember'])

    def test_agent_summary_distinguishes_test_failures_and_missing_memory(self):
        from Shared.bull_llm.agent_benchmark.reports import terminal_summary
        run = dict(status='success', verification=dict(passed=12, total=12),
                   metrics=dict(success=True, autonomous_success=True, duration_seconds=80, human_interventions=0,
                                tool_calls=8, repeated_tool_calls=3, resources={}),
                   errors=[dict(category='build_test_failure')]*3)
        out=[]; terminal_summary(run, out.append)
        result='\n'.join(out)
        self.assertIn('12/12', result)
        self.assertIn('проверок кода: 3', result)
        self.assertIn('не сбои приложения', result)
        self.assertIn('RAM сервера: нет данных', result)

    def test_ssh_wrong_fingerprint_never_installs(self):
        from Shared.bull_llm.connections_ui import new_ssh_connection
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp)/'identity'; key.touch()
            answers = ['example.invalid', 'tester', '', str(key), '', '', 'SHA256:WRONG']
            with self.inputs(answers), patch('Shared.bull_llm.connections_ui.scan_host_key', return_value=('key', 'SHA256:RIGHT')), patch(
                    'Shared.bull_llm.connections_ui.install_entry') as install:
                with self.assertRaises(ValueError): new_ssh_connection(self.core)
                install.assert_not_called()

    def test_ssh_full_wizard_requires_explicit_confirmation(self):
        from Shared.bull_llm.connections_ui import new_ssh_connection
        fixture = self.fixture_connection()
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp)/'identity'; key.touch()
            for confirmation, expected_calls in [('0', 0), ('', 0), ('1', 1), ('2', 1)]:
                answers = ['example.invalid', 'tester', '', str(key), '', '', fixture['host_key_fingerprint'], confirmation]
                with self.inputs(answers), patch('Shared.bull_llm.connections_ui.scan_host_key', return_value=(
                        fixture['host_public_key'], fixture['host_key_fingerprint'])), patch(
                        'Shared.bull_llm.connections_ui.install_entry') as install:
                    new_ssh_connection(self.core)
                    self.assertEqual(install.call_count, expected_calls)
                    if expected_calls: self.assertEqual(install.call_args.kwargs['remember'], confirmation == '1')

    def test_install_remember_and_activate_in_new_build_with_private_key_reference(self):
        from Shared.bull_llm.connections_ui import install_entry, saved_connections
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); key = root/'identity'; key.write_text('DO NOT COPY KEY BYTES')
            entry = self.fixture_connection(); entry['identity_file'] = str(key)
            old_api = self.core.OLLAMA_API; old_active = self.core.ACTIVE_BACKEND
            old_api2 = self.core.API
            try:
                with patch('Shared.bull_llm.connections_ui.vault_dir', return_value=root/'vault'):
                    for build in ('build1', 'build2'):
                        with patch.object(self.core, 'connection_store_path', return_value=root/build/'Runtime/connections.json'), patch.object(
                                self.core, 'backend_settings_path', return_value=root/build/'backend_settings.json'):
                            if build == 'build2': entry = saved_connections(self.core)[0]
                            imported = install_entry(self.core, entry, remember=True)
                            settings = self.core.load_backend_settings()
                            self.assertEqual(settings['target_mode'], 'remote')
                            self.assertEqual(settings['active'], 'ollama')
                            self.assertEqual(imported['identity_file'], str(key))
                            known = Path(imported['known_hosts_file']).read_text(encoding='ascii')
                            self.assertIn(entry['host_public_key'], known)
                            self.assertEqual(list((root/build/'Runtime').glob('connection-import-*.json')), [])
                            self.assertNotIn('DO NOT COPY', json.dumps(self.core.load_connection_store()))
            finally:
                self.core.OLLAMA_API=old_api; self.core.API=old_api2; self.core.ACTIVE_BACKEND=old_active
                self.core.reset_remote_endpoint_cache()

    def test_missing_private_key_does_not_create_current_store(self):
        from Shared.bull_llm.connections_ui import install_entry
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); entry=self.fixture_connection(); entry['identity_file']=str(root/'absent')
            with patch.object(self.core, 'connection_store_path', return_value=root/'connections.json'), patch.object(
                    self.core, 'save_backend_settings') as write:
                with self.assertRaises(ValueError): install_entry(self.core, entry)
                write.assert_not_called()
                self.assertFalse((root/'connections.json').exists())

    def test_corrupt_vault_entry_does_not_block_valid_entries(self):
        from Shared.bull_llm.connections_ui import saved_connections, remember_connection
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); entry=self.fixture_connection(); entry['identity_file']=str(root/'key')
            with patch('Shared.bull_llm.connections_ui.vault_dir', return_value=root):
                remember_connection(self.core, entry)
                (root/'broken.json').write_text('[')
                self.assertEqual(len(saved_connections(self.core)), 1)

    def test_agent_simple_default_setup_and_cancel_preserve_previous(self):
        from types import SimpleNamespace
        from copy import deepcopy
        from Shared.bull_llm.agent_benchmark.ui import configure_simple
        from Shared.bull_llm.agent_benchmark.contracts import AgentConfig
        backend=SimpleNamespace(models=lambda:[dict(name='fixture')])
        previous=AgentConfig('fixture'); original=deepcopy(previous)
        with patch.object(self.core, 'show_models'), patch.object(self.core, 'resolve_model_choice', return_value=('fixture',None)):
            with self.inputs(['1','1','s']):
                config=configure_simple(self.core,backend)
                self.assertEqual(config, original)
            with self.inputs(['2','8192','4096','','','0']):
                config=configure_simple(self.core,backend,previous)
                self.assertEqual(config,original)
                self.assertEqual(previous,original)

    def test_color_roles_have_distinct_escape_codes_and_text_labels(self):
        out=io.StringIO()
        with patch.object(self.core,'_COLOR_ENABLED',True), contextlib.redirect_stdout(out):
            self.core.ui_menu_item('1','Action')
            self.core.ui_status_strip([('status','good','ok'),('status','bad','error'),('status','check','warn')])
        text=out.getvalue()
        palette=self.core.ui_theme_palette()
        for code in (palette['action'],palette['success'],self.core.ANSI_RED,self.core.ANSI_YELLOW):
            self.assertIn(code,text)
        for word in ('OK','ОШИБКА','ВНИМАНИЕ'): self.assertIn(word,text)

    def test_agent_is_an_additional_action_and_needs_no_backend_until_run(self):
        with patch.object(self.core,'clear_console'), self.inputs(['6','5']):
            self.assertEqual(self.core.startup_home_menu('offline','OK'), '/agent')

    def test_full_bull_mark_and_expansion_are_available_on_every_page(self):
        from Shared.bull_llm import terminal_ui
        out=io.StringIO()
        with patch.object(self.core, '_COLOR_ENABLED', True), patch.object(self.core,'matrix'), patch.object(self.core,'white'), contextlib.redirect_stdout(out):
            terminal_ui.render_page_mark(self.core)
        text=out.getvalue()
        themed = terminal_ui._theme_console_mark(terminal_ui._load_console_mark(), self.core.UI_THEME)
        self.assertIn(themed, text)
        self.assertIn('B U L L  //  Benchmarking & Usage of Local Language Models',text)
        self.assertGreaterEqual(len(text.splitlines()),16)

    def test_page_header_clears_previous_screen(self):
        with patch.object(self.core, 'clear_console') as clear:
            self.core.ui_header('Header')
        clear.assert_called_once_with()

    def test_red_theme_uses_red_brand_and_action_colors(self):
        from Shared.bull_llm import terminal_ui
        selected = self.core.set_ui_theme('bull_red', persist=False)
        try:
            self.assertEqual(selected, 'bull_red')
            palette = self.core.ui_theme_palette()
            self.assertEqual(palette['accent'], self.core.ANSI_BULL_RED)
            self.assertEqual(palette['action'], self.core.ANSI_BULL_RED)
            self.assertFalse(palette['matrix'])
            canonical=terminal_ui._load_console_mark()
            themed=terminal_ui._theme_console_mark(canonical,'bull_red')
            self.assertNotEqual(themed,canonical)
            self.assertEqual(
                terminal_ui._SGR_ESCAPE_RE.sub('',themed),
                terminal_ui._SGR_ESCAPE_RE.sub('',canonical),
            )
        finally:
            self.core.set_ui_theme('bull_red', persist=False)

    def test_matrix_choice_repaints_home_and_survives_a_new_application_instance(self):
        import os
        from Apps._bootstrap import load_compat_core
        from Shared.bull_llm import terminal_ui
        previous_theme = self.core.UI_THEME
        try:
            with tempfile.TemporaryDirectory() as tmp, \
                 patch.dict(os.environ, {'BULL_UI_THEME':''}), \
                 patch.object(self.core, 'ui_settings_path', return_value=Path(tmp)/'ui_settings.json'), \
                 patch.object(self.core, '_COLOR_ENABLED', True), \
                 patch.object(self.core, 'enable_console_colors'), \
                 patch.object(self.core, 'clear_console'), patch.object(self.core.time, 'sleep'), \
                 patch.object(terminal_ui, 'test_library_status', return_value={'count':0,'selected':None,'issues':0}), \
                 self.inputs(['5','3','0','0']):
                self.core.save_ui_preferences(theme='bull_red', language='ru')
                self.core.set_ui_theme('bull_red', persist=False)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(self.core.startup_home_menu('offline','18/18'), 'exit')
                self.assertEqual(self.core.UI_THEME, 'matrix_bright')
                self.assertTrue(self.core.UI_MATRIX_ENABLED)
                art = terminal_ui._load_console_mark()
                green_mark = terminal_ui._theme_console_mark(art,'matrix_bright')
                final_frame = out.getvalue().rsplit('  B U L L  // ',1)[-1]
                last_mark = out.getvalue().rsplit('  B U L L  // ',1)[0]
                self.assertTrue(last_mark.endswith(green_mark + self.core.ui_theme_palette()['text']))
                self.assertNotIn(self.core.ANSI_BULL_RED, final_frame)
                settings = json.loads((Path(tmp)/'ui_settings.json').read_text(encoding='utf-8'))
                self.assertEqual((settings['theme'],settings['language']),('matrix_bright','ru'))
                restarted = load_compat_core()
                with patch.object(restarted, 'ui_settings_path', return_value=Path(tmp)/'ui_settings.json'):
                    self.assertEqual(restarted.initialize_ui_theme(), 'matrix_bright')
                    self.assertEqual(restarted.load_ui_language(), 'ru')
                    self.assertEqual(restarted._agent_core_proxy().UI_THEME, 'matrix_bright')
        finally:
            self.core.set_ui_theme(previous_theme, persist=False)

    def test_theme_display_names_and_matrix_aliases_resolve_to_the_same_palette(self):
        import os
        for label in ('Matrix BULL', 'matrix_bull', 'matrix-bull', '  MATRIX   BULL  '):
            with self.subTest(label=label):
                self.assertEqual(self.core.normalize_ui_theme(label), 'matrix_bright')
                self.assertTrue(self.core.ui_theme_palette(label)['matrix'])
                with patch.dict(os.environ, {'BULL_UI_THEME':label}):
                    self.assertEqual(self.core.load_ui_theme(), 'matrix_bright')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'BULL_UI_THEME':''}), \
             patch.object(self.core, 'ui_settings_path', return_value=Path(tmp)/'ui_settings.json'):
            (Path(tmp)/'ui_settings.json').write_text(json.dumps({
                'schema':self.core.UI_THEME_SCHEMA, 'version':self.core.UI_THEME_VERSION,
                'theme':'Matrix BULL', 'language':'ru',
            }), encoding='utf-8')
            self.assertEqual(self.core.load_ui_theme(), 'matrix_bright')
            self.core.save_ui_language('en')
            self.assertEqual(self.core.load_ui_theme(), 'matrix_bright')
        for key, label in self.core.UI_THEME_LABELS.items():
            with self.subTest(label=label):
                self.assertEqual(self.core.normalize_ui_theme(label), key)
        self.assertEqual(self.core.normalize_ui_theme('not-a-theme'), 'bull_red')
        self.assertIsNone(self.core.normalize_ui_theme('not-a-theme', default=None))

    def test_matrix_name_in_menu_and_language_change_keep_the_selected_theme(self):
        import os
        previous_theme = self.core.UI_THEME
        try:
            with tempfile.TemporaryDirectory() as tmp, \
                 patch.dict(os.environ, {'BULL_UI_THEME':''}), \
                 patch.object(self.core, 'ui_settings_path', return_value=Path(tmp)/'ui_settings.json'), \
                 patch.object(self.core, '_COLOR_ENABLED', True), \
                 patch.object(self.core, 'enable_console_colors'), \
                 patch.object(self.core, 'clear_console'), patch.object(self.core.time, 'sleep'), \
                 self.inputs(['Matrix BULL','not-a-theme','1','1','0']):
                self.core.save_ui_preferences(theme='bull_red', language='ru')
                self.core.set_ui_theme('bull_red', persist=False)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertIsNone(self.core.appearance_menu())
                self.assertEqual(self.core.UI_THEME, 'matrix_bright')
                self.assertEqual(self.core.get_language(), 'en')
                self.assertEqual(self.core.load_ui_theme(), 'matrix_bright')
                self.assertEqual(self.core.load_ui_language(), 'en')
                final_frame = out.getvalue().rsplit('  B U L L  // ',1)[-1]
                self.assertNotIn(self.core.ANSI_BULL_RED, final_frame)
                self.assertIn(self.core.ui_theme_palette('matrix_bright')['action'], final_frame)
        finally:
            self.core.set_ui_theme(previous_theme, persist=False)
            self.core.set_language('ru')

    def test_console_colour_state_is_not_stale_after_output_handle_changes(self):
        with patch.object(self.core, '_COLOR_ENABLED', True), contextlib.redirect_stdout(io.StringIO()):
            self.core.enable_console_colors()
            self.assertFalse(self.core._COLOR_ENABLED)
        if self.core.os.name == 'nt':
            class TerminalStream(io.StringIO):
                def isatty(self): return True
            kernel = SimpleNamespace(GetStdHandle=lambda value:1, GetConsoleMode=lambda *args:0)
            with patch.object(self.core, '_COLOR_ENABLED', True), \
                 patch.object(self.core.ctypes.windll, 'kernel32', kernel), \
                 contextlib.redirect_stdout(TerminalStream()):
                self.core.enable_console_colors()
                self.assertFalse(self.core._COLOR_ENABLED)

    @unittest.skipUnless(os.name == 'nt', 'Windows console mode contract')
    def test_first_launch_restores_console_mode_after_boot_and_before_matrix_redraw(self):
        import os
        from contextlib import ExitStack
        from unittest.mock import Mock
        from Shared.bull_llm import terminal_ui
        class TerminalStream(io.StringIO):
            def isatty(self): return True
        state = {'mode':1}
        def get_mode(handle, pointer):
            pointer._obj.value = state['mode']
            return 1
        def set_mode(handle, value):
            state['mode'] = value
            return 1
        kernel = SimpleNamespace(GetStdHandle=lambda value:1, GetConsoleMode=get_mode,
            SetConsoleMode=set_mode, SetConsoleCP=Mock(return_value=1), SetConsoleOutputCP=Mock(return_value=1))
        previous_theme = self.core.UI_THEME
        try:
            with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
                for name in ('set_console_icon','set_console_title','initialize_backend_from_settings',
                             'set_active_model','save_session','benchmark_pack_selection_menu','append_client_debug'):
                    stack.enter_context(patch.object(self.core,name))
                stack.enter_context(patch.object(self.core.ctypes.windll,'kernel32',kernel))
                stack.enter_context(patch.object(self.core,'_COLOR_ENABLED',False))
                stack.enter_context(patch.object(terminal_ui,'_startup_mark_shown',False))
                stack.enter_context(patch.object(self.core.time,'sleep'))
                stack.enter_context(patch.dict(os.environ, {'BULL_UI_THEME':'','BULL_UI_LANGUAGE':'','BULL_START_SURFACE':'home'}))
                stack.enter_context(patch.object(self.core,'ui_settings_path',return_value=Path(tmp)/'ui_settings.json'))
                stack.enter_context(patch.object(self.core,'newfile',return_value=Path(tmp)/'chat.json'))
                stack.enter_context(patch.object(self.core,'benchmark_dir',return_value=Path(tmp)))
                stack.enter_context(patch.object(self.core,'open_startup_verification_window',return_value=None))
                def boot(**kwargs):
                    state['mode'] = 1  # The console host can reset VT while startup is in progress.
                    return dict(ok=True,summary='18/18',output='')
                stack.enter_context(patch.object(self.core,'run_startup_regression',side_effect=boot))
                stack.enter_context(patch.object(self.core,'connect_active_backend',side_effect=ConnectionRefusedError('fixture')))
                stack.enter_context(patch.object(self.core,'maybe_save',return_value=False))
                stack.enter_context(patch.object(self.core,'stream_chat',side_effect=AssertionError('unexpected inference')))
                def home(*args):
                    self.assertEqual(state['mode'],5)
                    state['mode'] = 1
                    self.core.appearance_menu()
                    self.assertEqual(state['mode'],5)
                    self.assertEqual(self.core.UI_THEME,'matrix_bright')
                    return 'exit'
                stack.enter_context(patch.object(self.core,'startup_home_menu',side_effect=home))
                stack.enter_context(self.inputs(['2','3','0']))
                out = stack.enter_context(contextlib.redirect_stdout(TerminalStream()))
                self.assertEqual(self.core.main(),0,out.getvalue())
                self.assertGreaterEqual(kernel.SetConsoleOutputCP.call_count,3)
                self.assertEqual(self.core.load_ui_theme(),'matrix_bright')
        finally:
            self.core.set_ui_theme(previous_theme,persist=False)
            self.core.set_language('ru')

    def test_offline_dashboard_does_not_claim_a_live_backend_or_probe_telemetry(self):
        out = io.StringIO()
        session = self.core.new_session_meta('fixture-model')
        cfg = dict(self.core.THINK, model='fixture-model')
        with patch.object(self.core, 'clear_console'), \
                patch.object(self.core, 'telemetry_snapshot', side_effect=AssertionError('offline telemetry probe')), \
                contextlib.redirect_stdout(out):
            self.core.dashboard(None, 'think', cfg, True, Path('chat.json'), session,
                                [], '', [], {}, backend_ready=False)
        text = out.getvalue()
        self.assertIn('нет соединения', text)
        self.assertIn('сохранённые настройки', text)
        self.assertNotIn('OK · backend', text)

    def test_main_dispatch_home_commands_return_home_without_chat(self):
        import os
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            noop=lambda *a,**k:None
            for name in ('console_utf8','initialize_ui_theme','select_ui_language','enable_console_colors','set_console_icon',
                         'set_console_title','clear_console','initialize_backend_from_settings','set_active_model','save_session',
                         'benchmark_pack_selection_menu', 'append_client_debug'):
                stack.enter_context(patch.object(self.core,name,side_effect=noop))
            stack.enter_context(patch.object(self.core, 'open_startup_verification_window', return_value=None))
            stack.enter_context(patch.dict(os.environ, {'BULL_START_SURFACE':'home'}))
            stack.enter_context(patch.object(self.core,'newfile',return_value=Path(tmp)/'chat.json'))
            stack.enter_context(patch.object(self.core,'benchmark_dir',return_value=Path(tmp)))
            stack.enter_context(patch.object(self.core,'load_benchmarks',return_value={}))
            stack.enter_context(patch.object(self.core,'run_startup_regression',return_value=dict(ok=True,summary='OK',output='')))
            stack.enter_context(patch.object(self.core,'connect_active_backend',side_effect=ConnectionRefusedError('offline fixture')))
            stack.enter_context(patch.object(self.core,'version',return_value=None))
            home=stack.enter_context(patch.object(self.core,'startup_home_menu',side_effect=['/bench list','/no-such-command','exit']))
            stack.enter_context(patch.object(self.core,'maybe_save',return_value=False))
            stack.enter_context(patch.object(self.core,'installed_models',side_effect=AssertionError('unexpected backend call')))
            stream=stack.enter_context(patch.object(self.core,'stream_chat',side_effect=AssertionError('unexpected inference')))
            answers=stack.enter_context(self.inputs(['','']))
            out=io.StringIO()
            with contextlib.redirect_stdout(out): self.assertEqual(self.core.main(),0,out.getvalue())
            self.assertEqual(home.call_count,3)
            self.assertEqual(answers.call_count,2)
            self.assertIn('Неизвестная команда',out.getvalue())
            stream.assert_not_called()

    def test_agent_summary_labels_combined_local_memory_without_faking_remote_ram(self):
        from Shared.bull_llm.agent_benchmark.reports import outcome_lines
        run=dict(status='success', metrics=dict(resources={'client_and_backend':{'ram':{'peak_bytes':1024**3}}}))
        text='\n'.join(outcome_lines(run))
        self.assertIn('RAM этого ПК (клиент + сервер): 1.00 GiB',text)
        self.assertNotIn('RAM сервера: 1.00',text)

    def test_old_manual_profile_migrates_even_with_empty_connection_store(self):
        from Shared.bull_llm.connections_ui import import_old
        from Shared.bull_llm.storage import atomic_json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            atomic_json(root/'Runtime/connections.json',dict(connections={}))
            profile=dict(host='example.invalid',user='tester',port=22,identity_file='fixture-reference')
            atomic_json(root/'backend_settings.json',dict(remote_access=dict(profiles={'direct':profile})))
            with self.inputs([tmp,'1']), patch('Shared.bull_llm.connections_ui.new_ssh_connection') as wizard:
                import_old(self.core)
                wizard.assert_called_once_with(self.core,profile)


def run_suite(core):
    UXTests.core = core
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UXTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError('UX regression failed')
    return result.testsRun


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from Apps._bootstrap import load_compat_core
    run_suite(load_compat_core())
