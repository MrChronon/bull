"""Offline reproductions of the Pack Library usability and persistence findings."""
from __future__ import annotations
import contextlib
import io
import json
import os
import base64
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Shared.bull_llm import storage


def locked_error(code=32):
    error = PermissionError('controlled Windows file lock')
    error.winerror = code
    return error


class UsabilityPatchTests(unittest.TestCase):
    core = None

    def test_transient_windows_replace_retries_without_rewriting_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'state.json'
            storage.atomic_json(target, {'old': True})
            replace = os.replace
            calls = []
            def blocked_once(source, destination):
                calls.append(source)
                if len(calls) < 3:
                    raise locked_error()
                replace(source, destination)
            with patch.object(storage.os, 'replace', side_effect=blocked_once), patch.object(storage.time, 'sleep'):
                storage.atomic_json(target, {'new': True})
            self.assertEqual(len(calls), 3)
            self.assertEqual(len(set(calls)), 1)
            self.assertEqual(json.loads(target.read_text()), {'new': True})
            self.assertEqual(list(Path(temporary).glob('*.tmp')), [])

    def test_persistent_checkpoint_lock_keeps_old_file_and_complete_recovery_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'run_checkpoint.json'
            storage.atomic_json(target, {'records': {'old': {}}})
            with patch.object(storage.os, 'replace', side_effect=locked_error(5)), patch.object(storage.time, 'sleep'):
                with self.assertRaises(PermissionError) as caught:
                    storage.atomic_json(target, {'records': {'old': {}, 'new': {}}}, preserve_failed=True)
            recovery = Path(caught.exception.recovery_path)
            self.assertEqual(json.loads(target.read_text()), {'records': {'old': {}}})
            self.assertEqual(json.loads(recovery.read_text()), {'records': {'old': {}, 'new': {}}})
            self.assertEqual(recovery.parent, target.parent)

    def test_permanent_non_windows_permission_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'state.json'
            with patch.object(storage.os, 'replace', side_effect=PermissionError('fixture')) as replace:
                with self.assertRaises(PermissionError):
                    storage.atomic_json(target, {'new': True})
                self.assertEqual(replace.call_count, 1)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(temporary).glob('*.tmp')), [])

    def test_invalid_json_never_leaves_recovery_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'run_checkpoint.json'
            with self.assertRaises(ValueError):
                storage.atomic_json(target, {'bad': float('nan')}, preserve_failed=True)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_system_sampler_json_is_locale_independent(self):
        row = self.core.SystemSampler.parse_line('{"cpu_util":12.5,"ram_used_bytes":1024,"ram_total_bytes":4096}')
        self.assertEqual(row, {'cpu_util': 12.5, 'ram_used_bytes': 1024.0, 'ram_total_bytes': 4096.0})

    def test_ram_can_be_measured_without_cpu_sample(self):
        row = self.core.SystemSampler.parse_line('{"cpu_util":null,"ram_used_bytes":1024,"ram_total_bytes":4096}')
        self.assertIsNotNone(row)
        self.assertIsNone(row['cpu_util'])
        sampler = self.core.SystemSampler()
        sampler.samples = [row]
        summary = sampler.summary()
        self.assertIsNone(summary['cpu_util_avg'])
        self.assertEqual(summary['ram_used_peak_bytes'], 1024)

    def test_invalid_system_values_do_not_become_real_zeroes(self):
        for raw in ('{"cpu_util":101,"ram_used_bytes":2,"ram_total_bytes":1}',
                    '{"cpu_util":true,"ram_used_bytes":2,"ram_total_bytes":4}',
                    '{"cpu_util":NaN,"ram_used_bytes":2,"ram_total_bytes":4}', '12,5,1024,4096'):
            self.assertIsNone(self.core.SystemSampler.parse_line(raw), raw)

    def test_saved_summary_does_not_hide_missing_cpu_or_ram(self):
        record = {'execution_status':'ok', 'identity':{'benchmark':'fixture','model':'model'},
                  'primary':{'task_completed':True,'eval_rate':12}, 'telemetry':{'system':{'samples':0}}}
        output = io.StringIO()
        with patch.object(self.core,'green'), patch.object(self.core,'white'), contextlib.redirect_stdout(output):
            self.core.render_benchmark_run_summary(record, 1, 3)
        self.assertIn('CPU N/A', output.getvalue())
        self.assertIn('RAM N/A', output.getvalue())

    def test_batch_pack_numbers_and_all(self):
        from Shared.bull_llm.pack_library_ui import parse_pack_numbers
        self.assertEqual(parse_pack_numbers('1,3', 4), [0,2])
        self.assertEqual(parse_pack_numbers('all', 4), [0,1,2,3])
        for invalid in ('1,1','0,2','5','1,no','', 'all,2'):
            with self.assertRaises(ValueError):
                parse_pack_numbers(invalid, 4)

    def test_home_exposes_library_without_backend(self):
        output = io.StringIO()
        with patch.object(self.core,'read_user_input',side_effect=['3']), \
             patch.object(self.core,'clear_console'), contextlib.redirect_stdout(output):
            self.assertEqual(self.core.startup_home_menu('offline','OK'), 'packs')
        self.assertIn('[5]', output.getvalue())

    def test_benchmark_list_from_navigation_returns_to_lab(self):
        source = Path(self.core.__file__).read_text(encoding='utf-8')
        self.assertIn("return '/bench list',True", source)
        branch = source[source.index("if u=='/bench list':"):source.index("if u.startswith('/bench reference '")]
        self.assertIn('after_benchmark(u)', branch)
        for raw, expected in [('0', '/home'), ('1', '__benchmark_menu__'), ('2', '/bench list')]:
            out=io.StringIO()
            with patch.object(self.core,'read_user_input',return_value=raw), \
                 patch.object(self.core,'benchmark_pack_selection_menu'), contextlib.redirect_stdout(out):
                self.assertEqual(self.core.benchmark_result_menu(last_command='/bench list'), expected)
            self.assertNotIn('BENCHMARK ЗАВЕРШЁН', out.getvalue())

    def test_batch_install_keeps_single_pack_selection(self):
        from Shared.bull_llm.evaluation.pack_library import PackLibrary
        from Shared.bull_llm.evaluation.pack_selection import PackSelection
        from Shared.bull_llm.pack_library_ui import base_archive_menu
        with tempfile.TemporaryDirectory() as temporary:
            store = PackSelection(PackLibrary(Path(temporary), self.core.benchmark_registry_policy()))
            for raw, expected in [('1,3', 2), ('all', 4), ('all', 4)]:
                fake = SimpleNamespace(__file__=self.core.__file__, ui_header=lambda *x: None,
                                       ui_print=lambda *x: None, green=lambda: None, white=lambda: None,
                                       yellow=lambda: None, read_user_input=lambda prompt: raw if 'all,' in prompt else 'y')
                self.assertFalse(base_archive_menu(fake, store))
                self.assertEqual(len([x for x in store.library.scan() if x.pack]), expected)
                self.assertIsNone(store.read()['selection'])
                self.assertTrue(store.read()['onboarding_complete'])

    def test_recovery_promotion_preserves_old_and_temporary_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'run_checkpoint.json'
            old = {'spec': {}, 'records': {'old': {}}}
            new = {'spec': {}, 'records': {'old': {}, 'new': {}}}
            storage.atomic_json(target, old)
            with patch.object(storage.os, 'replace', side_effect=locked_error()), patch.object(storage.time, 'sleep'):
                with self.assertRaises(PermissionError) as caught:
                    self.core._atomic_json(target, new)
            recovery = Path(caught.exception.recovery_path)
            promoted = self.core.promote_checkpoint_recovery(recovery, new)
            self.assertEqual(json.loads(promoted.read_text()), new)
            self.assertEqual(json.loads(target.read_text()), old)
            self.assertTrue(recovery.is_file())
            self.assertTrue(promoted.name.endswith('_checkpoint.json'))

    @unittest.skipUnless(os.name == 'nt', 'Windows native counters')
    def test_actual_windows_counters_work_without_wmi(self):
        from Shared.bull_llm.system_telemetry import windows_script, parse_sample
        script = windows_script(500).replace('while ($true)', 'foreach ($probe in 1..3)')
        encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        result = subprocess.run(['powershell.exe', '-NoProfile', '-EncodedCommand', encoded],
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15, creationflags=flags)
        self.assertEqual(result.returncode, 0, result.stderr[:1000])
        rows = [parse_sample(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row and row['ram_total_bytes'] > 0 for row in rows), result.stdout)
        self.assertIsNotNone(rows[-1]['cpu_util'])

    def test_remote_sampler_never_uses_local_host_counters(self):
        with patch.object(self.core, '_telemetry_target', return_value='remote'), \
             patch.object(self.core, 'resolve_remote_endpoint', return_value={}), \
             patch.object(self.core, '_ssh_base_args', return_value=['ssh', 'fixture-pinned']):
            command = self.core._system_sampler_command()
        self.assertEqual(command[:3], ['ssh', 'fixture-pinned', 'powershell.exe'])
        with patch.object(self.core, '_telemetry_target', return_value='unknown'):
            self.assertIsNone(self.core._system_sampler_command())

    def test_boot_manifest_blocks_tampering_and_missing_modules(self):
        import hashlib
        from Shared.bull_llm.startup_checks import verify_files
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'engine.py'; path.write_bytes(b'initial')
            manifest = {'files': {'engine.py': hashlib.sha256(b'initial').hexdigest()}}
            verify_files(root, manifest, ['engine.py'])
            path.write_bytes(b'changed')
            with self.assertRaises(RuntimeError): verify_files(root, manifest, ['engine.py'])
            path.unlink()
            with self.assertRaises(RuntimeError): verify_files(root, manifest, ['engine.py'])
            with self.assertRaises(RuntimeError): verify_files(root, manifest, [])
            with self.assertRaises(RuntimeError): verify_files(root, manifest, ['../outside.py'])

    def test_restored_splash_matches_approved_artwork(self):
        root = Path(self.core.__file__).parent
        self.assertEqual((root / 'Assets/Brand/startup-hero.png').read_bytes(),
                         (root / f'Assets/Brand/splash-{self.core.APP_VERSION}.png').read_bytes())

    def test_splash_percentage_is_completed_check_fraction(self):
        from Shared.bull_llm.startup_window import _DesktopSplash
        stage, detail, bar, root = unittest.mock.Mock(), unittest.mock.Mock(), unittest.mock.Mock(), unittest.mock.Mock()
        window = _DesktopSplash(root, stage, detail, bar, width=100)
        window.update('Checking\nCurrent check: fixture', 9, 18)
        self.assertIn('50% (9/18)', stage.configure.call_args.kwargs['text'])
        self.assertEqual(detail.configure.call_args.kwargs['text'], 'Current check: fixture')
        bar.coords.assert_called_once_with('fill', 0, 0, 50, 8)

    def test_startup_cache_invalidates_when_manifest_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / 'smoke.py'; script.write_bytes(b'fixture')
            manifest = root / 'RELEASE_MANIFEST.json'; manifest.write_bytes(b'initial')
            with patch.object(self.core, 'appdir', return_value=root):
                first = self.core._startup_regression_identity(script)
                manifest.write_bytes(b'changed')
                second = self.core._startup_regression_identity(script)
            self.assertNotEqual(first, second)


def run_suite(core):
    UsabilityPatchTests.core = core
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(UsabilityPatchTests))
    if not result.wasSuccessful():
        raise AssertionError('Pack Library usability patch regression failed')
    return result.testsRun


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from Apps._bootstrap import load_compat_core
    run_suite(load_compat_core())
