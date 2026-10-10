"""Frozen prompt/runtime/scorer contracts for incremental pack extraction."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Shared.bull_llm.evaluation.catalog import definitions_from_packs
from Shared.bull_llm.evaluation.registry import PackRegistry, PackValidationError, load_pack

GOLD_PATH = ROOT / "Tests" / "Fixtures" / "engine_boundary_gold.json"


def run_suite(mod) -> int:
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    checks = []

    def check(name, action):
        action()
        checks.append(name)
        print("OK  Engine Boundary " + name)

    def frozen_definitions():
        definitions = mod.builtin_benchmarks()
        assert definitions == gold["definitions"]
        for name, item in definitions.items():
            expected = gold["fingerprints"][name]
            assert mod.canonical_sha256(item) == expected["definition_sha256"], name
            assert mod.benchmark_prompt_sha256(item) == expected["prompt_sha256"], name
            assert mod.benchmark_reference_sha256(item) == expected["reference_sha256"], name
            assert mod.benchmark_test_execution_fingerprint(item) == expected["execution_sha256"], name

    check("all 16 prompt/reference/runtime contracts frozen", frozen_definitions)

    def scorer_results():
        fixture = json.loads((ROOT / "Tests" / "Fixtures" / "benchmark_scorer_v3.json").read_text(encoding="utf-8"))
        expected = {row["id"]: row["score_sha256"] for row in gold["scorer_gold"]}
        assert set(expected) == {row["id"] for row in fixture["cases"]}
        for case in fixture["cases"]:
            score = mod.benchmark_score(case["benchmark"], gold["definitions"][case["benchmark"]], case.get("answer") or "")
            assert mod.canonical_sha256(score) == expected[case["id"]], case["id"]

    check("15 complete scorer results frozen", scorer_results)

    def catalog_contracts():
        with patch.object(mod, "builtin_benchmarks", side_effect=AssertionError("embedded catalog fallback")), \
             patch.object(mod, "benchmark_diagnostic_definitions", side_effect=AssertionError("diagnostic fallback")):
            definitions = mod.load_benchmarks()
        for name, expected in gold["fingerprints"].items():
            item = definitions[name]
            assert mod.benchmark_test_execution_fingerprint(item) == expected["execution_sha256"], name
            assert mod.benchmark_prompt_sha256(item) == expected["prompt_sha256"], name
            assert item["_pack"]["definition_sha256"] == expected["definition_sha256"], name
            raw = dict(item)
            raw.pop("_pack")
            assert mod.canonical_sha256(raw) == expected["definition_sha256"], name
        assert definitions["simpson"]["_pack"]["identity"] == "bull_chat_core@1.0.0"
        assert definitions["analytics_case"]["_pack"]["identity"] == "bull_extended_core@1.0.0"

    check("runnable catalog preserves all contracts and adds provenance", catalog_contracts)

    policy = mod.benchmark_registry_policy()
    with tempfile.TemporaryDirectory(prefix="bull-engine-boundary-") as temporary:
        root = Path(temporary)
        empty = PackRegistry([root / "not-installed"], [], policy)

        def empty_catalog():
            with patch.object(mod, "benchmark_pack_registry", return_value=empty), \
                 patch.object(mod, "appdir", return_value=root), \
                 patch.object(mod, "builtin_benchmarks", side_effect=AssertionError("embedded fallback")):
                assert mod.load_benchmarks() == {}
            assert not (root / "not-installed").exists()

        check("no installed packs means no implicit tests or filesystem writes", empty_catalog)

        def independent_pack():
            from Tests.registry_regression import _make_pack
            private_root = root / "private"
            _make_pack(private_root, policy)
            independent = PackRegistry([], [private_root], policy)
            with patch.object(mod, "benchmark_pack_registry", return_value=independent), \
                 patch.object(mod, "appdir", return_value=root), \
                 patch.object(mod, "builtin_benchmarks", side_effect=AssertionError("CHAT dependency")):
                definitions = mod.load_benchmarks()
                assert set(definitions) == {"safe_task"}
                assert definitions["safe_task"]["_pack"]["identity"] == "private_safe_task@1.0.0"

        check("independent pack runs without CHAT Core or client edits", independent_pack)

        def fixed_capabilities():
            with patch.object(mod, "builtin_benchmarks", side_effect=AssertionError("content defines permissions")):
                actual = mod.benchmark_registry_policy({"fake": {"score_type": "load_arbitrary_code"}})
            assert actual == policy
            assert "load_arbitrary_code" not in actual.scorer_refs
            assert "user_contract_v2" in actual.scorer_refs

        check("engine capability allowlist cannot be extended by pack content", fixed_capabilities)

        def missing_before_backend():
            with patch.object(mod, "benchmark_pack_registry", return_value=empty), \
                 patch.object(mod, "appdir", return_value=root), \
                 patch.object(mod, "model_catalog", side_effect=AssertionError("backend contacted")):
                for tests in ([], ["simpson"]):
                    try:
                        mod.make_benchmark_spec(tests, ["fixture-model"], 1, False)
                    except PackValidationError as error:
                        assert error.code == "BENCHMARK_CASE_NOT_AVAILABLE"
                    else:
                        raise AssertionError("unavailable tests must fail before inference")

        check("missing selected tests fail clearly before any backend call", missing_before_backend)

        def diagnostic_without_packs():
            with patch.object(mod, "benchmark_pack_registry", return_value=empty):
                result = mod.benchmark_scorer_selftest()
                assert result["ok"] is True and result["total"] == 15

        check("offline scorer self-check does not require installed packs", diagnostic_without_packs)

        def saved_results_without_packs():
            from Tests.evidence_regression import _record
            records = [_record()]
            expected = mod.benchmark_model_summary_rows(records)
            with patch.object(mod, "benchmark_pack_registry", return_value=empty), \
                 patch.object(mod, "appdir", return_value=root):
                actual = mod.benchmark_model_summary_rows(records)
            assert actual == expected and actual[0]["model"] == "fixture-model"

        check("saved result summary remains readable without installed packs", saved_results_without_packs)

        def historical_audit_without_packs():
            with patch.object(mod, "benchmark_pack_registry", return_value=empty):
                result = mod._legacy_rescore_one("ru_context_corrections", 2, "")
            assert result["method"] != "legacy_audit_unavailable"

        check("historical audit uses diagnostic contracts not live pack content", historical_audit_without_packs)

    def duplicate_ids():
        pack = load_pack(ROOT / "BenchmarkPacks" / "bull_chat_core", policy)
        try:
            definitions_from_packs([pack, pack])
        except PackValidationError as error:
            assert error.code == "DUPLICATE_CASE_ID"
        else:
            raise AssertionError("case overwrite must not be silent")

    check("ambiguous case IDs rejected rather than overwritten", duplicate_ids)

    def independent_copies():
        pack = load_pack(ROOT / "BenchmarkPacks" / "bull_chat_core", policy)
        first = definitions_from_packs([pack])
        first["ru_business_tone"]["constraints"]["word_range"][0] = 999
        first["ru_business_tone"]["_pack"]["identity"] = "changed"
        second = definitions_from_packs([pack])
        assert second["ru_business_tone"]["constraints"]["word_range"][0] != 999
        assert second["ru_business_tone"]["_pack"]["identity"] == pack.identity

    check("preview mutations cannot change loaded pack definitions", independent_copies)
    return len(checks)


if __name__ == "__main__":
    import importlib.util
    import sys

    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("bull_boundary_test_core", ROOT / "bull_client_v0.29.0.1.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    count = run_suite(core)
    print(f"PASS {count}/{count}")
