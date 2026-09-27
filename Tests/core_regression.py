"""Offline contract tests for T2 BULL Core extraction."""

from __future__ import annotations

import importlib
import inspect
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class CoreContractTests(unittest.TestCase):
    def _request(self):
        from Shared.bull_llm.core import ChatMessage, GenerationRequest
        return GenerationRequest(
            request_id="req-1",
            model="fixture-model",
            messages=(ChatMessage("user", "hello"),),
            options={"temperature": 0.25, "num_ctx": 4096, "custom": [1, 2]},
            think=False,
        )

    def _ports(self, kind):
        from Shared.bull_llm.core import BackendCapabilities
        from Shared.bull_llm.runtime import BackendPorts
        return BackendPorts(
            health=lambda timeout: {"ok": timeout > 0, "backend": kind},
            list_models=lambda: [
                {"name": "z-model", "digest": "z"},
                {"name": "A-model", "digest": "a"},
            ],
            describe_model=lambda model: {"name": model, "digest": "detail", "capabilities": ["tools"]},
            generate=lambda request: (
                "answer",
                "reasoning",
                {"done_reason": "stop", "prompt_eval_count": 4, "eval_count": 2},
            ),
            cancel=lambda request_id: request_id == "req-1",
            fingerprint=lambda: f"fp-{kind}",
            capabilities=BackendCapabilities(True, tools=True, telemetry=True),
        )

    def test_generation_request_is_typed_and_preserves_options(self):
        request = self._request()
        self.assertEqual(dict(request.options), {"temperature": 0.25, "num_ctx": 4096, "custom": [1, 2]})
        self.assertEqual(request.legacy_messages(), [{"role": "user", "content": "hello"}])
        with self.assertRaises(ValueError):
            type(request)("", request.model, request.messages)

    def test_fingerprint_is_strict_and_matches_legacy(self):
        from Shared.bull_llm.core import stable_fingerprint
        from Shared.bull_llm.telemetry import stable_fingerprint as legacy
        value = {"b": [1, "тест"], "a": {"enabled": False}}
        self.assertEqual(stable_fingerprint(value), legacy(value))
        with self.assertRaises(ValueError):
            stable_fingerprint({"bad": math.nan})

    def test_ollama_and_llama_share_adapter_contract(self):
        from Shared.bull_llm.core import BackendAdapter, BackendKind
        from Shared.bull_llm.runtime import LlamaCppAdapter, OllamaAdapter
        for adapter, kind in (
            (OllamaAdapter(self._ports("ollama")), BackendKind.OLLAMA),
            (LlamaCppAdapter(self._ports("llama_cpp")), BackendKind.LLAMA_CPP),
        ):
            self.assertIsInstance(adapter, BackendAdapter)
            self.assertEqual(adapter.kind, kind)
            self.assertTrue(adapter.health()["ok"])
            self.assertEqual(len(adapter.list_models()), 2)
            self.assertEqual(adapter.describe_model("fixture-model").capabilities, ("tools",))
            self.assertEqual(adapter.generate(self._request()).content, "answer")
            self.assertTrue(adapter.cancel("req-1"))
            self.assertEqual(adapter.runtime_fingerprint(), f"fp-{kind.value}")

    def test_discovery_sorting_has_no_ui_dependency(self):
        from Shared.bull_llm.runtime import ModelDiscoveryService, OllamaAdapter
        adapter = OllamaAdapter(self._ports("ollama"))
        self.assertEqual([row.name for row in ModelDiscoveryService(adapter).discover()], ["A-model", "z-model"])
        source = inspect.getsource(importlib.import_module("Shared.bull_llm.runtime.discovery"))
        self.assertNotIn("terminal_ui", source)
        self.assertNotIn("print(", source)

    def test_inference_events_are_ordered_and_render_free(self):
        from Shared.bull_llm.core import InferenceEventKind
        from Shared.bull_llm.runtime import CollectingEventSink, OllamaAdapter
        sink = CollectingEventSink()
        OllamaAdapter(self._ports("ollama")).generate(self._request(), sink)
        self.assertEqual(
            [event.kind for event in sink.events],
            [
                InferenceEventKind.STARTED,
                InferenceEventKind.REASONING,
                InferenceEventKind.TEXT,
                InferenceEventKind.METRICS,
                InferenceEventKind.COMPLETED,
            ],
        )
        source = inspect.getsource(importlib.import_module("Shared.bull_llm.runtime"))
        self.assertNotIn("terminal_ui", source)

    def test_native_evaluation_is_transport_independent(self):
        from Shared.bull_llm.core import (
            BenchmarkCase,
            GenerationResponse,
            ScoreResult,
            VerificationResult,
        )
        from Shared.bull_llm.evaluation import evaluate_native

        class FakeScorer:
            def score(self, case, response, context):
                return ScoreResult(0.75, True, {"native": 0.75})

        class FakeVerifier:
            def verify(self, case, response):
                return VerificationResult(True)

        result = evaluate_native(
            BenchmarkCase("case", "prompt"),
            GenerationResponse("req", "model", "native"),
            FakeScorer(),
            FakeVerifier(),
        )
        self.assertEqual(result.native_response.content, "native")
        self.assertEqual(result.native_score.score, 0.75)
        source = inspect.getsource(importlib.import_module("Shared.bull_llm.evaluation.service"))
        self.assertNotIn("runtime", source)
        self.assertNotIn("urllib", source)

    def test_report_serializes_precomputed_summary_without_scorer(self):
        from Shared.bull_llm.core import AtomicArtifactStore
        from Shared.bull_llm.reports import JsonReportRenderer
        with tempfile.TemporaryDirectory() as tmp:
            store = AtomicArtifactStore(tmp)
            path = JsonReportRenderer().render({"native_score": 0.42}, store, "report.json")
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(document["summary"], {"native_score": 0.42})
            self.assertNotIn("Scorer", inspect.getsource(importlib.import_module("Shared.bull_llm.reports")))

    def test_artifact_store_is_bounded_atomic_and_rooted(self):
        from Shared.bull_llm.core import ArtifactClassification, AtomicArtifactStore
        with tempfile.TemporaryDirectory() as tmp:
            store = AtomicArtifactStore(tmp, max_json_bytes=256)
            path = store.write_json("nested/result.json", {"ok": True}, ArtifactClassification.PRIVATE)
            self.assertEqual(store.read_json("nested/result.json"), {"ok": True})
            self.assertEqual(len(store.sha256("nested/result.json")), 64)
            self.assertEqual(path.with_suffix(".json.classification").read_text(encoding="ascii").strip(), "private")
            self.assertEqual(list(Path(tmp).rglob("*.tmp")), [])
            with self.assertRaises(ValueError):
                store.write_json("../escape.json", {}, ArtifactClassification.PRIVATE)
            with self.assertRaises(ValueError):
                store.write_json("nan.json", {"x": math.nan}, ArtifactClassification.PRIVATE)
            with self.assertRaises(ValueError):
                store.write_json("large.json", {"x": "a" * 300}, ArtifactClassification.PRIVATE)

    def test_legacy_adapter_never_switches_active_backend(self):
        from Shared.bull_llm.core import BackendKind
        from Shared.bull_llm.runtime import legacy_core_adapter

        class FakeCore:
            ACTIVE_BACKEND = "ollama"
            def version(self, timeout): return {"version": "fixture"}
            def _ollama_installed_models(self): return [{"name": "m"}]
            def _ollama_model_show(self, model): return {"name": model}
            def backend_runtime_fingerprint(self): return "runtime-fp"
            def stream_chat(self, *args, **kwargs): return ("ok", "", {"done_reason": "stop"})

        fake = FakeCore()
        adapter = legacy_core_adapter(fake, BackendKind.OLLAMA)
        self.assertEqual(adapter.runtime_fingerprint(), "runtime-fp")
        self.assertEqual(fake.ACTIVE_BACKEND, "ollama")
        fake.ACTIVE_BACKEND = "llama_cpp"
        with self.assertRaises(RuntimeError):
            adapter.runtime_fingerprint()
        self.assertEqual(fake.ACTIVE_BACKEND, "llama_cpp")

    def test_public_protocols_are_runtime_checkable(self):
        from Shared.bull_llm.core import BackendAdapter, ReportRenderer, Scorer
        self.assertTrue(getattr(BackendAdapter, "_is_runtime_protocol", False))
        self.assertTrue(getattr(Scorer, "_is_runtime_protocol", False))
        self.assertTrue(getattr(ReportRenderer, "_is_runtime_protocol", False))

    def test_dependency_boundaries_are_enforced_in_source(self):
        checks = {
            "Shared.bull_llm.core.contracts": ("Apps", "terminal_ui", "urllib"),
            "Shared.bull_llm.evaluation.service": ("runtime", "urllib", "terminal_ui"),
            "Shared.bull_llm.reports": ("Scorer", "stream_chat", "urllib"),
            "Shared.bull_llm.runtime.adapters": ("terminal_ui", "Apps", "evaluation"),
        }
        for module_name, forbidden in checks.items():
            source = inspect.getsource(importlib.import_module(module_name))
            for token in forbidden:
                self.assertNotIn(token, source, f"{module_name} depends on {token}")


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CoreContractTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("BULL Core regression failed")
    return result.testsRun


if __name__ == "__main__":
    run_suite()
