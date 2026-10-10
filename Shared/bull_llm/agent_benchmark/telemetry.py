"""Event metrics never include prompts, reasoning, arguments or tool output."""
from __future__ import annotations

import ctypes
import json
import math
import os
import platform
import shutil
import subprocess
import threading
import time


def rate(count, duration_ns):
    if count is None or duration_ns is None or duration_ns <= 0:
        return None
    return count / (duration_ns / 1e9)


def local_resources(include_gpu=True):
    data = {"scope": "client", "ram_used_bytes": None, "ram_total_bytes": None,
            "vram_used_bytes": None, "vram_total_bytes": None}
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in
                ("total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            data.update(ram_used_bytes=status.total - status.available, ram_total_bytes=status.total)
    else:
        try:
            import psutil
            memory = psutil.virtual_memory()
            data.update(ram_used_bytes=memory.total - memory.available, ram_total_bytes=memory.total)
        except ImportError:
            pass
    executable = shutil.which("nvidia-smi") if include_gpu else None
    if executable:
        try:
            result = subprocess.run([executable, "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                                    capture_output=True, text=True, timeout=2,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            rows = [[float(v.strip()) for v in line.split(",")] for line in result.stdout.splitlines()]
            if result.returncode == 0 and rows:
                data.update(vram_used_bytes=int(sum(x[0] for x in rows) * 1024**2),
                            vram_total_bytes=int(sum(x[1] for x in rows) * 1024**2))
        except (OSError, ValueError, IndexError, OverflowError, subprocess.TimeoutExpired):
            pass
    return data


def system_snapshot():
    # No hostname, login, paths, environment dump or network identifiers.
    return {"os": platform.system(), "os_release": platform.release(),
            "architecture": platform.machine(), "cpu": platform.processor(),
            "logical_cpus": os.cpu_count(), "python": platform.python_version(),
            "scope": "client"}


class ResourceSampler:
    def __init__(self, probe=local_resources, interval=2.0):
        self.probe, self.interval = probe, interval
        self.samples = []
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.started = time.monotonic()

    def sample(self):
        try:
            rows = self.probe()
            if not isinstance(rows, list):
                rows = [rows]
            with self.lock:
                if self.stop_event.is_set():
                    return
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    safe = {}
                    for key in ("ram_used_bytes", "ram_total_bytes", "vram_used_bytes", "vram_total_bytes"):
                        value = row.get(key)
                        safe[key] = value if type(value) in (int, float) and 0 <= value <= 1e18 and math.isfinite(value) else None
                    scope = row.get("scope")
                    safe["scope"] = scope if scope in ("client", "backend", "client_and_backend") else "unknown"
                    safe["elapsed_seconds"] = time.monotonic() - self.started
                    self.samples.append(safe)
        except Exception:
            pass

    def start(self):
        def loop():
            while not self.stop_event.is_set():
                self.sample()
                if self.stop_event.wait(self.interval):
                    break
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()
        return self

    def snapshot(self):
        with self.lock:
            return [dict(row) for row in self.samples]

    def stop(self):
        # A slow/disconnected SSH probe must not delay task completion. The
        # bounded daemon probe may finish later; its result will be discarded.
        with self.lock:
            self.stop_event.set()


def aggregate(run):
    requests = run["requests"]
    tools = run["tool_calls"]
    contexts = run["contexts"]
    numeric = lambda rows, key: [x[key] for x in rows if isinstance(x.get(key), (int, float))]
    def sum_available(key):
        completed = [x for x in requests if x.get("status") == "ok"]
        vals = numeric(completed, key)
        return sum(vals) if vals and len(vals) == len(completed) else None
    prompt = sum_available("prompt_eval_count")
    generated = sum_available("eval_count")
    prompt_duration = sum_available("prompt_eval_duration")
    generation_duration = sum_available("eval_duration")
    measured = [x["tokens"] for x in contexts if x["source"] == "ollama_prompt_eval_count"]
    estimates = [x["tokens"] for x in contexts if x["source"] == "estimate"]
    ttft = numeric(requests, "ttft_seconds")
    human = len(run["interventions"])
    failed = sum(not x["success"] for x in tools)
    compactions = [x for x in run["events"] if x["type"] == "compaction"]
    memory = {}
    for scope in sorted({x["scope"] for x in run["resources"]}):
        rows = [x for x in run["resources"] if x["scope"] == scope]
        memory[scope] = {}
        for kind in ("ram", "vram"):
            key = kind + "_used_bytes"
            vals = numeric(rows, key)
            memory[scope][kind] = {"start_bytes": rows[0].get(key),
                                   "peak_bytes": max(vals) if vals else None,
                                   "finish_bytes": rows[-1].get(key),
                                   "samples": len(vals),
                                   "finish_measurement": "last_observed_sample"}
    malformed = sum(x["category"] == "malformed_tool_call" for x in run["errors"])
    verified = run.get("verification", {}).get("success") is True
    success = run["status"] == "success" and verified
    metrics = {
        "llm_metric_scope": "completed_requests_only; partial failed requests unavailable",
        "success": success, "autonomous_success": success and human == 0,
        "duration_seconds": run.get("duration_seconds", 0),
        "useful_completion_seconds": run.get("verified_at_seconds") if success else None,
        "first_useful_action_seconds": run.get("first_useful_action_seconds"),
        "prompt_tokens_processed": prompt, "generated_tokens": generated,
        "prompt_tps": rate(prompt, prompt_duration), "generation_tps": rate(generated, generation_duration),
        "mean_ttft_seconds": sum(ttft) / len(ttft) if ttft else None,
        "peak_context": max(measured) if measured else None,
        "average_context": sum(measured) / len(measured) if measured else None,
        "peak_context_estimated": max(estimates) if estimates else None,
        "startup_context_estimated": contexts[0]["tokens"] if contexts else None,
        "completion_context_estimated": estimates[-1] if estimates else None,
        "compactions": len(compactions), "compaction_seconds": sum(x["duration_seconds"] for x in compactions),
        "compaction_rate_per_10000_prompt_tokens": len(compactions) * 10000 / prompt if prompt else None,
        "tool_calls": len(tools), "tool_failures": failed,
        "tool_successes": len(tools) - failed,
        "tool_failure_rate": failed / len(tools) if tools else None,
        "repeated_tool_calls": sum(x["repeated"] for x in tools),
        "retries": sum(x["retry_count"] for x in requests),
        "malformed_tool_calls": malformed, "human_interventions": human,
        "intervention_rate_per_task": human, "resources": memory,
    }
    return metrics
