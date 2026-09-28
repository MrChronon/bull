"""Offline fault injection for the v0.25.0.0 audit. No real model/server needed."""
from __future__ import annotations

import copy
import contextlib
import io
import json
import tempfile
import subprocess
import os
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class HardeningTests(unittest.TestCase):
    core = None

    def test_http_redirect_never_reaches_second_endpoint(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from Shared.bull_llm.http_transport import NoRedirect, open_response
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/must-not-be-reached")
                self.end_headers()
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.01), daemon=True)
        thread.start()
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with self.assertRaises(urllib.error.HTTPError) as caught:
                open_response(opener, f"http://127.0.0.1:{server.server_port}/start", 1)
            caught.exception.close()
            self.assertEqual(seen, ["/start"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(1)

    def test_http_limits_json_lines_and_cumulative_stream(self):
        from Shared.bull_llm import http_transport as net
        with patch.object(net, "MAX_JSON_BYTES", 16):
            with net.BoundedResponse(io.BytesIO(b"x" * 17), time.monotonic() + 1) as response:
                with self.assertRaises(ValueError):
                    response.read()
        with patch.object(net, "MAX_LINE_BYTES", 8):
            with net.BoundedResponse(io.BytesIO(b"x" * 9), time.monotonic() + 1) as response:
                with self.assertRaises(ValueError):
                    list(response)
        with net.BoundedResponse(io.BytesIO(b"x\n" * 9), time.monotonic() + 1, max_bytes=16) as response:
            with self.assertRaises(ValueError):
                list(response)

    def test_http_body_deadline_interrupts_stalled_socket(self):
        from Shared.bull_llm.http_transport import BoundedResponse
        released = threading.Event()
        response = SimpleNamespace(
            fp=SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(shutdown=lambda how: released.set()))),
            readline=lambda n: (released.wait(1) and b""), close=lambda: None)
        started = time.monotonic()
        with BoundedResponse(response, started + .04) as guarded:
            with self.assertRaises(TimeoutError):
                list(guarded)
        self.assertLess(time.monotonic() - started, .4)
        self.assertTrue(released.is_set())

    def test_http_json_rejects_wrong_envelope_and_nonfinite(self):
        from Shared.bull_llm.http_transport import json_object
        for raw in (b"[]", b"null", b'{"n":NaN}', b'{"n":1e309}'):
            with self.assertRaises(ValueError):
                json_object(io.BytesIO(raw))

    def test_stream_display_filters_terminal_controls_but_not_scored_text(self):
        content = "hello\x1b]52;c;fixture\x07world\r\x9b2J\n"
        payload = json.dumps({"message": {"content": content}, "done": True}).encode() + b"\n"
        out = io.StringIO()
        cfg = {"model": "fixture", "think": False, "num_predict": 32}
        with patch.object(self.core, "post", return_value=io.BytesIO(payload)), contextlib.redirect_stdout(out):
            answer, _, _ = self.core._ollama_stream_chat([], cfg, silent=False)
        self.assertEqual(answer, content)
        for control in ("\x1b", "\x07", "\x9b", "\r"):
            self.assertNotIn(control, out.getvalue())

    def test_telemetry_local_never_selects_ssh(self):
        with patch.object(self.core, "ACTIVE_BACKEND", "ollama"), patch.object(
                self.core, "load_backend_settings", return_value={"ollama": {"transport": "local"}}), patch.object(
                self.core, "OLLAMA_API", "http://127.0.0.1:11434"), patch.object(
                self.core, "resolve_remote_endpoint", side_effect=AssertionError("unexpected SSH")), patch.object(
                self.core.shutil, "which", return_value="nvidia-smi"):
            self.assertEqual(self.core._gpu_command(["--query-gpu=name"]), ["nvidia-smi", "--query-gpu=name"])

    def test_telemetry_external_does_not_claim_local_hardware(self):
        with patch.object(self.core, "ACTIVE_BACKEND", "llama_cpp"), patch.object(
                self.core, "load_backend_settings", return_value={"llama_cpp": {"transport": "external"}}):
            self.assertIsNone(self.core._gpu_command([]))
            self.assertIsNone(self.core.remote_ram_telemetry())

    def test_server_installer_whole_workflow_has_whatif_gate(self):
        path = Path(self.core.__file__).parent / "Server/Install-BULL-Node.ps1"
        script = path.read_text(encoding="utf-8-sig")
        gate = script.index("if (-not $PSCmdlet.ShouldProcess('BULL node'")
        self.assertLess(gate, script.index("\nAssert-Administrator\n"))
        self.assertLess(gate, script.index("    Ensure-WindowsCapability 'OpenSSH.Server"))
        self.assertIn("'*S-1-5-32-544:F'", script)

    @unittest.skipUnless(os.name == "nt", "Windows release gate")
    def test_public_gate_fails_closed_on_unscanned_files_and_pkcs8(self):
        root = Path(self.core.__file__).parent
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / "backend_settings.json").write_bytes((root / "backend_settings.json").read_bytes())
            (target / "unknown.dat").write_bytes(b"fixture")
            (target / "oversized.txt").write_bytes(b"x" * (8 * 1024 * 1024 + 1))
            (target / "secret.txt").write_text("-----BEGIN " + "PRIVATE KEY-----", encoding="ascii")
            child = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(root / "Test-Public-Release.ps1"),
                                    "-Root", str(target)], capture_output=True, timeout=20)
            self.assertNotEqual(child.returncode, 0)
            for marker in (b"unknown.dat", b"oversized.txt", b"private key material"):
                self.assertIn(marker, child.stdout + child.stderr)

    def test_atomic_writers_use_independent_temporary_files(self):
        from Shared.bull_llm.storage import atomic_text
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "shared.json"
            with atomic_text(path) as first:
                first.write('{"writer":1}')
                with atomic_text(path) as second:
                    second.write('{"writer":2}')
                self.assertEqual(json.loads(path.read_text()), {"writer": 2})
            self.assertEqual(json.loads(path.read_text()), {"writer": 1})
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_attachment_limit_applies_before_reading_whole_file(self):
        stream = io.BytesIO(b"x" * 2_000_001)
        with patch("pathlib.Path.is_file", return_value=True), patch("pathlib.Path.open", return_value=stream), patch(
                "pathlib.Path.read_bytes", side_effect=AssertionError("unbounded read")):
            with self.assertRaises(ValueError):
                self.core.read_text_attachment("fixture.txt")

    def test_agent_json_rejects_exponent_overflow_and_corrupt_context(self):
        from Shared.bull_llm.agent_benchmark.contracts import load_json, load_run, atomic_json
        from Tests.agent_benchmark_regression import FakeBackend, response
        from Shared.bull_llm.agent_benchmark.runner import run_benchmark
        from Shared.bull_llm.agent_benchmark.contracts import AgentConfig
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"x":1e309}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_json(path)
            run, _ = run_benchmark(AgentConfig("fixture", max_steps=1), FakeBackend([response(content="done")]), tmp)
            run["contexts"][0]["tokens"] = "not a number"
            atomic_json(path, run)
            with self.assertRaises(ValueError):
                load_run(path)

    def test_ollama_eof_does_not_complete_run(self):
        cfg = {"model": "fixture", "think": False, "num_predict": 32}
        with patch.object(self.core, "post", return_value=io.BytesIO(
                b'{"message":{"content":"partial"},"done":false}\n')):
            with self.assertRaises(ConnectionResetError):
                self.core._ollama_stream_chat([], cfg, silent=True)

    def test_ollama_error_does_not_complete_run(self):
        cfg = {"model": "fixture", "think": False, "num_predict": 32}
        with patch.object(self.core, "post", return_value=io.BytesIO(b'{"error":"fixture failure"}\n')):
            with self.assertRaises(RuntimeError):
                self.core._ollama_stream_chat([], cfg, silent=True)

    def test_ollama_done_stops_without_waiting_for_eof(self):
        cfg = {"model": "fixture", "think": False, "num_predict": 32}
        with patch.object(self.core, "post", return_value=io.BytesIO(
                b'{"message":{"content":"ok"},"done":true}\nNOT JSON\n')):
            answer, _, meta = self.core._ollama_stream_chat([], cfg, silent=True)
        self.assertEqual(answer, "ok")
        self.assertTrue(meta["done"])

    def test_llama_eof_without_finish_is_interruption(self):
        cfg = {"model": "fixture", "think": False, "num_predict": 32,
               "temperature": .2, "top_p": .9, "top_k": 40, "min_p": 0, "seed": 42}
        with patch.object(self.core, "ensure_llama_runtime"), patch.object(
                self.core, "llama_api_post", return_value=io.BytesIO(
                    b'data: {"choices":[{"delta":{"content":"partial"}}]}\n')):
            with self.assertRaises(ConnectionResetError):
                self.core._llama_stream_chat([], cfg, silent=True)

    def test_configuration_edit_is_transactional(self):
        from Shared.bull_llm.agent_benchmark.contracts import AgentConfig
        from Shared.bull_llm.agent_benchmark.ui import configure
        config = AgentConfig("old")
        original = copy.deepcopy(config)
        answers = iter(["1", "changed", "invalid number"])
        ui = SimpleNamespace(ui_header=lambda *a: None, show_models=lambda *a, **k: None,
                             read_user_input=lambda p: next(answers), resolve_model_choice=lambda *a: ("new", None))
        backend = SimpleNamespace(models=lambda: [{"name": "new"}], describe=lambda m: {})
        with self.assertRaises(ValueError):
            configure(ui, backend, config)
        self.assertEqual(config, original)

    def test_enter_preserves_custom_configuration(self):
        from Shared.bull_llm.agent_benchmark.contracts import AgentConfig
        from Shared.bull_llm.agent_benchmark.ui import configure
        config = AgentConfig("old", context_strategy="stop", agent_context=30000)
        original = copy.deepcopy(config)
        answers = iter(["1"] + [""] * 10)
        ui = SimpleNamespace(ui_header=lambda *a: None, show_models=lambda *a, **k: None,
                             read_user_input=lambda p: next(answers), resolve_model_choice=lambda *a: ("old", None))
        backend = SimpleNamespace(models=lambda: [{"name": "old"}], describe=lambda m: {})
        self.assertEqual(configure(ui, backend, config), original)

    def test_sampler_start_stop_never_waits_for_probe(self):
        from Shared.bull_llm.agent_benchmark.telemetry import ResourceSampler
        entered, release = threading.Event(), threading.Event()
        calls = []
        def probe():
            calls.append(1)
            entered.set()
            release.wait(1)
            return {"scope": "backend", "ram_used_bytes": 1}
        sampler = ResourceSampler(probe, interval=0.01)
        started = time.monotonic()
        try:
            sampler.start()
            self.assertLess(time.monotonic() - started, 0.4)
            self.assertTrue(entered.wait(1))
            started = time.monotonic()
            sampler.stop()
            self.assertLess(time.monotonic() - started, 0.4)
        finally:
            release.set()
            if sampler.thread:
                sampler.thread.join(2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sampler.snapshot(), [])  # late samples cannot alter a finished run

    def test_sampler_rejects_nonfinite_and_private_fields(self):
        from Shared.bull_llm.agent_benchmark.telemetry import ResourceSampler
        sampler = ResourceSampler(lambda: [{"scope": "backend", "ram_used_bytes": float("nan"),
                                           "vram_total_bytes": -1, "password": "fixture"}])
        sampler.sample()
        row = sampler.snapshot()[0]
        self.assertIsNone(row["ram_used_bytes"])
        self.assertIsNone(row["vram_total_bytes"])
        self.assertNotIn("password", row)
        json.dumps(row, allow_nan=False)

    def test_invalid_agent_json_has_controlled_error(self):
        from Shared.bull_llm.agent_benchmark.contracts import load_config, load_run
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for text in ("[]", "null", '{"schema":"local-llm-agent-run","schema_version":1,"metrics":{},"config":{}}'):
                path.write_text(text, encoding="utf-8")
                for reader in (load_config, load_run):
                    with self.subTest(reader=reader.__name__, text=text), self.assertRaises(ValueError):
                        reader(path)

    def test_atomic_save_keeps_previous_file_on_replace_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            path.write_text('{"old":true}', encoding="utf-8")
            with patch("os.replace", side_effect=PermissionError("fixture")):
                with self.assertRaises(PermissionError):
                    self.core._atomic_json(path, {"new": True})
            self.assertEqual(json.loads(path.read_text()), {"old": True})
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_cache_identity_includes_shared_apps_and_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("Shared", "Apps", "Tests/Fixtures"):
                (root / folder).mkdir(parents=True)
            script = root / "Tests/regression.py"
            script.write_text("pass", encoding="utf-8")
            with patch.object(self.core, "appdir", return_value=root):
                previous = self.core._startup_regression_identity(script)
                for name in ("Shared/net.py", "Apps/start.py", "Tests/Fixtures/gold.json"):
                    path = root / name
                    path.write_text("fixture", encoding="utf-8")
                    current = self.core._startup_regression_identity(script)
                    self.assertNotEqual(previous, current, name)
                    previous = current


def run_suite(core):
    HardeningTests.core = core
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(HardeningTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Hardening regression failed")
    return result.testsRun


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from Apps._bootstrap import load_compat_core
    run_suite(load_compat_core())
