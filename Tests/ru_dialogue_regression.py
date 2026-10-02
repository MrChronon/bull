"""Regression contracts for the BULL RU Dialogue development benchmark."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "BenchmarkPacks" / "bull_ru_dialogue"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_suite(mod) -> int:
    checks = []

    def check(name, fn):
        fn()
        checks.append(name)
        print("OK  RU Dialogue " + name)

    def sample_item():
        return {
            "score_type": "ru_dialogue_contract_v1",
            "reference": {"project": "Vega", "cloud_allowed": False},
            "dialogue_contract": {
                "weights": {"semantic": 0.8, "structural": 0.2},
                "sections": [{
                    "id": "current",
                    "prefix": "Текущее состояние:",
                    "required_any": [["Vega"], ["облако запрещено", "без облака"]],
                    "forbidden": ["облако разрешено"],
                    "critical": True,
                }],
                "constraints": {"line_count": 1, "forbid_exclamation": True, "expected_language": "ru"},
            },
        }

    def perfect_answer_separates_dimensions():
        answer = (
            "Текущее состояние: проект Vega, облако запрещено.\n\n"
            "BENCHMARK_RESULT\n"
            '{"project":"Vega","cloud_allowed":false}'
        )
        score = mod.benchmark_score("fixture", sample_item(), answer)
        assert score["value"] == 1.0
        assert score["semantic_score"] == 1.0
        assert score["structural_score"] == 1.0
        assert not score["critical_failures"]
        assert score["manual_review_required"] is False

    check("perfect semantic and structural result", perfect_answer_separates_dimensions)

    def semantic_failure_is_capped_and_auditable():
        answer = (
            "Текущее состояние: проект Vega, облако разрешено.\n\n"
            "BENCHMARK_RESULT\n"
            '{"project":"Vega","cloud_allowed":true}'
        )
        score = mod.benchmark_score("fixture", sample_item(), answer)
        assert score["semantic_score"] < 1.0
        assert score["structural_score"] == 1.0
        assert score["value"] <= 0.55
        assert score["manual_review_required"] is True
        assert all(row.get("evidence") and row.get("reason") for row in score["critical_failures"])

    check("critical failures are capped and auditable", semantic_failure_is_capped_and_auditable)

    def structure_does_not_change_semantics():
        item = sample_item()
        item["dialogue_contract"]["constraints"]["line_count"] = 2
        answer = (
            "Текущее состояние: проект Vega, облако запрещено.\n\n"
            "BENCHMARK_RESULT\n"
            '{"project":"Vega","cloud_allowed":false}'
        )
        score = mod.benchmark_score("fixture", item, answer)
        assert score["semantic_score"] == 1.0
        assert score["structural_score"] < 1.0
        assert score["value"] < 1.0
        assert not any(row["dimension"] == "semantic" for row in score["critical_failures"])

    check("structural defects stay separate", structure_does_not_change_semantics)

    def public_pack_has_development_contract():
        registry = mod.benchmark_pack_registry(mod.builtin_benchmarks())
        pack = registry.get("bull_ru_dialogue")
        assert pack.status.value == "candidate"
        assert len(pack.cases) == 10
        assert {case.scorer_ref for case in pack.cases} == {"ru_dialogue_contract_v1"}
        development = _json(PACK / "development_set.json")
        assert development["schema"] == "bull-ru-dialogue-development-set"
        assert sum(len(family["variants"]) for family in development["families"]) == 10
        assert all(len(family["variants"]) >= 1 for family in development["families"])

    check("public parameterized development set", public_pack_has_development_contract)

    def gold_and_adversarial_fixtures_are_executable():
        benches = mod.load_benchmarks()
        gold = _json(PACK / "scorer_gold.json")
        audits = _json(PACK / "manual_audit.json")
        for fixture in gold["fixtures"]:
            score = mod.benchmark_score(fixture["case_id"], benches[fixture["case_id"]], fixture["answer"])
            expected = fixture["expected"]
            assert abs(score["semantic_score"] - expected["semantic_score"]) < 1e-12
            assert abs(score["structural_score"] - expected["structural_score"]) < 1e-12
            assert score["manual_review_required"] is expected["manual_review_required"]
        assert audits["cases"]
        for audit in audits["cases"]:
            score = mod.benchmark_score(audit["case_id"], benches[audit["case_id"]], audit["answer"])
            assert score["critical_failures"]
            assert score["manual_review_required"] is True
            assert score["value"] <= audit["expected_max_value"]
            observed = {row["name"] for row in score["critical_failures"]}
            assert set(audit["expected_critical_checks"]) <= observed

    check("gold and manually audited adversarial set", gold_and_adversarial_fixtures_are_executable)
    return len(checks)

