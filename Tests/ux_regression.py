"""Offline UX contracts: navigation, explicit trust and release-independent settings."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class UXTests(unittest.TestCase):
    core = None

    def setUp(self):
        # Existing behavior contracts are asserted in the original Russian UI.
        # Dedicated tests below cover the new English interface explicitly.
        from Shared.bull_llm.i18n import set_language
        set_language('ru')

    def inputs(self, values):
        return patch.object(self.core, 'read_user_input', side_effect=values)

    def test_home_exposes_four_clear_tasks_and_keeps_commands_unadvertised(self):
        out = io.StringIO()
        with patch.object(self.core, 'clear_console'), self.inputs(['/backend import "C:/My Config.JSON"']), contextlib.redirect_stdout(out):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), '/backend import "C:/My Config.JSON"')
        text=out.getvalue()
        for label in ('Сравнить модели','Чат с моделью','Подключение','Дополнительно'):
            self.assertIn(label,text)
        self.assertNotIn('Команда /',text)
        self.assertNotIn('MATRIX NODE', out.getvalue())
        self.assertNotIn('[5]', out.getvalue())

    def test_home_routes_chat_and_connections(self):
        with patch.object(self.core, 'clear_console'), self.inputs(['2', '2']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'load')
        with patch.object(self.core, 'clear_console'), self.inputs(['3']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'connections')

    def test_empty_home_input_never_starts_chat(self):
        with patch.object(self.core, 'clear_console'), self.inputs(['', 'unknown text', '0']):
            self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'exit')

    def test_selection_rejects_zero_negative_and_out_of_range(self):
        from Shared.bull_llm.terminal_ui import selection
        for value in ('0', '-1', '4', 'foo', ''):
            self.assertIsNone(selection(value, ['a', 'b', 'c']))
        self.assertEqual(selection('2', ['a', 'b']), 'b')

    def test_more_and_command_palette_offline(self):
        from Shared.bull_llm.terminal_ui import more_menu, command_menu
        with patch.object(self.core, 'clear_console'), self.inputs(['3']):
            self.assertEqual(more_menu(self.core), '/dashboard')
        with self.inputs(['/profile import-tested "C:/Test A.JSON"']):
            self.assertEqual(command_menu(self.core), '/profile import-tested "C:/Test A.JSON"')

    def test_startup_pixel_bull_is_compact_and_drawn_once(self):
        from Shared.bull_llm import terminal_ui
        out = io.StringIO()
        with patch.object(terminal_ui, '_startup_mark_shown', False), patch.object(
                self.core, 'matrix'), patch.object(self.core, 'white'), contextlib.redirect_stdout(out):
            self.assertTrue(terminal_ui.render_startup_mark(self.core))
            self.assertFalse(terminal_ui.render_startup_mark(self.core))
        text = out.getvalue()
        plain = terminal_ui._SGR_ESCAPE_RE.sub('', text)
        self.assertIn('\x1b[', text)
        self.assertEqual(text.count('B U L L  //  Benchmarking & Usage of Local LLMs'), 1)
        self.assertNotIn('\x1b', plain)
        art = terminal_ui._load_chafa_mark()
        self.assertIsNotNone(art)
        art_plain = terminal_ui._SGR_ESCAPE_RE.sub('', art)
        self.assertLessEqual(len(art_plain.splitlines()), 18)
        self.assertLessEqual(max(map(len, art_plain.splitlines())), 30)
        self.assertLessEqual(len(plain.splitlines()), 20)

    def test_startup_pixel_bull_falls_back_if_chafa_asset_is_missing(self):
        from Shared.bull_llm import terminal_ui
        out = io.StringIO()
        with patch.object(terminal_ui, '_startup_mark_shown', False), patch.object(
                terminal_ui, '_load_chafa_mark', return_value=None), patch.object(
                self.core, 'matrix'), patch.object(self.core, 'white'), contextlib.redirect_stdout(out):
            self.assertTrue(terminal_ui.render_startup_mark(self.core))
        text = out.getvalue()
        self.assertIn('▗▆            ▆▖', text)
        self.assertIn('▅▇▁▁▇▅', text)

    def test_home_is_english_after_language_choice_and_model_text_is_untouched(self):
        from Shared.bull_llm.i18n import set_language, tr
        out = io.StringIO()
        set_language('en')
        try:
            with patch.object(self.core, 'clear_console'), self.inputs(['0']), contextlib.redirect_stdout(out):
                self.assertEqual(self.core.startup_home_menu('offline', 'OK'), 'exit')
            text = out.getvalue()
            self.assertIn('Choose what you want to do', text)
            self.assertIn('Compare models', text)
            self.assertIn('More', text)
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
        from Shared.bull_llm.terminal_ui import experimental_menu, more_menu
        has_cyrillic=lambda value:any(('А' <= char <= 'я') or char in 'Ёё' for char in value)
        set_language('en')
        try:
            for menu in (more_menu, experimental_menu):
                out=io.StringIO()
                with patch.object(self.core, 'clear_console'), self.inputs(['0']), contextlib.redirect_stdout(out):
                    self.assertIsNone(menu(self.core))
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
                    self.assertEqual(document['version'], 3)
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

    def test_unknown_command_not_sent_as_prompt(self):
        from Shared.bull_llm.terminal_ui import command_menu
        with self.inputs(['hello model', '0']):
            self.assertIsNone(command_menu(self.core))

    def fixture_connection(self):
        import base64, hashlib
        blob = b'public synthetic host key fixture' * 2
        return dict(schema='local-llm-connection', version=1, id='fixture', name='Fixture',
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

    def test_agent_is_hidden_in_experimental_menu_and_needs_no_backend_until_run(self):
        from Shared.bull_llm.terminal_ui import experimental_menu
        with patch.object(self.core,'clear_console'), self.inputs(['1']):
            self.assertEqual(experimental_menu(self.core), 'agent')

    def test_full_bull_mark_and_expansion_are_available_on_every_page(self):
        from Shared.bull_llm import terminal_ui
        out=io.StringIO()
        with patch.object(self.core,'matrix'), patch.object(self.core,'white'), contextlib.redirect_stdout(out):
            terminal_ui.render_page_mark(self.core)
        text=out.getvalue()
        canonical=terminal_ui._SGR_ESCAPE_RE.sub('',terminal_ui._load_chafa_mark()).strip()
        visible=terminal_ui._SGR_ESCAPE_RE.sub('',text)
        self.assertIn(canonical,visible)
        self.assertIn('B U L L  //  Benchmarking & Usage of Local LLMs',text)
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
            canonical=terminal_ui._load_chafa_mark()
            themed=terminal_ui._theme_chafa_mark(canonical,'bull_red')
            self.assertNotEqual(themed,canonical)
            self.assertEqual(
                terminal_ui._SGR_ESCAPE_RE.sub('',themed),
                terminal_ui._SGR_ESCAPE_RE.sub('',canonical),
            )
        finally:
            self.core.set_ui_theme('bull_brand', persist=False)

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
                         'set_console_title','clear_console','initialize_backend_from_settings','set_active_model','save_session'):
                stack.enter_context(patch.object(self.core,name,side_effect=noop))
            stack.enter_context(patch.dict(os.environ, {'BULL_START_SURFACE':'home'}))
            stack.enter_context(patch.object(self.core,'newfile',return_value=Path(tmp)/'chat.json'))
            stack.enter_context(patch.object(self.core,'benchmark_dir',return_value=Path(tmp)))
            stack.enter_context(patch.object(self.core,'run_startup_regression',return_value=dict(ok=True,summary='OK',output='')))
            stack.enter_context(patch.object(self.core,'connect_active_backend',side_effect=ConnectionRefusedError('offline fixture')))
            stack.enter_context(patch.object(self.core,'version',return_value=None))
            home=stack.enter_context(patch.object(self.core,'startup_home_menu',side_effect=['/bench list','/no-such-command','exit']))
            stack.enter_context(patch.object(self.core,'maybe_save',return_value=False))
            stack.enter_context(patch.object(self.core,'installed_models',side_effect=AssertionError('unexpected backend call')))
            stream=stack.enter_context(patch.object(self.core,'stream_chat',side_effect=AssertionError('unexpected inference')))
            answers=stack.enter_context(self.inputs(['','']))
            out=io.StringIO()
            with contextlib.redirect_stdout(out): self.assertEqual(self.core.main(),0)
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
