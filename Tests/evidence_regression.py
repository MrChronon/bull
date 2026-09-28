"""Offline contract tests for T4 BULL Evidence."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _record(seed: int = 42) -> dict:
    return {
        "record_schema_version": 12,
        "execution_status": "ok",
        "identity": {
            "benchmark": "fixture_case",
            "benchmark_category": "fixture_category",
            "benchmark_version": 1,
            "benchmark_prompt_sha256": "1" * 64,
            "benchmark_reference_sha256": "2" * 64,
            "benchmark_execution_sha256": "3" * 64,
            "benchmark_pack_identity": "fixture_pack@1.0.0",
            "benchmark_pack_manifest_sha256": "4" * 64,
            "benchmark_definition_sha256": "5" * 64,
            "scorer_ref": "fixture_scorer",
            "scorer_sha256": "6" * 64,
            "verifier_ref": "fixture_verifier",
            "verifier_sha256": "7" * 64,
            "backend": "ollama",
            "model": "fixture-model",
            "run": 1,
            "attempt": 1,
        },
        "config": {
            "seed": seed,
            "ctx": 8192,
            "backend_launch_fingerprint": "8" * 64,
            "effective_runtime_request_fingerprint": "9" * 64,
            "effective_profile_fingerprint": "a" * 64,
        },
        "primary": {"answer": "private native answer", "generation_completed": True},
        "final": {"answer": "private final answer", "generation_completed": True},
        "score": {"native": {"method": "fixture_scorer", "value": 0.75}, "final": {"value": 0.8}},
        "telemetry": {"runtime": {"observed_fingerprint": "b" * 64}},
        "schedule": {"global_position": 0, "round_position": 0, "block_position": 0},
    }


def _case_row() -> dict:
    return {
        "benchmark": "fixture_case", "benchmark_category": "fixture_category",
        "benchmark_version": 1, "model": "fixture-model", "backend": "ollama",
        "runs_planned": 3, "runs_executed": 3, "errors": 0, "seeds": [42, 43, 44],
        "context_length": 8192, "context_lengths": [8192],
        "native_score_avg": 0.75, "native_score_sd": 0.05, "native_score_min": 0.7,
        "native_score_max": 0.8, "native_score_ci95_low": 0.69, "native_score_ci95_high": 0.81,
        "native_score_valid_runs": 3, "native_score_worst_seed": 42,
        "final_score_avg": 0.8, "final_score_sd": 0.02, "final_score_min": 0.78,
        "final_score_max": 0.82, "final_score_ci95_low": 0.77, "final_score_ci95_high": 0.83,
        "final_score_valid_runs": 3, "final_score_worst_seed": 42,
        "native_generation_completion_rate": 1.0, "native_task_completion_rate": 2 / 3,
        "generation_completion_rate": 1.0, "task_completion_rate": 1.0,
        "primary_eval_warm_avg": 20.0, "primary_eval_avg": 18.0, "primary_eval_sd": 2.0,
        "primary_eval_min": 16.0, "primary_eval_max": 20.0,
        "pipeline_wall_avg": 10.0, "pipeline_wall_sd": 1.0, "pipeline_wall_min": 9.0,
        "pipeline_wall_max": 11.0, "pipeline_wall_ci95_low": 8.9, "pipeline_wall_ci95_high": 11.1,
        "load_states": ["cold", "warm", "warm"], "vram_peak_mib": 10240,
        "recovery_rate": 1 / 3, "recovery_dependency": "mixed", "client_attempts": 4,
        "client_transport_failures": 1, "client_resumed_runs": 1,
        "client_recovery_excluded_from_model_score": True,
        "rank_stability": 1.0, "rank_stability_status": "available",
        "pareto_status": "non_dominated_with_95pct_uncertainty",
        "backend_launch_fingerprints": ["8" * 64],
        "effective_runtime_request_fingerprints": ["9" * 64],
        "observed_runtime_fingerprints": ["b" * 64],
    }


def _model_row() -> dict:
    return {
        "model": "fixture-model", "backend": "ollama", "chat_native_score": 0.75,
        "chat_assisted_score": 0.8, "chat_native_mean": 0.75, "chat_native_sd": 0.05,
        "chat_native_min": 0.7, "chat_native_max": 0.8, "chat_native_ci95": [0.69, 0.81],
        "chat_assisted_mean": 0.8, "chat_assisted_sd": 0.02, "chat_assisted_min": 0.78,
        "chat_assisted_max": 0.82, "chat_category_scores_native": {"reasoning": 0.75},
        "chat_category_scores_assisted": {"reasoning": 0.8},
        "native_generation_completion_rate": 1.0, "native_task_completion_rate": 2 / 3,
        "generation_completion_rate": 1.0, "task_completion_rate": 1.0,
        "primary_eval_warm_avg": 20.0, "vram_peak_mib": 10240,
        "recovery_rate": 1 / 3, "critical_failure_count": 1,
        "worst_test": "fixture_case", "chat_native_worst_seed": 42, "chat_suite_status": "complete",
    }


class EvidenceContractTests(unittest.TestCase):
    def _provenance(self):
        from Shared.bull_llm.evidence import build_provenance
        return build_provenance(
            [_record()], spec={"spec_fingerprint": "c" * 64}, engine_version="v0.25.0.0",
            source_sha256="d" * 64, created_at_utc="2000-01-01T00:00:00+00:00",
        )

    def test_provenance_is_hashed_and_runtime_spaces_are_separate(self):
        from Shared.bull_llm.evidence import validate_provenance
        provenance = self._provenance()
        validate_provenance(provenance)
        fingerprints = provenance["fingerprints"]
        self.assertEqual(fingerprints["launch"], ["8" * 64])
        self.assertEqual(fingerprints["effective_runtime_request"], ["9" * 64])
        self.assertEqual(fingerprints["observed_runtime"], ["b" * 64])
        changed = deepcopy(provenance)
        changed["fingerprints"]["launch"] = []
        with self.assertRaises(ValueError):
            validate_provenance(changed)

    def test_private_record_keeps_native_evidence_and_is_explicit(self):
        from Shared.bull_llm.evidence import build_private_record_document
        document = build_private_record_document([_record()], self._provenance())
        self.assertEqual(document["schema"], "bull-benchmark-record")
        self.assertEqual(document["artifact_classification"], "private")
        self.assertEqual(document["records"][0]["primary"]["answer"], "private native answer")

    def test_share_safe_summary_has_disjoint_metric_spaces(self):
        from Shared.bull_llm.evidence import build_share_safe_summary_document
        document = build_share_safe_summary_document([_model_row()], [_case_row()], self._provenance())
        case = document["metrics"]["case"][0]
        self.assertEqual(case["quality"]["native"]["mean"], 0.75)
        self.assertEqual(case["quality"]["assisted"]["mean"], 0.8)
        self.assertNotIn("score", case)
        self.assertTrue(case["recovery"]["excluded_from_model_score"])
        self.assertIn("quality.native", document["metric_spaces"])
        self.assertIn("security", document["metric_spaces"])

    def test_share_safe_summary_contains_report_analytics(self):
        from Shared.bull_llm.evidence import build_share_safe_summary_document
        analytics = build_share_safe_summary_document(
            [_model_row()], [_case_row()], self._provenance()
        )["analytics"]
        self.assertTrue(analytics["confidence_intervals"][0]["available"])
        self.assertEqual(analytics["latency_distributions"][0]["mean"], 10.0)
        self.assertEqual(analytics["context_curves"][0]["points"][0]["context_length"], 8192)
        self.assertEqual(analytics["category_heatmap"][0]["category"], "reasoning")

    def test_privacy_audit_rejects_content_endpoint_home_and_email(self):
        from Shared.bull_llm.evidence import audit_share_safe
        bad_values = (
            {"prompt": "secret"},
            {"note": "http://private.example:11434"},
            {"note": "C:\\Users\\person\\private.json"},
            {"note": "person@example.test"},
        )
        for value in bad_values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit_share_safe(value)

    def test_schema_files_define_new_named_contracts(self):
        record = json.loads((ROOT / "Schemas" / "bull_benchmark_record_v1.schema.json").read_text(encoding="utf-8"))
        summary = json.loads((ROOT / "Schemas" / "bull_benchmark_summary_v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(record["properties"]["schema"]["const"], "bull-benchmark-record")
        self.assertEqual(summary["properties"]["schema"]["const"], "bull-benchmark-summary")

    def test_save_writes_private_and_share_safe_documents(self):
        from Shared.bull_llm.evidence import save_evidence_artifacts
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "run.json"
            raw.write_text(json.dumps([_record()]), encoding="utf-8")
            private, share, document = save_evidence_artifacts(
                raw, spec={"spec_fingerprint": "c" * 64}, records=[_record()],
                model_rows=[_model_row()], case_rows=[_case_row()], engine_version="v0.25.0.0",
            )
            self.assertTrue(private.is_file())
            self.assertTrue(share.is_file())
            self.assertEqual(document["artifact_classification"], "share_safe")
            self.assertNotIn("private native answer", share.read_text(encoding="utf-8"))

    def test_record_migration_is_copy_only_and_never_overwrites(self):
        from Shared.bull_llm.evidence import migrate_legacy_record_copy
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "legacy.json"
            destination = Path(tmp) / "migrated.json"
            source.write_text(json.dumps([_record()]), encoding="utf-8")
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            migrate_legacy_record_copy(source, destination, engine_version="v0.25.0.0")
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            with self.assertRaises(FileExistsError):
                migrate_legacy_record_copy(source, destination, engine_version="v0.25.0.0")

    def test_summary_migration_rejects_private_legacy_content(self):
        from Shared.bull_llm.evidence import migrate_legacy_summary_copy
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "summary.json"
            source.write_text(json.dumps([{"benchmark": "x", "model": "m", "prompt": "secret"}]), encoding="utf-8")
            # Normalization is an allow-list, so unknown legacy content cannot leak.
            target = migrate_legacy_summary_copy(source, Path(tmp) / "share.json", engine_version="v0.25.0.0")
            text = target.read_text(encoding="utf-8")
            self.assertNotIn("secret", text)
            self.assertNotIn('"prompt"', text)


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(EvidenceContractTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("BULL Evidence regression failed")
    return result.testsRun


if __name__ == "__main__":
    run_suite()
