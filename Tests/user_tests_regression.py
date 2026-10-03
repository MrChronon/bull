import tempfile
import unittest
from pathlib import Path

from Shared.bull_llm.user_tests import (
    UserTestError,
    load_user_tests,
    parse_user_test_yaml,
    score_user_test,
    score_user_test_v1,
    validate_user_test,
)


STRUCTURED = """schema: bull-user-test
version: 1
id: beam_check
title: Beam calculation
description: Synthetic engineering fixture
language: en
prompt: |
  Calculate the synthetic beam fixture.
  Return the declared JSON contract.
criteria:
  - id: mentions_method
    type: contains_all
    description: Explains the method
    weight: 20
    values:
      - bending moment
  - id: stress_value
    type: terminal_json_number
    description: Correct stress with tolerance
    weight: 60
    path: result.stress_mpa
    expected: 125
    tolerance_abs: 0.5
    critical: true
  - id: no_fake_claim
    type: forbidden_any
    description: Does not claim certification
    weight: 20
    values:
      - certified design
manual_review:
  - Check that assumptions match the actual project before use.
"""


class UserTestsRegression(unittest.TestCase):
    def test_yaml_subset_loads_and_generates_explicit_contract(self):
        document = validate_user_test(parse_user_test_yaml(STRUCTURED), "beam.yaml")
        self.assertEqual(document["id"], "beam_check")
        self.assertEqual(sum(row["weight"] for row in document["criteria"]), 100)
        self.assertIn("result.stress_mpa", document["result_instruction"])
        self.assertEqual(document["source_name"], "beam.yaml")

    def test_structured_scorer_is_deterministic_and_critical(self):
        document = validate_user_test(parse_user_test_yaml(STRUCTURED))
        good = "The bending moment gives the result.\nBENCHMARK_RESULT\n{\"result\":{\"stress_mpa\":125.2}}"
        score = score_user_test(good, document)
        self.assertEqual(score["value"], 1.0)
        self.assertTrue(score["manual_review_required"])
        bad = "The bending moment gives the result.\nBENCHMARK_RESULT\n{\"result\":{\"stress_mpa\":190}}"
        score = score_user_test(bad, document)
        self.assertLessEqual(score["value"], .59)
        self.assertEqual(score["critical_failures"][0]["criterion"], "stress_value")

    def test_v2_keeps_boolean_types_and_terminal_json_contract_strict(self):
        document = validate_user_test(parse_user_test_yaml(STRUCTURED.replace(
            "path: result.stress_mpa\n    expected: 125\n    tolerance_abs: 0.5",
            "path: result.ok\n    expected: true",
        ).replace("type: terminal_json_number", "type: terminal_json_equals")))
        numeric_boolean = "bending moment\nBENCHMARK_RESULT\n{\"result\":{\"ok\":1}}"
        self.assertLess(score_user_test(numeric_boolean, document)["value"], 1.0)
        numeric_document = validate_user_test(parse_user_test_yaml(STRUCTURED))
        numeric_score = score_user_test(
            "bending moment\nBENCHMARK_RESULT\n{\"result\":{\"stress_mpa\":true}}", numeric_document
        )
        self.assertLess(numeric_score["value"], 1.0)
        trailing = "bending moment\nBENCHMARK_RESULT\n{\"result\":{\"ok\":true}}\nextra"
        strict = score_user_test(trailing, document)
        self.assertEqual(strict["parse_error"], "trailing_text_after_terminal_json")
        self.assertLess(strict["value"], 1.0)
        # Existing v1 artifacts retain their historical field-check behavior
        # rather than being silently rescored as v2.
        self.assertEqual(score_user_test_v1(trailing, document)["method"], "user_contract_v1")

    def test_v2_one_word_literal_does_not_match_inside_another_word(self):
        document = validate_user_test(parse_user_test_yaml(STRUCTURED.replace(
            "type: contains_all", "type: forbidden_any", 1
        ).replace("- bending moment", "- ты", 1)))
        score = score_user_test("Документы готовы.\nBENCHMARK_RESULT\n{\"result\":{\"stress_mpa\":125}}", document)
        check = next(item for item in score["checks"] if item["name"] == "mentions_method")
        self.assertTrue(check["ok"])

    def test_plain_text_is_runtime_only_and_invalid_yaml_is_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "my task.txt").write_text("Explain this synthetic task.", encoding="utf-8")
            (root / "broken.yaml").write_text("schema: unsafe\n", encoding="utf-8")
            tests, findings = load_user_tests(root)
        self.assertEqual(tests["user_my_task"]["score_type"], "none")
        self.assertTrue(tests["user_my_task"]["manual_review_required"])
        self.assertEqual(findings[0]["file"], "broken.yaml")

    def test_weights_and_yaml_features_fail_closed(self):
        invalid = STRUCTURED.replace("weight: 20", "weight: 10", 1)
        with self.assertRaisesRegex(UserTestError, "sum to exactly 100"):
            validate_user_test(parse_user_test_yaml(invalid))
        with self.assertRaises(UserTestError):
            parse_user_test_yaml("schema: &anchor bull-user-test\n  child: value")


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(UserTestsRegression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("BULL user tests regression failed")
    return result.testsRun


if __name__ == "__main__":
    run_suite()
