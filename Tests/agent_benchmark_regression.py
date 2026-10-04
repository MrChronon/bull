"""Offline regression: fake model transport, real independent verifier."""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from Shared.bull_llm.agent_benchmark.contracts import (
    AgentConfig, atomic_json, classify_error, load_config, load_run, save_config)
from Shared.bull_llm.agent_benchmark.runner import TaskWorkspace, parse_call, run_benchmark
from Shared.bull_llm.agent_benchmark.tasks import INITIAL_FILES, Evaluator, RejectedCode, verify_external, verify_source
from Shared.bull_llm.agent_benchmark.telemetry import ResourceSampler, rate
from Shared.bull_llm.agent_benchmark.reports import comparison_warnings, export_csv, report_html, terminal_comparison
from Shared.bull_llm.agent_benchmark.ollama import OllamaAgentBackend

SOLUTION = '''def subtotal(items):
    return sum(item['price'] * item['quantity'] for item in items)

def discount_amount(amount, percent):
    return amount * max(0, min(100, percent)) / 100

def total(items, percent):
    amount = subtotal(items)
    return round(amount - discount_amount(amount, percent), 2)
'''


def call(name, **args):
    return {"function": {"name": name, "arguments": args}}


def response(*calls, content="", count=100):
    return {"content": content, "tool_calls": list(calls), "meta": {
        "prompt_eval_count": count, "prompt_eval_duration": 2_000_000_000,
        "eval_count": 20, "eval_duration": 1_000_000_000, "load_duration": 100_000_000,
        "total_duration": 3_100_000_000, "ttft_seconds": 0.5,
        "request_duration_seconds": 3.1}}


class FakeBackend:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.received = []

    def describe(self, model):
        return {"model": model, "digest": "fixture-digest", "ollama_version": "fixture", "backend": "ollama"}

    def resources(self):
        return {"scope": "client_and_backend", "ram_used_bytes": 1234, "ram_total_bytes": 5678,
                "vram_used_bytes": None, "vram_total_bytes": None}

    def request(self, messages, config, tools, timeout):
        self.received.append(copy.deepcopy(messages))
        item = next(self.responses, response(content="done"))
        if isinstance(item, BaseException):
            raise item
        if callable(item):
            return item()
        return item


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_agent(self, items, config=None, **kwargs):
        config = config or AgentConfig("fixture-model", max_steps=6)
        self.backend = FakeBackend(items)
        return run_benchmark(config, self.backend, self.root, **kwargs)

    def test_configuration_roundtrip(self):
        config = AgentConfig("fixture-model")
        path = self.root / "config.json"
        save_config(path, config)
        self.assertEqual(load_config(path), config)
        self.assertEqual(config.reserve, 4096)
        changed = copy.deepcopy(config)
        changed.instructions += " changed"
        self.assertNotEqual(config.public_snapshot()["instructions_sha256"], changed.public_snapshot()["instructions_sha256"])

    def test_configuration_rejects_context_sampling_and_unknown_version(self):
        for update in ({"agent_context": 32760}, {"timeout_seconds": False},
                       {"context_strategy": "invented"}, {"backend_context": 0}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                AgentConfig("m", **update).validate()
        for key, value in (("temperature", float("nan")), ("seed", 1.5), ("num_predict", -1)):
            config = AgentConfig("m")
            config.sampling[key] = value
            with self.assertRaises(ValueError):
                config.validate()
        atomic_json(self.root / "bad.json", {"schema": "local-llm-agent-config", "schema_version": 2})
        with self.assertRaises(ValueError):
            load_config(self.root / "bad.json")

    def test_initial_fixture_fails_and_golden_solution_passes(self):
        self.assertFalse(verify_source(INITIAL_FILES["pricing.py"])["success"])
        self.assertTrue(verify_source(SOLUTION)["success"])
        result = verify_external(SOLUTION)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["passed"], 12)
        self.assertEqual(verify_external(INITIAL_FILES["pricing.py"])["exit_code"], 1)

    def test_generated_code_has_no_host_capabilities(self):
        samples = ["import os", "def f():\n return open('file')", "def f():\n return ().__class__",
                   "@print\ndef f():\n return 1", "def f():\n return 2 ** 99999",
                   "def f():\n return __import__('os')", "def f():\n while True: pass"]
        for source in samples:
            self.assertFalse(verify_source(source)["success"])
        with self.assertRaises(RejectedCode):
            Evaluator("def f():\n return 'x' * 1000000000").call("f", [])
        with self.assertRaises(RejectedCode):
            Evaluator("def f():\n return f()").call("f", [])
        with self.assertRaises(RejectedCode):
            Evaluator("def f():\n return range(1000000000)").call("f", [])
        with self.assertRaises(RejectedCode):
            Evaluator("def f():\n return b'x' * 1000000000").call("f", [])

    def test_workspace_boundaries_and_test_integrity(self):
        workspace = TaskWorkspace(self.root / "workspace")
        for path in ("../outside", "C:/outside", "REQUIREMENTS.md:stream", "tests.py"):
            with self.assertRaises(ValueError):
                workspace.execute("read_file", {"path": path}, 1)
        with self.assertRaises(ValueError):
            workspace.execute("write_file", {"path": "REQUIREMENTS.md", "content": "changed"}, 1)
        with self.assertRaises(ValueError):
            workspace.execute("shell", {}, 1)

    def test_tools_validate_strict_shape(self):
        self.assertEqual(parse_call(call("list_files")), ("list_files", {}))
        good = call("read_file", path="pricing.py")
        good["function"]["arguments"] = json.dumps({"path": "pricing.py"})
        self.assertEqual(parse_call(good)[1]["path"], "pricing.py")
        for bad in ({}, call("unknown"), call("list_files", extra="x"), call("read_file", path=42)):
            with self.assertRaises(ValueError):
                parse_call(bad)

    def test_multistep_success_is_independently_verified(self):
        run, path = self.run_agent([response(call("read_file", path="REQUIREMENTS.md")),
                                   response(call("write_file", path="pricing.py", content=SOLUTION)),
                                   response(call("run_tests"))])
        self.assertEqual(run["status"], "success")
        self.assertTrue(run["metrics"]["autonomous_success"])
        self.assertEqual(run["metrics"]["tool_calls"], 3)
        self.assertEqual(run["metrics"]["prompt_tokens_processed"], 300)
        self.assertEqual(run["metrics"]["generation_tps"], 20)
        self.assertEqual(run["metrics"]["prompt_tps"], 50)
        self.assertEqual(load_run(path)["verification"]["exit_code"], 0)
        self.assertEqual(run["metrics"]["peak_context"], 100)
        self.assertEqual(run["metrics"]["resources"]["client_and_backend"]["vram"]["peak_bytes"], None)

    def test_claimed_success_cannot_pass(self):
        run, _ = self.run_agent([response(content="BUILD SUCCESSFUL")], AgentConfig("m", max_steps=1))
        self.assertFalse(run["metrics"]["success"])
        self.assertEqual(run["status"], "step_limit")
        self.assertIn("build_test_failure", [x["category"] for x in run["errors"]])

    def test_tool_loop_stops(self):
        run, _ = self.run_agent([response(call("list_files"))] * 10)
        self.assertEqual(run["status"], "agent_loop")
        self.assertEqual(run["metrics"]["repeated_tool_calls"], 3)

    def test_malformed_does_not_execute_or_persist_payload(self):
        secret = "sensitive-fixture-marker"
        run, path = self.run_agent([response({"function": {"name": "shell", "arguments": secret}})],
                                    AgentConfig("m", max_steps=1))
        self.assertEqual(run["metrics"]["tool_calls"], 0)
        self.assertEqual(run["metrics"]["malformed_tool_calls"], 1)
        self.assertNotIn(secret, path.read_text(encoding="utf-8"))

    def test_request_failure_is_durable_and_classified(self):
        run, path = self.run_agent([ConnectionResetError("ECONNRESET sensitive-marker")])
        self.assertEqual(run["status"], "backend_error")
        self.assertEqual(run["errors"][0]["category"], "connection_reset")
        self.assertNotIn("sensitive-marker", path.read_text(encoding="utf-8"))
        self.assertFalse(load_run(path)["metrics"]["success"])

    def test_manual_retry_success_is_not_autonomous(self):
        run, _ = self.run_agent([ConnectionRefusedError("ECONNREFUSED"),
                                response(call("write_file", path="pricing.py", content=SOLUTION)),
                                response(call("run_tests"))], control=lambda category: "retry")
        self.assertTrue(run["metrics"]["success"])
        self.assertFalse(run["metrics"]["autonomous_success"])
        self.assertEqual(run["metrics"]["human_interventions"], 1)
        self.assertEqual(run["metrics"]["retries"], 1)

    def test_manual_correction_is_counted_not_logged(self):
        run, path = self.run_agent([KeyboardInterrupt(), response(call("write_file", path="pricing.py", content=SOLUTION)),
                                   response(call("run_tests"))],
                                  control=lambda category: {"kind": "manual_correction", "message": "private-correction"})
        self.assertEqual(run["metrics"]["human_interventions"], 1)
        self.assertEqual(run["interventions"][0]["kind"], "manual_correction")
        self.assertNotIn("private-correction", path.read_text(encoding="utf-8"))

    def test_manual_file_edit_is_counted(self):
        def edit():
            source = next(self.root.glob("*/workspace/pricing.py"))
            source.write_text(SOLUTION, encoding="utf-8")
            return response(content="done")
        run, _ = self.run_agent([edit])
        self.assertTrue(run["metrics"]["success"])
        self.assertFalse(run["metrics"]["autonomous_success"])
        self.assertEqual(run["interventions"][0]["kind"], "manual_code_change")

    def test_rerun_is_fresh_and_preserves_parent(self):
        first, path = self.run_agent([response(call("write_file", path="pricing.py", content=SOLUTION)), response(call("run_tests"))])
        raw = path.read_bytes()
        second, _ = self.run_agent([response(content="done")], AgentConfig("m", max_steps=1), parent_run_id=first["run_id"])
        self.assertFalse(second["metrics"]["success"])
        self.assertEqual(second["parent_run_id"], first["run_id"])
        self.assertEqual(raw, path.read_bytes())

    def test_context_and_effective_runtime_are_not_conflated(self):
        run, _ = self.run_agent([response(count=30000)])
        self.assertEqual(run["status"], "context_overflow")
        item = response()
        item["meta"]["effective_backend_context"] = 4096
        run, _ = self.run_agent([item])
        self.assertEqual(run["status"], "configuration_mismatch")

    def test_compaction_is_bounded_and_preserves_rules(self):
        config = AgentConfig("m", backend_context=6000, agent_context=3500, compaction_keep_turns=1, max_steps=7)
        items = [response(call("read_file", path="pricing.py"), content="word " * 800) for _ in range(3)]
        items += [response(call("write_file", path="pricing.py", content=SOLUTION)), response(call("run_tests"))]
        run, _ = self.run_agent(items, config)
        self.assertTrue(run["metrics"]["success"], run["status"])
        self.assertGreater(run["metrics"]["compactions"], 0)
        for messages in self.backend.received:
            self.assertEqual(messages[0]["role"], "system")
            self.assertIn(config.system_prompt, messages[0]["content"])
            self.assertNotEqual(messages[2].get("role") if len(messages) > 2 else None, "tool")

    def test_secret_reasoning_and_tool_payloads_absent(self):
        config = AgentConfig("m", system_prompt="private-instruction-marker")
        secret_source = SOLUTION + "\n# private-source-marker\n"
        item = response(call("write_file", path="pricing.py", content=secret_source), content="private-answer-marker")
        item["thinking"] = "private-reasoning-marker"
        run, path = self.run_agent([item, response(call("run_tests"))], config)
        text = path.read_text(encoding="utf-8") + report_html([run])
        for marker in ("private-instruction-marker", "private-source-marker", "private-answer-marker", "private-reasoning-marker"):
            self.assertNotIn(marker, text)

    def test_compare_has_no_winner_and_escapes_export(self):
        run, _ = self.run_agent([response(content="done")], AgentConfig("m", max_steps=1))
        other = copy.deepcopy(run)
        other["task"]["version"] = "2"
        other["config"]["model"] = "<script>danger</script>"
        report = report_html([run, other])
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertTrue(any("некорректно" in x for x in comparison_warnings([run, other])))
        self.assertNotIn("universal_score", run["metrics"])
        other["config"]["model"] = "=1+1"
        path = self.root / "compare.csv"
        export_csv(path, [other])
        self.assertIn("'=1+1", path.read_text(encoding="utf-8-sig"))
        output = []
        terminal_comparison([run], output.append)
        self.assertTrue(output)

    def test_nan_unknown_metrics_and_error_categories(self):
        self.assertIsNone(rate(None, 10))
        self.assertIsNone(rate(10, 0))
        self.assertEqual(rate(2, 500000000), 4)
        cases = {"ECONNRESET": "connection_reset", "ECONNREFUSED": "connection_refused",
                 "exceed_context_size_error": "context_overflow", "unexpected end of JSON input": "malformed_tool_call"}
        for message, expected in cases.items():
            self.assertEqual(classify_error(RuntimeError(message)), expected)

    def test_streaming_adapter_metrics_options_no_reasoning(self):
        class Core:
            active_backend = staticmethod(lambda: "ollama")
            _ollama_running_model_info = staticmethod(lambda model: {"context_length": 32768})
            def post(self, payload, stream, timeout):
                self.payload = payload
                chunks = [{"message": {"thinking": "secret-reasoning"}},
                          {"message": {"tool_calls": [call("list_files")]}},
                          {"done": True, "prompt_eval_count": 10, "eval_count": 3,
                           "prompt_eval_duration": 1000000000, "eval_duration": 1000000000}]
                return io.BytesIO(b"\n".join(json.dumps(x).encode() for x in chunks))
        core = Core()
        backend = OllamaAgentBackend(core)
        backend.open_stream = lambda payload, timeout: core.post(payload, True, timeout)
        result = backend.request([], AgentConfig("m"), [], 5)
        self.assertEqual(core.payload["options"]["num_ctx"], 32768)
        self.assertEqual(core.payload["options"]["seed"], 42)
        self.assertFalse(core.payload["think"])
        self.assertNotIn("secret-reasoning", json.dumps(result))
        self.assertIsNotNone(result["meta"]["ttft_seconds"])

    def test_nan_backend_metrics_fail_closed(self):
        item = response()
        item["meta"]["eval_duration"] = float("nan")
        run, path = self.run_agent([item])
        self.assertEqual(run["status"], "model_error")
        self.assertFalse(load_run(path)["metrics"]["success"])

    def test_failed_tools_are_not_successful_actions(self):
        run, _ = self.run_agent([response(call("read_file", path="../outside")),
                                response(call("run_tests"))], AgentConfig("m", max_steps=2))
        self.assertEqual(run["metrics"]["tool_failure_rate"], 1)
        self.assertEqual(run["metrics"]["first_useful_action_seconds"], None)
        self.assertEqual(run["metrics"]["tool_failures"], 2)

    def test_timeout_and_stop_leave_records(self):
        run, path = self.run_agent([TimeoutError("backend timeout")])
        self.assertEqual(run["errors"][0]["category"], "backend_timeout")
        self.assertEqual(load_run(path)["status"], "backend_error")
        run, path = self.run_agent([KeyboardInterrupt()])
        self.assertEqual(load_run(path)["status"], "interrupted")
        self.assertFalse(run["metrics"]["success"])

    def test_compaction_failure_and_stop_policy_are_explicit(self):
        config = AgentConfig("m", backend_context=4096, agent_context=1024,
                             system_prompt="long " * 2000)
        run, _ = self.run_agent([], config)
        self.assertEqual(run["status"], "context_overflow")
        self.assertEqual(run["errors"][0]["category"], "compaction_failure")
        config.context_strategy = "stop"
        run, _ = self.run_agent([], config)
        self.assertEqual(run["errors"][0]["category"], "context_overflow")

    def test_second_verification_can_reject_first_pass(self):
        verdicts = [{"success": True, "exit_code": 0}, {"success": False, "exit_code": 1}]
        with patch("Shared.bull_llm.agent_benchmark.runner.verify_external", side_effect=verdicts):
            run, _ = self.run_agent([response(content="done")])
        self.assertEqual(run["status"], "verification_failed")
        self.assertFalse(run["metrics"]["success"])

    def test_adapter_incomplete_stream_and_redirect_fail(self):
        from Shared.bull_llm.agent_benchmark.ollama import NoRedirect
        class Core:
            active_backend = staticmethod(lambda: "ollama")
        backend = OllamaAgentBackend(Core())
        backend.open_stream = lambda payload, timeout: io.BytesIO(b'{"message":{"content":"partial"}}\n')
        with self.assertRaises(ConnectionResetError):
            backend.request([], AgentConfig("m"), [], 1)
        req = type("Request", (), {"full_url": "http://127.0.0.1:11434/api/chat"})()
        with self.assertRaises(urllib.error.HTTPError):
            NoRedirect().redirect_request(req, None, 302, "redirect", {}, "https://example.com")
        import threading
        from types import SimpleNamespace
        released = threading.Event()
        class Stalled:
            fp = SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(shutdown=lambda how: released.set())))
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def readline(self, limit):
                released.wait(1)
                return b""
        backend.open_stream = lambda payload, timeout: Stalled()
        with self.assertRaises(TimeoutError):
            backend.request([], AgentConfig("m"), [], 0.02)
        self.assertTrue(released.is_set())

    def test_model_must_exist_and_support_tools(self):
        class Core:
            active_backend = staticmethod(lambda: "ollama")
            installed_models = staticmethod(lambda: [{"name": "m"}])
            ollama_profile_snapshot = staticmethod(lambda *args, **kw: {"capabilities": ["completion"]})
        backend = OllamaAgentBackend(Core())
        with self.assertRaises(ValueError):
            backend.describe("missing")
        with self.assertRaises(ValueError):
            backend.describe("m")

    def test_local_metrics_never_probe_remote(self):
        class Core:
            active_backend = staticmethod(lambda: "ollama")
            load_backend_settings = staticmethod(lambda: {"ollama": {"transport": "local"}})
            remote_ram_telemetry = staticmethod(lambda: (_ for _ in ()).throw(AssertionError("remote")))
        with patch("Shared.bull_llm.agent_benchmark.ollama.local_resources", return_value={"scope": "client"}):
            self.assertEqual(OllamaAgentBackend(Core()).resources()[0]["scope"], "client_and_backend")

    def test_agent_menu_history_is_available_offline(self):
        from Shared.bull_llm.agent_benchmark.ui import menu
        from types import SimpleNamespace
        answers = iter(["4", "0"])
        core = SimpleNamespace(appdir=lambda: self.root, read_user_input=lambda prompt: next(answers),
                               ui_header=lambda *args: None, ui_menu_item=lambda *args: None)
        calls = []
        menu(core, lambda purpose: calls.append(purpose))
        self.assertEqual(calls, [])

    def test_agent_config_and_schema_assets_match(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("agent_config_v1.schema.json", "agent_run_v1.schema.json"):
            data = json.loads((root / "Schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(data["properties"]["schema_version"]["const"], 1)
        core_source = (root / "bull_client_v0.28.0.5.py").read_text(encoding="utf-8")
        self.assertIn("if initial_surface=='agent'", core_source)
        self.assertIn("if action=='agent'", core_source)


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AgentTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Agent Benchmark regression failed")
    return result.testsRun


if __name__ == "__main__":
    run_suite()
