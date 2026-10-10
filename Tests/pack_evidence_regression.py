"""Captured pack content survives library changes; hashes are not signatures."""
from copy import deepcopy
import json
import tempfile
import unittest
from pathlib import Path

from Shared.bull_llm.evaluation.catalog import definitions_from_packs
from Shared.bull_llm.evaluation.pack_library import PackLibrary
from Shared.bull_llm.evaluation.pack_selection import PackSelection
from Shared.bull_llm.evaluation.registry import PackValidationError, canonical_sha256
from Tests.pack_library_regression import POLICY, _fixture, _zip


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        from Shared.bull_llm.evaluation.pack_evidence import capture_snapshot, snapshot_catalog
        self.capture, self.catalog = capture_snapshot, snapshot_catalog
        temp = tempfile.TemporaryDirectory(prefix="bull-pack-evidence-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.library = PackLibrary(self.base / "library", POLICY)
        self.pack = self.library.install_zip(_zip(self.base / "pack.zip", _fixture(self.base)))
        self.store = PackSelection(self.library)
        self.selection = self.store.select(self.pack.id, self.pack.version)
        self.snapshot = self.capture(self.pack, self.selection, POLICY)

    def resolve(self, snapshot=None, selection=None):
        return self.catalog(self.snapshot if snapshot is None else snapshot,
                            self.selection if selection is None else selection, POLICY)

    def resign(self, snapshot):
        snapshot.pop("snapshot_sha256", None)
        snapshot["snapshot_sha256"] = canonical_sha256(snapshot)
        return snapshot

    def test_complete_definition_roundtrip(self):
        self.assertEqual(self.resolve(), definitions_from_packs((self.pack,)))

    def test_removed_library_still_resolves_exact_snapshot(self):
        self.library.move_to_trash(self.pack.id, self.pack.version)
        self.store.clear()
        self.assertEqual(self.resolve()["safe_case"]["_pack"]["identity"], self.pack.identity)

    def test_current_selection_does_not_replace_snapshot(self):
        self.library.install_zip(_zip(self.base / "new.zip", _fixture(self.base, version="2.0.0")))
        self.store.select(self.pack.id, "2.0.0")
        self.assertEqual(self.resolve()["safe_case"]["_pack"]["identity"], self.pack.identity)

    def test_snapshot_json_roundtrip(self):
        self.assertEqual(self.resolve(json.loads(json.dumps(self.snapshot))), self.resolve())

    def test_returned_definitions_are_independent(self):
        first = self.resolve()
        first["safe_case"]["prompt"] = "changed"
        self.assertNotEqual(self.resolve()["safe_case"]["prompt"], "changed")

    def test_changed_prompt_rejected_even_with_outer_hash_recomputed(self):
        snap = deepcopy(self.snapshot)
        snap["compiled"]["cases"][0]["definition"]["prompt"] = "changed"
        with self.assertRaises(PackValidationError):
            self.resolve(self.resign(snap))

    def test_manifest_change_rejected(self):
        snap = deepcopy(self.snapshot)
        snap["manifest"]["title"] = "changed"
        with self.assertRaises(PackValidationError):
            self.resolve(self.resign(snap))

    def test_outer_hash_corruption_rejected(self):
        snap = deepcopy(self.snapshot)
        snap["snapshot_sha256"] = "0" * 64
        with self.assertRaises(PackValidationError):
            self.resolve(snap)

    def test_changed_case_selection_rejected(self):
        selection = deepcopy(self.selection)
        selection["case_ids"] = ["unknown"]
        with self.assertRaises(PackValidationError):
            self.resolve(selection=selection)

    def test_unknown_fields_rejected(self):
        snap = deepcopy(self.snapshot)
        snap["path"] = "private source"
        with self.assertRaises(PackValidationError):
            self.resolve(self.resign(snap))

    def test_nonfinite_data_rejected(self):
        snap = deepcopy(self.snapshot)
        snap["manifest"]["provenance"]["extra"] = float("nan")
        with self.assertRaises(PackValidationError):
            self.resolve(snap)

    def test_bounds_rejected(self):
        snap = deepcopy(self.snapshot)
        snap["manifest"]["description"] = "x" * (16 * 1024 * 1024)
        with self.assertRaises(PackValidationError):
            self.resolve(snap)

    def test_invalid_boolean_counts_rejected(self):
        selection = deepcopy(self.selection)
        selection["selected_cases"] = True
        with self.assertRaises(PackValidationError):
            self.resolve(selection=selection)

    def test_code_consent_cannot_be_inferred(self):
        from Shared.bull_llm.evaluation.pack_evidence import capture_snapshot, snapshot_catalog
        from Shared.bull_llm.evaluation.catalog import engine_registry_policy
        policy = engine_registry_policy("0.29.0.1")
        library = PackLibrary(self.base / "engine-library", policy)
        store = PackSelection(library)
        root = Path(__file__).resolve().parents[1]
        pack = library.install_zip(root / "BasePacks" / "bull_extended_core@1.0.0.zip")
        selection = store.select(pack.id, pack.version, ["python_debug"], allow_code_execution=True)
        snap = capture_snapshot(pack, selection, policy)
        selection["approved_code_cases"] = []
        with self.assertRaises(PackValidationError):
            snapshot_catalog(snap, selection, policy)

    def test_public_scope_does_not_disclose_author_or_prompts(self):
        from Shared.bull_llm.evaluation.pack_evidence import public_scope
        scope = public_scope(self.snapshot)
        self.assertEqual(scope["selected_cases"], 1)
        self.assertNotIn("title", scope)
        self.assertNotIn("manifest", scope)
        self.assertNotIn("compiled", scope)
        self.assertNotIn("case_ids", scope)
        self.assertNotIn(str(self.base), json.dumps(scope))

    def test_evidence_keeps_snapshot_private_and_coverage_public(self):
        from Shared.bull_llm.evidence import build_provenance, build_private_record_document, build_share_safe_summary_document
        provenance = build_provenance([], spec={"pack_run_snapshot": self.snapshot, "pack_selection": self.selection},
                                      engine_version="0.29.0.1")
        private = build_private_record_document([], provenance, pack_snapshot=self.snapshot)
        shared = build_share_safe_summary_document([], [], provenance)
        self.assertEqual(private["pack_run_snapshot"], self.snapshot)
        self.assertEqual(shared["provenance"]["pack_run_scope"]["coverage"], "full_pack")
        self.assertNotIn("safe prompt", json.dumps(shared))
        self.assertNotIn("pack_run_snapshot", shared)

    def test_html_provenance_is_escaped_and_contains_no_snapshot(self):
        from Shared.bull_llm.results_report import render_report
        scope = deepcopy(self.selection)
        scope["title"] = '<script>alert("fixture")</script>'
        html = render_report([], [], run_scope=scope, language="en")
        self.assertIn(scope["compiled_sha256"], html)
        self.assertNotIn('<script>alert(', html)
        self.assertNotIn(json.dumps(self.snapshot), html)


def run_suite():
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SnapshotTests))
    if not result.wasSuccessful():
        raise AssertionError("Pack evidence regression failed")
    return result.testsRun


if __name__ == "__main__":
    run_suite()
