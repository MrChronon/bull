"""Real installed-pack binding for all language routes; no backend requests."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class LanguageRouteTests(unittest.TestCase):
    core = None

    def setUp(self):
        from Shared.bull_llm.evaluation.pack_library import PackLibrary
        from Shared.bull_llm.evaluation.pack_selection import PackSelection, SelectedPackRegistry
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.library = PackLibrary(Path(self.directory.name), self.core.benchmark_registry_policy())
        self.selection = PackSelection(self.library)
        self.addCleanup(patch.stopall)
        patch.object(self.core, 'benchmark_pack_library', return_value=self.library).start()
        patch.object(self.core, 'benchmark_pack_registry', side_effect=lambda: SelectedPackRegistry(self.selection)).start()
        patch.object(self.core, 'model_catalog', side_effect=AssertionError('Must validate pack before API')).start()

    def test_all_tracks_fail_clearly_without_installed_pack_before_api(self):
        for suite in self.core.LANGUAGE_SUITE_DEFINITIONS:
            with self.assertRaisesRegex(ValueError, 'LANGUAGE_PACK_SELECTION_REQUIRED'):
                self.core.make_named_suite_spec(suite, ['example'])

    def test_chat_pack_cannot_supply_language_cases(self):
        self.library.install_zip(ROOT/'BasePacks/bull_chat_core@1.0.0.zip')
        self.selection.select('bull_chat_core','1.0.0')
        with self.assertRaisesRegex(ValueError, 'LANGUAGE_PACK_SELECTION_REQUIRED'):
            self.core.language_suite_selection('bilingual')

    def test_all_tracks_bind_to_same_exact_installed_version_and_snapshot(self):
        self.library.install_zip(ROOT/'BasePacks/bull_language_comparison@1.0.1.zip')
        self.selection.select('bull_language_comparison','1.0.1')
        for suite, definition in self.core.LANGUAGE_SUITE_DEFINITIONS.items():
            snapshot = self.core.language_suite_selection(suite)
            self.assertEqual(snapshot['case_ids'], list(definition['tests']))
            self.assertEqual(snapshot['identity'], 'bull_language_comparison@1.0.1')
            catalog = self.selection.catalog_for_snapshot(snapshot)
            self.assertEqual(set(catalog), set(snapshot['case_ids']))
            self.assertTrue(all(item['expected_language'] == item['language_track'] for item in catalog.values()))

    def test_language_picker_is_available_offline_and_selects_only_one_pack(self):
        from Shared.bull_llm.pack_library_ui import choose_language_pack
        self.library.install_zip(ROOT/'BasePacks/bull_language_comparison@1.0.1.zip')
        core = Mock(LANGUAGE_SUITE_DEFINITIONS=self.core.LANGUAGE_SUITE_DEFINITIONS)
        core.benchmark_pack_library.return_value = self.library
        core.read_user_input.return_value = '1'
        self.assertTrue(choose_language_pack(core,'language_ru'))
        self.assertEqual(self.selection.snapshot()['selected_cases'],3)
        self.assertEqual(self.selection.snapshot()['id'],'bull_language_comparison')


def run_suite(core):
    LanguageRouteTests.core = core
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LanguageRouteTests))
    if not result.wasSuccessful(): raise AssertionError('Language route contracts failed')
    return result.testsRun


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    from Apps._bootstrap import load_compat_core
    run_suite(load_compat_core())
