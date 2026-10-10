"""Explicit one-pack selection, consent previews and offline UX contracts."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Shared.bull_llm.evaluation.catalog import catalog_from_registry
from Shared.bull_llm.evaluation.pack_library import PackLibrary
from Shared.bull_llm.evaluation.pack_selection import PackSelection, SelectedPackRegistry
from Shared.bull_llm.evaluation.registry import PackValidationError
from Tests.pack_library_regression import POLICY, _fixture, _zip


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bull-selection-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.library = PackLibrary(self.base / "library", POLICY)
        self.store = PackSelection(self.library)
        self.rows = _fixture(self.base)
        self.archive = _zip(self.base / "pack.zip", self.rows)

    def install(self):
        return self.library.install_zip(self.archive)

    def test_empty_selection_is_offline_read_only(self):
        self.assertIsNone(self.store.snapshot())
        self.assertEqual(catalog_from_registry(SelectedPackRegistry(self.store)), ({}, ()))
        self.assertFalse(self.library.root.exists())

    def test_skip_is_persistent_but_never_installs_tests(self):
        self.store.finish_onboarding()
        other = PackSelection(PackLibrary(self.library.root, POLICY))
        self.assertTrue(other.read()["onboarding_complete"])
        self.assertIsNone(other.active_pack())
        self.assertEqual(other.library.scan(), ())

    def test_install_is_not_automatic_selection(self):
        self.install()
        self.assertIsNone(self.store.active_pack())

    def test_selection_survives_a_new_app_instance(self):
        self.install()
        snapshot = self.store.select("author_tasks", "1.0.0")
        self.assertEqual(snapshot, PackSelection(self.library).snapshot())
        self.assertEqual(snapshot["coverage"], "full_pack")

    def test_missing_exact_version_never_selects_newest(self):
        self.install()
        with self.assertRaises(KeyError):
            self.store.select("author_tasks", "2.0.0")
        with self.assertRaises(PackValidationError):
            SelectedPackRegistry(self.store).get("author_tasks")

    def test_subset_rejects_empty_unknown_and_duplicate_cases(self):
        self.install()
        for ids in ([], ["not_in_pack"], ["safe_case", "safe_case"]):
            with self.assertRaises(PackValidationError):
                self.store.select("author_tasks", "1.0.0", ids)

    def test_read_rejects_bad_state_schema(self):
        self.store.finish_onboarding()
        self.store.path.write_text('{"schema":"wrong"}', encoding="utf-8")
        with self.assertRaises(PackValidationError):
            self.store.read()

    def test_duplicate_state_keys_rejected(self):
        self.store.finish_onboarding()
        self.store.path.write_text('{"selection":null,"selection":null}', encoding="utf-8")
        with self.assertRaises(PackValidationError):
            self.store.read()

    def test_preview_never_creates_library(self):
        preview = self.library.inspect_zip(self.archive)
        self.assertEqual(preview.identity, "author_tasks@1.0.0")
        self.assertFalse(preview.root.exists())
        self.assertFalse(self.library.root.exists())

    def test_zip_change_after_preview_prevents_publication(self):
        preview = self.library.inspect_zip(self.archive)
        newer = _fixture(self.base, version="2.0.0")
        _zip(self.archive, newer)
        with self.assertRaises(PackValidationError) as caught:
            self.library.install_zip(self.archive, expected_manifest_sha256=preview.manifest_sha256,
                                     expected_compiled_sha256=preview.compiled_sha256)
        self.assertEqual(caught.exception.code, "PACK_PREVIEW_CHANGED")
        self.assertEqual(self.library.scan(), ())

    def test_removed_version_is_recoverable_and_never_substituted(self):
        self.install()
        snapshot = self.store.select("author_tasks", "1.0.0")
        target = self.library.move_to_trash("author_tasks", "1.0.0")
        self.assertTrue((target / "manifest.json").is_file())
        with self.assertRaises(KeyError):
            self.store.catalog_for_snapshot(snapshot)
        self.store.clear()
        self.assertIsNone(self.store.active_pack())

    def test_changed_selection_digest_blocks_execution(self):
        self.install()
        snapshot = self.store.select("author_tasks", "1.0.0")
        snapshot["compiled_sha256"] = "0" * 64
        with self.assertRaises(PackValidationError):
            self.store.catalog_for_snapshot(snapshot)

    def test_broken_other_pack_does_not_block_healthy_selection(self):
        self.install()
        self.store.select("author_tasks", "1.0.0")
        broken = self.library.root / "Installed" / "private" / "broken@1.0.0"
        broken.mkdir()
        self.assertEqual(len(self.library.scan()), 2)
        catalog, packs = catalog_from_registry(SelectedPackRegistry(self.store))
        self.assertEqual(list(catalog), ["safe_case"])
        self.assertEqual(len(packs), 1)

    def test_newer_install_does_not_mutate_checkpoint_catalog(self):
        self.install()
        snapshot = self.store.select("author_tasks", "1.0.0")
        newer = _zip(self.base / "new.zip", _fixture(self.base, version="2.0.0"))
        self.library.install_zip(newer)
        self.store.select("author_tasks", "2.0.0")
        definitions = self.store.catalog_for_snapshot(snapshot)
        self.assertEqual(definitions["safe_case"]["_pack"]["identity"], "author_tasks@1.0.0")

    def test_terminal_untrusted_labels_cannot_inject_controls(self):
        from Shared.bull_llm.pack_library_ui import label
        self.assertEqual(label("\x1b[31mred\n\x07next"), "[31mred next")
        self.assertEqual(len(label("x" * 1000)), 180)

    def test_onboarding_skip_does_not_query_models_and_does_not_repeat(self):
        from Shared.bull_llm.pack_library_ui import library_menu
        calls = []
        core = SimpleNamespace(benchmark_pack_library=lambda: self.library, ui_header=lambda *a: None,
                               ui_print=lambda *a: None, ui_menu_item=lambda *a: None, ui_status_strip=lambda *a: None,
                               read_user_input=lambda *a: calls.append(a) or "0")
        self.assertFalse(library_menu(core, onboarding=True))
        self.assertEqual(len(calls), 1)
        self.assertFalse(library_menu(core, onboarding=True))
        self.assertEqual(len(calls), 1)

    def ui_core(self, values, output):
        iterator = iter(values)
        return SimpleNamespace(benchmark_pack_library=lambda: self.library,
                               ui_header=lambda *a: output.append(str(a)),
                               ui_print=lambda *a: output.append(" ".join(map(str, a))),
                               ui_status_strip=lambda *a: output.append(str(a)),
                               ui_menu_item=lambda *a: output.append(str(a)),
                               read_user_input=lambda *a: next(iterator),
                               yellow=lambda: None, white=lambda: None)

    def test_declined_install_preview_leaves_library_empty(self):
        from Shared.bull_llm.pack_library_ui import install
        output = []
        self.assertFalse(install(self.ui_core(["n"], output), self.store, self.archive))
        self.assertFalse(self.library.root.exists())

    def test_own_zip_onboarding_installs_and_selects_one_version(self):
        from Shared.bull_llm.pack_library_ui import library_menu
        output = []
        self.assertTrue(library_menu(self.ui_core(["2", str(self.archive), "y", "all"], output), onboarding=True))
        self.assertEqual(self.store.snapshot()["identity"], "author_tasks@1.0.0")

    def test_broken_zip_returns_to_menu_in_english(self):
        from Shared.bull_llm.pack_library_ui import library_menu
        from Shared.bull_llm.i18n import get_language, set_language
        previous = get_language()
        self.addCleanup(set_language, previous)
        set_language("en")
        self.archive.write_bytes(b"broken ZIP fixture")
        output = []
        self.assertFalse(library_menu(self.ui_core(["2", str(self.archive), "", "0"], output), onboarding=True))
        self.assertIn("Pack operation failed:", "\n".join(output))
        self.assertEqual(self.library.scan(), ())

    def test_duplicate_case_numbers_return_without_selection(self):
        from Shared.bull_llm.pack_library_ui import choose_cases
        pack = self.install()
        self.assertFalse(choose_cases(self.ui_core(["1,1", "", "0"], []), self.store, pack))
        self.assertIsNone(self.store.active_pack())


def run_suite(mod=None, production_load=None, production_registry=None):
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SelectionTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Pack selection regression failed")
    count = result.testsRun
    if mod is not None:
        with tempfile.TemporaryDirectory(prefix="bull-selected-client-") as temporary:
            root = Path(temporary)
            library = PackLibrary(root / "library", mod.benchmark_registry_policy())
            with patch.object(mod, "benchmark_pack_library", return_value=library), \
                 patch.object(mod, "benchmark_pack_registry", production_registry), \
                 patch.object(mod, "load_benchmarks", production_load), \
                 patch.object(mod, "BENCHMARK_CATALOG_SCOPE", "packs"), \
                 patch.object(mod, "appdir", return_value=root), \
                 patch.object(mod, "benchmark_profiles_path", return_value=Path(mod.__file__).resolve().parent / "benchmark_profiles.json"), \
                 patch.object(mod, "model_catalog", side_effect=AssertionError("API called before selection")):
                assert mod.load_benchmarks() == {}
                try:
                    mod.make_benchmark_spec(["simpson"], ["test-model"], 1, False)
                    raise AssertionError("uninstalled bundled test ran")
                except PackValidationError as error:
                    assert error.code == "BENCHMARK_CASE_NOT_AVAILABLE"
                count += 1
                source = Path(mod.__file__).resolve().parent / "BasePacks" / "bull_chat_core@1.0.0.zip"
                library.install_zip(source)
                store = PackSelection(library)
                store.select("bull_chat_core", "1.0.0", ["simpson"])
                assert len(mod.load_benchmarks()) == 12
                assert mod.benchmark_suite_tests("selected_pack") == ["simpson"]
                spec = mod.make_named_suite_spec("selected_pack", ["test-model"], catalog={})
                assert spec["pack_selection"]["coverage"] == "subset"
                assert spec["tests"] == ["simpson"] and spec["runs"] == 3
                assert "simpson" in mod.benchmark_catalog_for_spec(spec)
                assert "Subset" not in json.dumps(spec)  # no localized execution contract
                count += 1
                try:
                    mod.make_named_suite_spec("selected_pack", ["test-model"], catalog={}, selection_sha256="0" * 64)
                    raise AssertionError("changed preview was accepted")
                except PackValidationError as error:
                    assert error.code == "PACK_PREVIEW_CHANGED"
                count += 1
                store.clear()
                assert mod.load_benchmarks() == {}
                assert "simpson" in mod.benchmark_catalog_for_spec(spec)
                from Shared.bull_llm.results_report import render_report
                html = render_report([], [], language="en", run_scope=spec["pack_selection"])
                assert "SUBSET" in html and "1/12" in html
                count += 1
                captured = mod.benchmark_catalog_for_spec(spec)
                library.move_to_trash("bull_chat_core", "1.0.0")
                assert mod.benchmark_catalog_for_spec(spec) == captured
                path, cp = mod.new_checkpoint(spec)
                cp["records"] = {mod._run_key("simpson", "test-model", run): {
                    "record_schema_version": mod.BENCH_RECORD_SCHEMA_VERSION, "execution_status": "ok"
                } for run in range(1, 4)}
                completed = deepcopy(cp["records"])
                with patch.object(mod, "set_active_model", side_effect=AssertionError("completed jobs replayed")):
                    mod.execute_benchmark_checkpoint(path, cp, catalog={})
                assert cp["records"] == completed
                count += 1
                damaged = deepcopy(spec)
                damaged["pack_run_snapshot"]["compiled"]["cases"][0]["definition"]["prompt"] = "changed"
                try:
                    mod.benchmark_catalog_for_spec(damaged)
                    raise AssertionError("damaged snapshot executed")
                except PackValidationError:
                    pass
                count += 1
                with patch.object(mod, "benchmark_scorer_sha256", return_value="0" * 64):
                    try:
                        mod.benchmark_catalog_for_spec(spec)
                        raise AssertionError("changed scorer executed")
                    except PackValidationError as error:
                        assert error.code == "PACK_ENGINE_CHECK_CHANGED"
                count += 1
                extended = Path(mod.__file__).resolve().parent / "BasePacks" / "bull_extended_core@1.0.0.zip"
                library.install_zip(extended)
                store.select("bull_extended_core", "1.0.0", ["python_debug"])
                try:
                    mod.make_named_suite_spec("selected_pack", ["test-model"], catalog={})
                    raise AssertionError("code-check permission bypass")
                except PackValidationError as error:
                    assert error.code == "PACK_CODE_PERMISSION_REQUIRED"
                store.select("bull_extended_core", "1.0.0", ["python_debug"], allow_code_execution=True)
                approved = mod.make_named_suite_spec("selected_pack", ["test-model"], catalog={})
                assert approved["pack_selection"]["code_execution_approved"] is True
                approved["pack_selection"]["approved_code_cases"] = []
                try:
                    mod.benchmark_catalog_for_spec(approved)
                    raise AssertionError("snapshot approval bypass")
                except PackValidationError as error:
                    assert error.code == "PACK_CODE_PERMISSION_REQUIRED"
                count += 1
                guards = []
                with patch.object(mod, "benchmark_pack_selection_menu", return_value=False), \
                     patch.object(mod, "read_user_input", side_effect=["1", "0"]), \
                     patch.object(mod, "ui_header"), patch.object(mod, "ui_menu_item"), \
                     patch.object(mod, "ui_footer"), patch.object(mod, "clear_console"), \
                     contextlib.redirect_stdout(io.StringIO()):
                    assert mod.startup_benchmark_wizard(runtime_guard=lambda purpose: guards.append(purpose)) == ("/home", False)
                assert guards == []
                count += 1
    return count


if __name__ == "__main__":
    run_suite()
