import unittest

from Shared.bull_llm.decision_support import build_decision_support


class DecisionSupportTests(unittest.TestCase):
    def rows(self):
        return [
            dict(model="quality-model", chat_native_score=.92, chat_native_ci95_low=.90,
                 primary_eval_warm_avg=12, native_task_completion_rate=1.0, vram_peak_mib=10000),
            dict(model="balanced-model", chat_native_score=.88, chat_native_ci95_low=.86,
                 primary_eval_warm_avg=30, native_task_completion_rate=1.0, vram_peak_mib=8000),
            dict(model="fast-bad", chat_native_score=.45, chat_native_ci95_low=.40,
                 primary_eval_warm_avg=100, native_task_completion_rate=.5, vram_peak_mib=4000),
        ]

    def test_profiles_are_transparent_and_quality_gated(self):
        result = build_decision_support(self.rows())
        profiles = {row["id"]: row for row in result["profiles"]}
        self.assertEqual(profiles["quality"]["winner"], "quality-model")
        self.assertNotEqual(profiles["speed"]["winner"], "fast-bad")
        point = next(row for row in result["points"] if row["model"] == "fast-bad")
        self.assertFalse(point["quality_gate"])
        self.assertIn("not new benchmark quality scores", result["warnings"][0])

    def test_missing_quality_never_creates_a_fake_winner(self):
        result = build_decision_support([dict(model="runtime-only", primary_eval_warm_avg=55)])
        self.assertTrue(all(row["winner"] is None for row in result["profiles"]))

    def test_custom_weights_are_normalized(self):
        result = build_decision_support(self.rows(), {"quality": 7, "speed": 3})
        custom = next(row for row in result["profiles"] if row["id"] == "custom")
        self.assertAlmostEqual(sum(custom["weights"].values()), 1.0)
        self.assertIsNotNone(custom["winner"])

    def test_same_model_name_on_two_backends_remains_distinct(self):
        rows = [
            dict(model="same", backend="ollama", overall_native_score=.8,
                 primary_eval_warm_avg=10, native_task_completion_rate=1.0),
            dict(model="same", backend="llama_cpp", overall_native_score=.8,
                 primary_eval_warm_avg=20, native_task_completion_rate=1.0),
        ]
        result = build_decision_support(rows)
        self.assertEqual({point["model"] for point in result["points"]},
                         {"same [ollama]", "same [llama_cpp]"})

    def test_ties_remain_equal_candidates_not_name_selected_winner(self):
        rows = [
            dict(model="model_a", chat_native_score=.8, primary_eval_warm_avg=20,
                 native_task_completion_rate=1.0, vram_peak_mib=8000),
            dict(model="model_z", chat_native_score=.8, primary_eval_warm_avg=20,
                 native_task_completion_rate=1.0, vram_peak_mib=8000),
        ]
        result = build_decision_support(rows)
        quality = next(item for item in result["profiles"] if item["id"] == "quality")
        self.assertIsNone(quality["winner"])
        self.assertEqual(quality["tied_models"], ["model_a", "model_z"])
        self.assertIn("no arbitrary winner", quality["reason"])

    def test_native_mean_and_conservative_value_are_separate(self):
        row = dict(model="stable", chat_native_score=.90, chat_native_ci95_low=.82,
                   primary_eval_warm_avg=20, native_task_completion_rate=1.0)
        point = build_decision_support([row])["points"][0]
        self.assertEqual(point["quality"], .90)
        self.assertEqual(point["decision_quality"], .82)
        self.assertEqual(point["decision_quality_basis"], "ci95_low")


if __name__ == "__main__":
    unittest.main()
