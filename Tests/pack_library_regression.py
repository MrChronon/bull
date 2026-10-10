"""Offline security and version-retention contracts for ZIP pack installation."""

from __future__ import annotations

import io
import json
import stat
import struct
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from Shared.bull_llm.evaluation.pack_library import (
    PackLibrary, ZipLimits, default_pack_library_root,
)
from Shared.bull_llm.evaluation.registry import (
    PackValidationError, RegistryPolicy, canonical_sha256, write_pack_lock,
)


POLICY = RegistryPolicy(
    engine_version="0.29.0.1", runner_refs=frozenset({"single_turn_v1"}),
    scorer_refs=frozenset({"none"}), verifier_refs=frozenset({"benchmark_contract_v1"}),
)


def _json_write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _fixture(parent, *, version="1.0.0", visibility="private"):
    import hashlib

    root = parent / ("source-" + version)
    root.mkdir()
    definition = {"version": 1, "category": "custom", "score_type": "none", "prompt": "Return OK."}
    cases = [{"id": "safe_case", "version": 1, "category": "custom", "runner_ref": "single_turn_v1",
              "scorer_ref": "none", "verifier_ref": "benchmark_contract_v1", "definition": definition}]
    gold = {"schema": "bull-benchmark-pack-gold", "schema_version": 1, "cases": [{
        "id": "safe_case", "version": 1, "definition_sha256": canonical_sha256(definition),
        "prompt_sha256": hashlib.sha256(b"Return OK.").hexdigest(),
        "result_instruction_sha256": hashlib.sha256(b"").hexdigest(),
    }]}
    manifest = {
        "schema": "bull-benchmark-pack-manifest", "schema_version": 1, "id": "author_tasks",
        "version": version, "title": "Author tasks", "description": "Synthetic test fixture",
        "status": "experimental", "visibility": visibility,
        "engine": {"minimum_version": "0.29.0.1"},
        "license": {"id": "LicenseRef-Test", "name": "Test fixture", "file": "LICENSE.txt"},
        "provenance": {"source": "Synthetic regression fixture"}, "taxonomy": ["custom"],
        "content": {"cases_file": "cases.json", "sha256": canonical_sha256(cases), "case_count": 1},
        "gold": {"file": "gold.json", "sha256": canonical_sha256(gold)}, "documentation": "README.md",
    }
    for name, value in (("manifest.json", manifest), ("cases.json", cases), ("gold.json", gold)):
        _json_write(root / name, value)
    (root / "README.md").write_text("Synthetic fixture; no semantic score.", encoding="utf-8")
    (root / "LICENSE.txt").write_text("Synthetic test fixture only.", encoding="utf-8")
    write_pack_lock(root, POLICY, visibility)
    return {path.name: path.read_bytes() for path in root.iterdir()}


def _zip(path, rows, *, prefix="", extras=(), compression=zipfile.ZIP_STORED):
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, data in rows.items():
            archive.writestr(prefix + name, data)
        for name, data in extras:
            if isinstance(name, str):
                entry = zipfile.ZipInfo(name)
                # zipfile normalizes backslashes on Windows while constructing
                # ZipInfo. Write a deliberately raw attacker-controlled path.
                entry.filename = entry.orig_filename = name
                entry.compress_type = compression
            else:
                entry = name
            archive.writestr(entry, data)
    return path


class PackLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bull-pack-tests-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "library"
        self.library = PackLibrary(self.root, POLICY)
        self.rows = _fixture(self.base)

    def install(self, *, rows=None, extras=(), prefix="", compression=zipfile.ZIP_STORED):
        archive = _zip(self.base / "pack.zip", self.rows if rows is None else rows,
                       prefix=prefix, extras=extras, compression=compression)
        return self.library.install_zip(archive)

    def reject(self, code, **kwargs):
        with self.assertRaises(PackValidationError) as caught:
            self.install(**kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.library.scan(), ())
        self.assertFalse((self.root / ".install.lock").exists())

    def test_reading_empty_library_does_not_create_directories(self):
        self.assertEqual(self.library.scan(), ())
        self.assertFalse(self.root.exists())

    def test_default_location_is_per_user_not_bundle_or_cwd(self):
        actual = default_pack_library_root({"LOCALAPPDATA": str(self.base)}, platform="win32")
        self.assertEqual(actual, self.base / "BULL" / "BenchmarkPacks")
        for environment in ({}, {"LOCALAPPDATA": "relative"}):
            with self.assertRaises(PackValidationError):
                default_pack_library_root(environment, platform="win32")
        with self.assertRaises(PackValidationError):
            default_pack_library_root({}, platform="linux")

    def test_root_and_wrapper_archives_keep_exact_manifest_and_content(self):
        for prefix, visibility in (("", "private"), ("my-pack/", "public")):
            with self.subTest(prefix=prefix):
                version = "1.0.0" if visibility == "private" else "1.1.0"
                rows = self.rows if visibility == "private" else _fixture(self.base, version=version, visibility=visibility)
                installed = self.install(rows=rows, prefix=prefix)
                self.assertEqual(installed.identity, "author_tasks@" + version)
                self.assertEqual(installed.root.parent.name, visibility)
                self.assertEqual(self.library.get(installed.id, installed.version).compiled_sha256, installed.compiled_sha256)
                for name, data in rows.items():
                    self.assertEqual((installed.root / name).read_bytes(), data)

    def test_reinstall_is_rejected_without_overwriting_first_version(self):
        pack = self.install()
        before = (pack.root / "manifest.json").read_bytes()
        with self.assertRaises(PackValidationError) as caught:
            self.install()
        self.assertEqual(caught.exception.code, "PACK_VERSION_EXISTS")
        self.assertEqual((pack.root / "manifest.json").read_bytes(), before)
        self.assertEqual(len(self.library.scan()), 1)

    def test_upgrade_retains_exact_previous_version_and_requires_explicit_version(self):
        first = self.install()
        second = self.install(rows=_fixture(self.base, version="1.1.0"))
        self.assertEqual(len(self.library.scan()), 2)
        self.assertEqual(self.library.get("author_tasks", "1.0.0").compiled_sha256, first.compiled_sha256)
        self.assertEqual(self.library.get("author_tasks", "1.1.0").root, second.root)
        with self.assertRaises(TypeError):
            self.library.get("author_tasks")
        with self.assertRaises(PackValidationError):
            self.library.get("../escape", "1.0.0")

    def test_traversal_absolute_ads_and_windows_ambiguous_names_are_rejected(self):
        for name in ("../escape.txt", "/escape.txt", "C:/escape.txt", "a\\escape.txt", "a/../x.txt",
                     "a/./x.txt", "file.txt:stream", "CON.txt", "a/NUL.md", "CONIN$.txt",
                     "trailing .txt ", "a//x.txt", "nul\x00hidden.txt"):
            with self.subTest(name=name):
                self.reject("ZIP_UNSAFE_PATH", extras=[(name, b"unsafe")])
        self.assertFalse((self.base / "escape.txt").exists())

    def test_duplicate_case_collisions_and_file_directory_collisions_are_rejected(self):
        for extras in ([("README.MD", b"collision")], [("Folder/a.txt", b"a"), ("folder/b.txt", b"b")],
                       [("a.txt", b"a"), ("a.txt/b.txt", b"b")]):
            with self.subTest(extras=extras):
                self.reject("ZIP_PATH_COLLISION", extras=extras)

    def test_symlink_and_special_file_entries_are_rejected(self):
        for kind in (stat.S_IFLNK, stat.S_IFIFO):
            entry = zipfile.ZipInfo("link.txt")
            entry.create_system = 3
            entry.external_attr = (kind | 0o600) << 16
            self.reject("ZIP_LINK_OR_SPECIAL_FILE", extras=[(entry, b"outside")])

    def test_unknown_or_executable_suffix_is_not_extracted(self):
        for name in ("setup.py", "script.PS1", "module.dll", "payload.bin", ".hidden.txt"):
            with self.subTest(name=name):
                self.reject("ZIP_FILE_TYPE_FORBIDDEN", extras=[(name, b"unused")])

    def test_crc_damage_cleans_staging_and_keeps_existing_pack(self):
        installed = self.install()
        rows = _fixture(self.base, version="1.1.0")
        path = _zip(self.base / "broken.zip", rows)
        data = bytearray(path.read_bytes())
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo("README.md")
            offset = info.header_offset
            name_len, extra_len = struct.unpack_from("<HH", data, offset + 26)
            data[offset + 30 + name_len + extra_len] ^= 1
        path.write_bytes(data)
        with self.assertRaises(PackValidationError) as caught:
            self.library.install_zip(path)
        self.assertEqual(caught.exception.code, "ZIP_INVALID")
        self.assertEqual([row.pack.identity for row in self.library.scan()], [installed.identity])
        self.assertEqual(list((self.root / ".staging").iterdir()), [])

    def test_manifest_or_lock_damage_never_publishes_pack(self):
        for name in ("cases.json", "pack.lock.json"):
            rows = dict(self.rows)
            rows[name] = b"{}"
            with self.subTest(name=name), self.assertRaises(PackValidationError):
                self.install(rows=rows)
            self.assertEqual(self.library.scan(), ())
            self.assertEqual(list((self.root / ".staging").iterdir()), [])

    def test_only_one_pack_and_no_unrelated_root_files(self):
        self.reject("ZIP_PACK_LAYOUT", prefix="pack/", extras=[("unrelated.txt", b"extra")])
        self.reject("ZIP_PACK_LAYOUT", prefix="pack/", extras=[("other/manifest.json", b"{}")])

    def test_archive_expansion_file_and_entry_budgets_are_enforced(self):
        for limit in (replace(ZipLimits(), max_archive_bytes=1), replace(ZipLimits(), max_total_bytes=1),
                      replace(ZipLimits(), max_file_bytes=1), replace(ZipLimits(), max_entries=1)):
            with self.subTest(limit=limit):
                self.library = PackLibrary(self.root, POLICY, limits=limit)
                self.reject("ZIP_LIMIT_EXCEEDED")

    def test_zip_bomb_ratio_is_rejected(self):
        self.reject("ZIP_LIMIT_EXCEEDED", extras=[("padding.txt", b"0" * 100_000)], compression=zipfile.ZIP_DEFLATED)

    def test_encrypted_entry_is_rejected_before_extraction(self):
        path = _zip(self.base / "encrypted.zip", self.rows)
        data = bytearray(path.read_bytes())
        position = data.index(b"PK\x01\x02")
        struct.pack_into("<H", data, position + 8, 1)
        path.write_bytes(data)
        with self.assertRaises(PackValidationError) as caught:
            self.library.install_zip(path)
        self.assertEqual(caught.exception.code, "ZIP_ENCRYPTED")
        self.assertFalse(self.root.exists())

    def test_exclusive_lock_is_not_stolen_or_removed(self):
        self.root.mkdir()
        lock = self.root / ".install.lock"
        lock.write_bytes(b"another installer")
        with self.assertRaises(PackValidationError) as caught:
            self.install()
        self.assertEqual(caught.exception.code, "PACK_INSTALL_BUSY")
        self.assertEqual(lock.read_bytes(), b"another installer")
        self.assertEqual(self.library.scan(), ())

    def test_failed_publish_cleans_staging_and_lock(self):
        with patch("Shared.bull_llm.evaluation.pack_library.os.rename", side_effect=OSError("fixture failure")):
            with self.assertRaises(PackValidationError) as caught:
                self.install()
        self.assertEqual(caught.exception.code, "PACK_INSTALL_IO")
        self.assertEqual(self.library.scan(), ())
        self.assertEqual(list((self.root / ".staging").iterdir()), [])
        self.assertFalse((self.root / ".install.lock").exists())

    def test_library_reparse_attribute_is_rejected_without_windows_symlink_privilege(self):
        import types

        self.root.mkdir()
        real_lstat = Path.lstat

        def fixture_lstat(path):
            if path == self.root:
                return types.SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return real_lstat(path)

        with patch.object(Path, "lstat", fixture_lstat):
            with self.assertRaises(PackValidationError) as caught:
                self.install()
        self.assertEqual(caught.exception.code, "PACK_LIBRARY_LINK")

    def test_invalid_version_is_listed_but_does_not_hide_valid_version(self):
        installed = self.install()
        bad = installed.root.parent / "author_tasks@1.1.0"
        bad.mkdir()
        (bad / "manifest.json").write_text("{}", encoding="utf-8")
        findings = self.library.scan()
        self.assertEqual(len(findings), 2)
        self.assertEqual(sum(row.pack is not None for row in findings), 1)
        self.assertEqual(self.library.get("author_tasks", "1.0.0").identity, installed.identity)
        with self.assertRaises(PackValidationError):
            self.library.get("author_tasks", "1.1.0")

    def test_duplicate_manifest_key_and_nonfinite_value_are_rejected(self):
        for payload, code in ((b'{"visibility":"public","visibility":"private"}', "DUPLICATE_JSON_KEY"),
                              (b'{"visibility":"private","value":NaN}', "NONFINITE_JSON"),
                              (b'{"visibility":', "INVALID_JSON")):
            rows = dict(self.rows)
            rows["manifest.json"] = payload
            self.reject(code, rows=rows)

    def test_unknown_runner_and_engine_incompatibility_fail_before_publish(self):
        rows = dict(self.rows)
        cases = json.loads(rows["cases.json"])
        cases[0]["runner_ref"] = "external_python"
        rows["cases.json"] = json.dumps(cases).encode()
        manifest = json.loads(rows["manifest.json"])
        manifest["content"]["sha256"] = canonical_sha256(cases)
        rows["manifest.json"] = json.dumps(manifest).encode()
        self.reject("UNKNOWN_RUNNER", rows=rows)
        rows = dict(self.rows)
        manifest = json.loads(rows["manifest.json"])
        manifest["engine"]["minimum_version"] = "99.0.0"
        rows["manifest.json"] = json.dumps(manifest).encode()
        self.reject("INCOMPATIBLE_ENGINE", rows=rows)

    def test_data_source_files_are_retained_but_not_automatically_run(self):
        installed = self.install(extras=[("Sources/task.yaml", b"prompt: |\n  Draft task\n")])
        self.assertEqual((installed.root / "Sources" / "task.yaml").read_bytes(), b"prompt: |\n  Draft task\n")
        self.assertEqual([case.id for case in installed.cases], ["safe_case"])

    def test_atomic_publish_moves_only_fully_validated_pack(self):
        import os

        rename = os.rename
        observations = []

        def observe(source, target):
            self.assertEqual(self.library.scan(), ())
            self.assertTrue((source / "pack.lock.json").is_file())
            self.assertFalse(target.exists())
            observations.append(True)
            return rename(source, target)

        with patch("Shared.bull_llm.evaluation.pack_library.os.rename", side_effect=observe):
            installed = self.install()
        self.assertEqual(observations, [True])
        self.assertEqual(self.library.get(installed.id, installed.version).root, installed.root)

    def test_lookup_rejects_symlink_attribute_before_reading_manifest(self):
        import types

        installed = self.install()
        real_lstat = Path.lstat

        def fixture_lstat(path):
            if path == installed.root / "cases.json":
                return types.SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400)
            return real_lstat(path)

        with patch.object(Path, "lstat", fixture_lstat):
            findings = self.library.scan()
            self.assertEqual(findings[0].error_code, "PACK_LIBRARY_LINK")
            with self.assertRaises(PackValidationError):
                self.library.get(installed.id, installed.version)

    def test_limits_reject_invalid_types_and_values(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ZipLimits(max_entries=value)

    def test_llm_author_examples_parse_and_positive_negative_scores_match_docs(self):
        import re
        from Shared.bull_llm.user_tests import parse_user_test_yaml, validate_user_test, score_user_test

        root = Path(__file__).resolve().parents[1]
        positive = 'BENCHMARK_RESULT\n{"result":{"id":"B-104","quantity":3,"confirmed":false}}'
        for language in ("en", "ru"):
            guide = root / "Docs" / language / "PACK_AUTHOR_LLM.md"
            examples = re.findall(r"```yaml\n(.*?)\n```", guide.read_text(encoding="utf-8"), re.S)
            self.assertEqual(len(examples), 1)
            task = validate_user_test(parse_user_test_yaml(examples[0]))
            self.assertEqual(task["language"], language)
            config = {"criteria": task["criteria"], "manual_review": task["manual_review"]}
            self.assertAlmostEqual(score_user_test(positive, config)["value"], 1.0)
            negative = score_user_test(positive.replace("false", "true"), config)
            self.assertAlmostEqual(negative["value"], 0.59)
            self.assertEqual([row["criterion"] for row in negative["critical_failures"]], ["ticket_confirmation"])
            self.assertEqual(score_user_test(positive + "\nTrailing text.", config)["value"], 0)
            self.assertTrue(score_user_test(positive, config)["manual_review_required"])


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PackLibraryTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Pack Library regression failed")
    return result.testsRun


if __name__ == "__main__":
    run_suite()
