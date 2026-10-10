"""Offline editable-source, fixture and immutable author ZIP contracts."""
from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from Shared.bull_llm.evaluation.catalog import engine_registry_policy
from Shared.bull_llm.evaluation.pack_library import PackLibrary
from Shared.bull_llm.evaluation.pack_selection import PackSelection
from Shared.bull_llm.evaluation.registry import PackValidationError
from Shared.bull_llm.evaluation.author_workshop import AuthorWorkshop


class WorkshopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bull-author-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.library = PackLibrary(self.base / "library", engine_registry_policy("0.29.0.1"))
        self.workshop = AuthorWorkshop(self.library)
        self.workspace = self.workshop.create_starter("my_tasks")

    def read(self, name):
        return json.loads((self.workspace / name).read_text(encoding="utf-8"))

    def write(self, name, value):
        (self.workspace / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def source(self, **values):
        row = self.read("author.json"); row.update(values); self.write("author.json", row)

    def build(self, name="pack.zip"):
        return self.workshop.build(self.workspace, self.base / name)

    def test_starter_is_private_experimental_and_not_installed(self):
        row = self.read("author.json")
        self.assertEqual((row["visibility"], row["status"]), ("private", "experimental"))
        self.assertEqual(self.library.scan(), ())
        self.assertIsNone(PackSelection(self.library).snapshot())

    def test_positive_negative_and_json_boundary_fixtures(self):
        report = self.workshop.validate(self.workspace)
        self.assertEqual(report["scored_cases"], 1)
        self.assertGreaterEqual(len(report["checks"]), 3)
        self.assertTrue(all(row["passed"] for row in report["checks"]))

    def test_zip_roundtrip_uses_existing_contract_scorer(self):
        pack = self.library.install_zip(self.build())
        self.assertEqual(pack.identity, "my_tasks@1.0.0")
        self.assertEqual(pack.cases[0].scorer_ref, "user_contract_v2")
        self.assertTrue((pack.root / "Source" / "Tasks" / "ticket.yaml").is_file())
        self.assertNotIn("answer", pack.cases[0].definition)
        self.assertNotIn("fixtures", pack.cases[0].definition)

    def test_repeat_build_is_byte_identical(self):
        self.assertEqual(self.build("a.zip").read_bytes(), self.build("b.zip").read_bytes())
        approved = self.workshop.validate(self.workspace)["source_sha256"]
        readme = self.workspace / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "Changed after preview.\n", encoding="utf-8")
        with self.assertRaises(PackValidationError) as caught:
            self.workshop.build(self.workspace, self.base / "changed.zip", expected_source_sha256=approved)
        self.assertEqual(caught.exception.code, "AUTHOR_SOURCE_CHANGED")

    def test_existing_output_is_never_overwritten(self):
        output = self.build(); before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(output.read_bytes(), before)
        from dataclasses import replace
        constrained = PackLibrary(self.library.root, self.library.policy,
                                  limits=replace(self.library.limits, max_archive_bytes=10))
        with self.assertRaises(PackValidationError):
            AuthorWorkshop(constrained).build(self.workspace, self.base / "tiny.zip")
        self.assertFalse((self.base / "tiny.zip").exists())
        self.assertFalse(list(self.base.glob(".bull-author-*.zip")))

    def test_wrong_reference_blocks_zip_creation(self):
        task = self.workspace / "Tasks" / "ticket.yaml"
        task.write_text(task.read_text(encoding="utf-8").replace("expected: B-104", "expected: B-999"), encoding="utf-8")
        with self.assertRaises(PackValidationError):
            self.build()
        self.assertFalse((self.base / "pack.zip").exists())

    def test_wrong_expected_failed_check_is_rejected(self):
        row = self.read("fixtures.json")
        row["cases"][0]["answers"][1]["failed_checks"] = ["ticket_quantity"]
        self.write("fixtures.json", row)
        self.assertFalse(self.workshop.validate(self.workspace)["passed"])
        with self.assertRaises(PackValidationError):
            self.build()

    def test_missing_positive_fixture_rejected(self):
        row = self.read("fixtures.json")
        row["cases"][0]["answers"] = row["cases"][0]["answers"][1:]
        self.write("fixtures.json", row)
        with self.assertRaises(PackValidationError):
            self.workshop.validate(self.workspace)

    def test_negative_coverage_must_include_every_criterion(self):
        row = self.read("fixtures.json")
        row["cases"][0]["answers"] = row["cases"][0]["answers"][:2]
        self.write("fixtures.json", row)
        with self.assertRaises(PackValidationError):
            self.workshop.validate(self.workspace)

    def test_manual_text_never_gains_an_automatic_score(self):
        row = self.read("author.json")
        row["tasks"].append({"file": "Tasks/poem.txt", "id": "poem", "title": "Poem", "description": "Review manually", "language": "en", "category": "creative", "case_version": 1})
        (self.workspace / "Tasks" / "poem.txt").write_text("Write a short original poem about rain.", encoding="utf-8")
        self.write("author.json", row)
        report = self.workshop.validate(self.workspace)
        self.assertEqual(report["manual_cases"], 1)
        pack = self.library.install_zip(self.build())
        poem = next(case for case in pack.cases if case.id == "poem")
        self.assertEqual(poem.scorer_ref, "none")
        self.assertTrue(poem.definition["manual_review_required"])

    def test_unknown_author_fields_rejected(self):
        self.source(shell="do not execute")
        with self.assertRaises(PackValidationError):
            self.workshop.validate(self.workspace)

    def test_unknown_yaml_fields_and_invalid_types_rejected(self):
        task = self.workspace / "Tasks" / "ticket.yaml"
        original = task.read_text(encoding="utf-8")
        for value in (original + "unknown: ignored\n", original.replace("weight: 40", "weight: true"),
                      original.replace("critical: true", "critical: yes"), original.replace("expected: B-104", 'expected: {"value": NaN}')):
            task.write_text(value, encoding="utf-8")
            with self.assertRaises(PackValidationError):
                self.workshop.validate(self.workspace)

    def test_duplicate_json_keys_rejected(self):
        path = self.workspace / "author.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'), encoding="utf-8")
        with self.assertRaises(PackValidationError):
            self.workshop.validate(self.workspace)

    def test_task_path_traversal_rejected(self):
        row = self.read("author.json"); row["tasks"][0]["file"] = "../outside.yaml"; self.write("author.json", row)
        with self.assertRaises(PackValidationError):
            self.workshop.validate(self.workspace)

    def test_extra_files_are_not_silently_exported(self):
        (self.workspace / "private.txt").write_text("Private test-only content", encoding="utf-8")
        with self.assertRaises(PackValidationError):
            self.build()

    def test_executable_payloads_are_rejected(self):
        (self.workspace / "setup.py").write_text("raise AssertionError('must never run')", encoding="utf-8")
        with self.assertRaises(PackValidationError):
            self.build()

    def test_output_inside_source_directory_rejected(self):
        with self.assertRaises(PackValidationError):
            self.workshop.build(self.workspace, self.workspace / "pack.zip")
        for name in ("nul.zip", "pack:stream.zip"):
            with self.assertRaises(PackValidationError):
                self.workshop.build(self.workspace, self.base / name)

    def test_safe_parameters_compile_without_runtime_calls(self):
        row = self.read("author.json")
        row["tasks"][0]["parameters"] = {"primary_predict": 600, "think_override": False, "benchmark_defaults": {"ctx": 8192, "temperature": 0.3}}
        self.write("author.json", row)
        pack = self.library.install_zip(self.build())
        self.assertEqual(pack.cases[0].definition["primary_predict"], 600)
        self.assertEqual(pack.cases[0].definition["benchmark_defaults"]["temperature"], 0.3)
        self.assertEqual(pack.cases[0].definition["benchmark_defaults"]["ctx"], 8192)

    def test_unknown_or_unsafe_parameters_are_rejected(self):
        for settings in ({"endpoint": "placeholder"}, {"primary_predict": -1}, {"primary_predict": 10 ** 400},
                         {"benchmark_defaults": {"num_ctx": True}}, {"benchmark_defaults": {"temperature": 10}}):
            row = self.read("author.json"); row["tasks"][0]["parameters"] = settings; self.write("author.json", row)
            with self.assertRaises(PackValidationError):
                self.workshop.validate(self.workspace)

    def test_new_copy_preserves_installed_version_and_selection(self):
        pack = self.library.install_zip(self.build()); store = PackSelection(self.library)
        snapshot = store.select(pack.id, pack.version)
        copy = self.workshop.copy_installed(pack.id, pack.version, "1.1.0")
        self.assertEqual(json.loads((copy / "author.json").read_text(encoding="utf-8"))["version"], "1.1.0")
        self.assertEqual(store.snapshot(), snapshot)
        new_pack = self.library.install_zip(self.workshop.build(copy, self.base / "new.zip"))
        self.assertNotEqual(pack.compiled_sha256, new_pack.compiled_sha256)
        self.assertEqual(len(self.library.scan()), 2)

    def test_copy_requires_different_explicit_version(self):
        pack = self.library.install_zip(self.build())
        with self.assertRaises(PackValidationError):
            self.workshop.copy_installed(pack.id, pack.version, pack.version)

    def test_tampered_embedded_sources_cannot_be_copied_as_trusted(self):
        pack = self.library.install_zip(self.build())
        path = pack.root / "Source" / "Tasks" / "ticket.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("B-104", "B-999"), encoding="utf-8")
        with self.assertRaises(PackValidationError):
            self.workshop.copy_installed(pack.id, pack.version, "1.1.0")

    def test_missing_author_source_has_clear_nonconversion_error(self):
        from Tests.pack_library_regression import _fixture, _zip, POLICY
        legacy = PackLibrary(self.base / "legacy", POLICY)
        pack = legacy.install_zip(_zip(self.base / "legacy.zip", _fixture(self.base)))
        with self.assertRaises(PackValidationError) as caught:
            AuthorWorkshop(legacy).copy_installed(pack.id, pack.version, "1.1.0")
        self.assertEqual(caught.exception.code, "AUTHOR_SOURCE_UNAVAILABLE")

    def test_russian_starter_preserves_language(self):
        root = self.workshop.create_starter("ru_tasks", language="ru")
        pack = self.library.install_zip(self.workshop.build(root, self.base / "ru.zip"))
        self.assertEqual(pack.cases[0].definition["expected_language"], "ru")

    def test_symlink_ancestor_rejected(self):
        from Shared.bull_llm.evaluation.pack_library import REPARSE_POINT
        from types import SimpleNamespace
        import stat
        with patch("Shared.bull_llm.evaluation.pack_library._lstat", return_value=SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=REPARSE_POINT)):
            with self.assertRaises(PackValidationError):
                self.workshop.validate(self.workspace)

    def test_no_legacy_100_task_truncation(self):
        row = self.read("author.json")
        for index in range(101):
            name = f"Tasks/text_{index}.txt"
            (self.workspace / name).write_text("Review this answer manually.", encoding="utf-8")
            row["tasks"].append({"file": name, "id": f"text_{index}", "title": "Manual", "description": "Manual review", "language": "en", "category": "manual", "case_version": 1})
        self.write("author.json", row)
        self.assertEqual(self.workshop.validate(self.workspace)["case_count"], 102)

    def test_duplicate_task_identity_rejected(self):
        row = self.read("author.json"); row["tasks"].append(dict(row["tasks"][0])); self.write("author.json", row)
        with self.assertRaises(PackValidationError):
            self.workshop.validate(self.workspace)

    def test_nonfinite_fixture_score_is_rejected(self):
        path = self.workspace / "fixtures.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"expected_score": 1.0', '"expected_score": NaN'), encoding="utf-8")
        with self.assertRaises(PackValidationError):
            self.workshop.validate(self.workspace)

    def test_archive_contains_no_workspace_absolute_path(self):
        with zipfile.ZipFile(self.build()) as archive:
            for name in archive.namelist():
                self.assertNotIn(str(self.base).encode(), archive.read(name))

    def test_incompatible_engine_is_rejected_before_zip(self):
        self.source(minimum_engine_version="99.0.0")
        with self.assertRaises(PackValidationError):
            self.workshop.validate(self.workspace)

    def test_cli_validate_and_build_are_offline(self):
        from Tools.build_author_pack import main
        import contextlib
        import io
        output = self.base / "cli.zip"
        common = ["--library-root", str(self.library.root)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(common + ["validate", str(self.workspace)]), 0)
            self.assertEqual(main(common + ["build", str(self.workspace), "--output", str(output)]), 0)
        self.assertEqual(self.library.inspect_zip(output).id, "my_tasks")

    def test_ui_cancel_is_read_only_and_english(self):
        from Shared.bull_llm.author_workshop_ui import workshop_menu
        from Shared.bull_llm.i18n import get_language, set_language
        from types import SimpleNamespace
        previous = get_language(); self.addCleanup(set_language, previous); set_language("en")
        unused = PackLibrary(self.base / "unused", self.library.policy)
        lines = []
        core = SimpleNamespace(benchmark_pack_library=lambda: unused, ui_header=lambda *args: lines.extend(args),
                               ui_menu_item=lambda *args: lines.extend(args), ui_print=lines.append,
                               read_user_input=lambda *args: "0")
        workshop_menu(core)
        self.assertFalse(unused.root.exists())
        self.assertTrue(any("AUTHOR WORKSHOP" in line for line in lines))

    def test_ui_create_and_validate_do_not_install_or_change_selection(self):
        from Shared.bull_llm.author_workshop_ui import workshop_menu
        from Shared.bull_llm.i18n import get_language, set_language
        from types import SimpleNamespace
        previous = get_language(); self.addCleanup(set_language, previous); set_language("en")
        values = iter(["1", "ui_tasks", "", "4", "", "0"])
        lines = []
        core = SimpleNamespace(benchmark_pack_library=lambda: self.library, ui_header=lambda *args: None,
                               ui_menu_item=lambda *args: None, ui_print=lines.append,
                               read_user_input=lambda *args: next(values), green=lambda: None, red=lambda: None, white=lambda: None)
        workshop_menu(core)
        self.assertEqual(self.library.scan(), ())
        self.assertIsNone(PackSelection(self.library).snapshot())
        self.assertTrue(any(line.startswith("PASS ") for line in lines))


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkshopTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("BULL Author Workshop regression failed")
    return result.testsRun


if __name__ == "__main__":
    run_suite()
