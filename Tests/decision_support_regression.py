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

    def test_unknown_vram_never_becomes_a_low_memory_recommendation(self):
        row = dict(model="unknown-memory", chat_native_score=.9, primary_eval_warm_avg=20,
                   native_task_completion_rate=1.0)
        result = build_decision_support([row])
        low_memory = next(item for item in result["profiles"] if item["id"] == "low_memory")
        self.assertIsNone(low_memory["winner"])
        self.assertTrue(any("Memory is unknown" in warning for warning in result["warnings"]))

    def test_measured_speed_top_three_is_not_the_gated_recommendation(self):
        rows = self.rows()
        result = build_decision_support(rows)
        ranked = result["rankings"]["speed"]
        self.assertEqual([item["model"] for item in ranked],
                         ["fast-bad", "balanced-model", "quality-model"])
        self.assertEqual([item["rank"] for item in ranked], [1, 2, 3])
        profile = next(item for item in result["profiles"] if item["id"] == "speed")
        self.assertNotEqual(profile["winner"], ranked[0]["model"])
        rejected = next(item for item in profile["ranking"] if item["model"] == "fast-bad")
        self.assertFalse(rejected["eligible"])
        self.assertIn("quality_below_gate", rejected["exclusions"])

    def test_rank_ties_and_zero_metrics_are_preserved(self):
        rows = [dict(model=name, chat_native_score=.8, primary_eval_warm_avg=0,
                     primary_eval_avg=55, native_task_completion_rate=1, vram_peak_mib=0)
                for name in ("b", "a", "c", "d")]
        result = build_decision_support(rows)
        self.assertEqual([row["rank"] for row in result["rankings"]["speed"]], [1]*4)
        self.assertTrue(all(row["speed"] == 0 for row in result["points"]))

    def test_warm_and_unclassified_speed_are_not_silently_mixed(self):
        rows = self.rows()
        rows[1].pop("primary_eval_warm_avg")
        rows[1]["primary_eval_avg"] = 500
        result = build_decision_support(rows)
        point = next(p for p in result["points"] if p["model"] == "balanced-model")
        self.assertEqual(point["speed_basis"], "all_load_states")
        self.assertNotIn("balanced-model", [p["model"] for p in result["rankings"]["speed"]])

    def test_unequal_coverage_does_not_produce_recommendations(self):
        rows = self.rows()
        for i, row in enumerate(rows):
            row["comparison_signature"] = str(i)
        result = build_decision_support(rows)
        self.assertFalse(result["comparable"])
        self.assertTrue(all(p["winner"] is None for p in result["profiles"]))

    def test_results_report_is_bilingual_offline_and_allowlisted(self):
        from Shared.bull_llm.results_report import render_report
        rows = self.rows()
        rows[0]["model"] = '<script>alert("label")</script>'
        rows[0]["answer"] = "PRIVATE_ANSWER_SENTINEL"
        rows[0]["endpoint"] = "SECRET_ENDPOINT_SENTINEL"
        for language in ("en", "ru"):
            report = render_report(rows, [], version="test", language=language)
            self.assertIn(f'<html lang="{language}">', report)
            self.assertIn('id="rankings"', report)
            self.assertIn('id="resources"', report)
            self.assertIn('id="tests"', report)
            self.assertIn('viewBox=', report)
            self.assertIn('#FF3C52', report)
            self.assertIn('&lt;script&gt;', report)
            self.assertNotIn('<script>', report)
            self.assertNotIn('PRIVATE_ANSWER_SENTINEL', report)
            self.assertNotIn('SECRET_ENDPOINT_SENTINEL', report)
            self.assertNotIn('https://', report)
        english = render_report(rows, [], language="en")
        self.assertNotRegex(english, r'[А-Яа-яЁё]')

    def test_resource_observations_keep_missing_unknown_and_ignore_settings_secrets(self):
        from Shared.bull_llm.results_report import report_observations
        records = [dict(execution_status="ok", identity={"benchmark": "test"},
                        config={"ctx": 8192, "token": "DO_NOT_EXPORT", "seed": 42},
                        primary={"load_state": "warm", "eval_rate": 25},
                        telemetry={"system": {"cpu_util_avg": 0, "ram_used_peak_bytes": 2**30}},
                        final={"pipeline_wall_seconds": 10})]
        result = report_observations(records)
        self.assertEqual(result["cpu_util_avg"], 0)
        self.assertEqual(result["ram_peak_gib"], 1)
        self.assertIsNone(result["gpu_util_avg"])
        self.assertEqual(result["pipeline_wall_avg"], 10)
        self.assertNotIn("DO_NOT_EXPORT", str(result))

    def test_terminal_map_and_top_three_fit_narrow_terminal(self):
        from Shared.bull_llm.results_report import terminal_decisions
        rows = self.rows()
        rows[0]["model"] = "very-long-name-" * 20
        lines = terminal_decisions(build_decision_support(rows), language="en", width=60)
        self.assertTrue(all(len(line) <= 60 for line in lines))
        self.assertIn("tok/s", "\n".join(lines))
        self.assertNotIn("execution time", "\n".join(lines))
        from Shared.bull_llm.results_report import live_progress_line
        for width in (40, 60, 80, 120):
            line = live_progress_line('long model label'*15,'FINAL',9.4,125,1800,
                                      'GPU 56% | VRAM 10.0/12.0G | 48°C | CPU 35% | RAM 22.0/64.0G',width)
            self.assertLessEqual(len(line), width)
            self.assertIn('56%',line)
            self.assertIn('35%',line)
            self.assertNotIn('/1800 tok %',line)

    def test_per_test_rolling_progress_is_not_an_overall_leaderboard(self):
        from Shared.bull_llm.results_report import rolling_test_lines
        records = []
        for seed, quality in ((42, .9), (43, .7)):
            records.append(dict(identity={"model": "a", "benchmark": "case", "backend": "ollama"},
                                config={"seed": seed}, execution_status="ok",
                                score={"native": {"value": quality}},
                                primary={"eval_rate": 20, "task_completed": True}))
        lines = rolling_test_lines(records, records[-1], language="en", width=72)
        text = "\n".join(lines)
        self.assertIn("80.0%", text)
        self.assertIn("2 runs", text)
        self.assertIn("provisional", text)
        self.assertNotIn("winner", text)


if __name__ == "__main__":
    unittest.main()
