"""Agent-specific Ollama adapter using the selected Client transport."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

from .contracts import label
from .telemetry import local_resources, system_snapshot
from ..http_transport import decode_object


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Agent endpoint redirect refused", headers, fp)


class OllamaAgentBackend:
    def __init__(self, core):
        if core.active_backend() != "ollama":
            raise ValueError("Agent Benchmark MVP работает с Ollama. Выберите Ollama в настройках подключения.")
        self.core = core

    def models(self):
        return self.core.installed_models()

    def describe(self, model):
        row = next((x for x in self.models() if x["name"] == model), None)
        if not row:
            raise ValueError("Выбранная модель отсутствует на backend.")
        show = self.core.ollama_profile_snapshot(model, refresh=True)
        caps = show.get("capabilities", [])
        if caps and "tools" not in caps:
            raise ValueError("Backend не заявляет tool calling для выбранной модели.")
        running = self.core._ollama_running_model_info(model) or {}
        return {"model": label(model), "digest": row.get("digest"),
                "quantization": label(show.get("quantization", "")),
                "ollama_version": label(show.get("ollama_version", "")),
                "profile_context": show.get("parameters", {}).get("num_ctx"),
                "running_context": running.get("context_length"),
                "capabilities": caps, "backend": "ollama",
                "thinking_policy": "disabled"}

    def system(self):
        settings = self.core.load_backend_settings()
        if settings.get("ollama", {}).get("transport") == "remote_ssh":
            script = ("$o=Get-CimInstance Win32_OperatingSystem; "
                      "$c=Get-CimInstance Win32_Processor|Select-Object -First 1; "
                      "$g=Get-CimInstance Win32_VideoController; "
                      "[pscustomobject]@{os=$o.Caption;cpu=$c.Name;ram_bytes=([double]$o.TotalVisibleMemorySize*1024);"
                      "gpu=(@($g|ForEach-Object {$_.Name}) -join ', ')}|ConvertTo-Json -Compress")
            raw = self.core.remote_ps_text(script, timeout=8)
            try:
                data = json.loads(raw) if raw else {}
                return {"scope": "backend", **{k: label(data[k]) if isinstance(data.get(k), str) else data.get(k)
                        for k in ("os", "cpu", "ram_bytes", "gpu")}}
            except (ValueError, TypeError):
                return {"scope": "backend", "availability": "unavailable"}
        result = {**system_snapshot(), "scope": "client_and_backend", "gpu": None}
        executable = shutil.which("nvidia-smi")
        if executable:
            try:
                output = subprocess.run([executable, "--query-gpu=name", "--format=csv,noheader"],
                                        capture_output=True, text=True, timeout=2,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                if output.returncode == 0:
                    result["gpu"] = label(output.stdout.replace("\n", ", "))
            except (OSError, subprocess.TimeoutExpired):
                pass
        return result

    def open_stream(self, payload, timeout):
        req = urllib.request.Request(self.core.API + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        return urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout)

    def resources(self):
        local = local_resources()
        settings = self.core.load_backend_settings()
        if settings.get("ollama", {}).get("transport") != "remote_ssh":
            local["scope"] = "client_and_backend"
            return [local]
        ram = self.core.remote_ram_telemetry() or {}
        gpu = self.core.remote_gpu_telemetry() or {}
        total = ram.get("ram_total_gib")
        free = ram.get("ram_free_gib")
        return [local, {"scope": "backend",
                        "ram_total_bytes": total * 1024**3 if total is not None else None,
                        "ram_used_bytes": (total - free) * 1024**3 if total is not None and free is not None else None,
                        "vram_used_bytes": gpu["vram_used_mib"] * 1024**2 if "vram_used_mib" in gpu else None,
                        "vram_total_bytes": gpu["vram_total_mib"] * 1024**2 if "vram_total_mib" in gpu else None}]

    def request(self, messages, config, tools, timeout):
        payload = {"model": config.model, "messages": messages, "tools": tools,
                   "think": False, "stream": True, "keep_alive": "5m",
                   "options": {**config.sampling, "num_ctx": config.backend_context}}
        start = time.monotonic()
        first_token = None
        first_action = None
        calls, content, meta = [], [], {}
        size = 0
        # Timeout on reads alone is insufficient if a backend streams forever.
        # Closing the response also bounds a stalled/infinite streaming request.
        with self.open_stream(payload, timeout=timeout) as response:
            deadline_fired = threading.Event()
            def abort_read():
                deadline_fired.set()
                # Buffered HTTP reads can hold a lock while a peer trickles bytes.
                # Shutdown the transport before close so the hard deadline can
                # interrupt readline even if the idle socket timeout never fires.
                sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
                if sock is not None:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                else:
                    response.close()
            timer = threading.Timer(max(0, timeout - (time.monotonic() - start)), abort_read)
            timer.daemon = True
            timer.start()
            try:
                for raw in iter(lambda: response.readline(1024 * 1024 + 1), b""):
                    if time.monotonic() - start >= timeout:
                        raise TimeoutError("Backend timeout")
                    if len(raw) > 1024 * 1024:
                        raise ValueError("Model response too large")
                    # Count all wire bytes, including hidden reasoning/empty chunks.
                    size += len(raw)
                    if size > 2 * 1024 * 1024:
                        raise ValueError("Model stream byte budget exceeded")
                    if not raw.strip():
                        continue
                    chunk = decode_object(raw.decode("utf-8"))
                    if not isinstance(chunk, dict):
                        raise ValueError("Model invalid stream envelope")
                    if chunk.get("error"):
                        raise RuntimeError("Model error")
                    message = chunk.get("message") or {}
                    if not isinstance(message, dict):
                        raise ValueError("Model invalid message envelope")
                    now = time.monotonic() - start
                    # Observe timing only. Never retain or log hidden reasoning.
                    if first_token is None and (message.get("thinking") or message.get("content") or message.get("tool_calls")):
                        first_token = now
                    if first_action is None and (message.get("content") or message.get("tool_calls")):
                        first_action = now
                    value = message.get("content") or ""
                    if not isinstance(value, str):
                        raise ValueError("Model invalid content")
                    content.append(value)
                    chunk_calls = message.get("tool_calls") or []
                    if not isinstance(chunk_calls, list):
                        raise ValueError("Model invalid tool call envelope")
                    calls.extend(chunk_calls)
                    if len(calls) > 16:
                        raise ValueError("Model response budget exceeded")
                    if chunk.get("done") is True:
                        meta = {key: chunk.get(key) for key in (
                            "total_duration", "load_duration", "prompt_eval_count", "prompt_eval_cached_count",
                            "prompt_eval_duration", "eval_count", "eval_duration", "done_reason")}
                        break
            except (OSError, ValueError) as exc:
                if deadline_fired.is_set():
                    raise TimeoutError("Backend timeout") from exc
                raise
            finally:
                timer.cancel()
        if not meta:
            # The abort timer can wake a mocked or real socket a fraction before
            # the monotonic comparison reaches the rounded deadline.  Its event
            # is authoritative: an empty stream caused by our own shutdown is a
            # timeout, not an unrelated transport reset.
            if deadline_fired.is_set() or time.monotonic() - start >= timeout:
                raise TimeoutError("Backend timeout")
            raise ConnectionResetError("Incomplete stream")
        request_duration = time.monotonic() - start
        running = self.core._ollama_running_model_info(config.model) or {}
        return {"content": "".join(content), "tool_calls": calls,
                "meta": {**meta, "ttft_seconds": first_token,
                         "first_visible_action_seconds": first_action,
                         "request_duration_seconds": request_duration,
                         "effective_backend_context": running.get("context_length")}}
