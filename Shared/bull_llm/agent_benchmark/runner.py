"""Bounded agent loop, independent verification, and durable diagnostic records."""
from __future__ import annotations

import json
import math
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import AGENT_VERSION, RUN_SCHEMA, SCHEMA_VERSION
from .contracts import atomic_json, classify_error, fingerprint, save_config
from .tasks import INITIAL_FILES, PROMPT, TASK_ID, TASK_VERSION, verify_external
from .telemetry import ResourceSampler, aggregate, rate, system_snapshot


def tool(name, description, properties):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": list(properties), "additionalProperties": False}}}


TOOLS = [tool("list_files", "List the task's available files", {}),
         tool("read_file", "Read a task file", {"path": {"type": "string"}}),
         tool("write_file", "Replace pricing.py with complete source", {
             "path": {"type": "string"}, "content": {"type": "string"}}),
         tool("run_tests", "Run the independent task verifier", {})]
TOOL_PROPERTIES = {x["function"]["name"]: x["function"]["parameters"]["properties"] for x in TOOLS}


def estimate_tokens(messages):
    # Explicit estimate, not a claim of tokenizer precision; calibrated upwards
    # using observed prompt_eval_count at each response.
    return math.ceil(len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) / 3)


def parse_call(value):
    if not isinstance(value, dict) or not isinstance(value.get("function"), dict):
        raise ValueError("tool envelope")
    fn = value["function"]
    name, args = fn.get("name"), fn.get("arguments")
    if name not in TOOL_PROPERTIES:
        raise ValueError("unknown tool")
    if isinstance(args, str):
        args = json.loads(args)
    if not isinstance(args, dict) or set(args) != set(TOOL_PROPERTIES[name]):
        raise ValueError("tool arguments")
    if any(not isinstance(v, str) for v in args.values()):
        raise ValueError("tool argument type")
    if len(json.dumps(args).encode("utf-8")) > 65536:
        raise ValueError("tool argument budget")
    return name, args


class TaskWorkspace:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        for name, content in INITIAL_FILES.items():
            (self.root / name).write_text(content, encoding="utf-8")

    def read(self, name):
        if name not in INITIAL_FILES:
            raise ValueError("file_not_allowed")
        path = self.root / name
        if path.is_symlink() or path.resolve().parent != self.root.resolve() or path.stat().st_size > 32768:
            raise ValueError("file_boundary")
        # Includes Windows junction/reparse targets in the resolved-boundary check.
        return path.read_text(encoding="utf-8")

    def snapshot(self):
        return {name: fingerprint(self.read(name)) for name in INITIAL_FILES}

    def execute(self, name, args, timeout):
        if name == "list_files":
            return {"files": list(INITIAL_FILES)}, True
        if name == "read_file":
            return {"content": self.read(args["path"])}, True
        if name == "write_file":
            if args["path"] != "pricing.py" or len(args["content"].encode("utf-8")) > 32768:
                raise ValueError("write_not_allowed")
            self.read("pricing.py")
            # Atomic replacement also avoids writing through a hard-linked file.
            dest = self.root / "pricing.py"
            temp = self.root / (uuid.uuid4().hex + ".tmp")
            try:
                with temp.open("x", encoding="utf-8") as stream:
                    stream.write(args["content"])
                temp.replace(dest)
            finally:
                if temp.exists():
                    temp.unlink()
            return {"written": "pricing.py", "bytes": len(args["content"].encode("utf-8"))}, True
        if name == "run_tests":
            verdict = verify_external(self.read("pricing.py"), timeout=min(5, timeout))
            return verdict, verdict["success"]
        raise ValueError("tool_not_allowed")


def run_benchmark(config, backend, storage, progress=None, control=None,
                  parent_run_id=None, initial_intervention=None, sampler=None):
    """One attempt. Reruns always start from the immutable fixture, never dirty state.

    control(error_category) returns stop/retry. Every retry is a human intervention.
    Raw request/response content exists only in memory and private workspace.
    """
    config.validate()
    identity = backend.describe(config.model)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:12]
    root = Path(storage) / run_id
    root.mkdir(parents=True, exist_ok=False)
    workspace = TaskWorkspace(root / "workspace")
    save_config(root / "configuration.private.json", config)
    started = time.monotonic()
    sampler = sampler or ResourceSampler(backend.resources, interval=5)
    run = {"schema": RUN_SCHEMA, "schema_version": SCHEMA_VERSION,
           "run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(),
           "agent_version": AGENT_VERSION, "parent_run_id": parent_run_id,
           "status": "running", "config": config.public_snapshot(), "model": identity,
           "task": {"id": TASK_ID, "version": TASK_VERSION,
                    "initial_state_sha256": fingerprint(INITIAL_FILES),
                    "prompt_sha256": fingerprint(PROMPT), "verifier_version": "1"},
           "system": system_snapshot(), "requests": [], "tool_calls": [],
           "contexts": [], "events": [], "errors": [], "interventions": [],
           "resources": [], "verification": {"success": False, "status": "not_run"},
           "metrics": {}, "context_measurement": "request counts from Ollama; other points estimated",
           "privacy": {"reasoning_saved": False, "tool_payloads_saved": False,
                       "instructions_saved_in_result": False}}
    try:
        run["backend_system"] = backend.system() if hasattr(backend, "system") else {"availability": "unavailable"}
    except Exception:
        run["backend_system"] = {"availability": "unavailable"}
    def elapsed():
        return time.monotonic() - started

    def remaining():
        return max(0.0, config.timeout_seconds - elapsed())

    def event(event_type, **fields):
        run["events"].append({"type": event_type, "elapsed_seconds": elapsed(), **fields})

    def error(category):
        run["errors"].append({"category": category, "elapsed_seconds": elapsed()})
        event("error", category=category)

    def intervention(kind):
        run["interventions"].append({"kind": kind, "elapsed_seconds": elapsed()})
        event("human_intervention", kind=kind)

    def save():
        run["duration_seconds"] = elapsed()
        run["resources"] = sampler.snapshot()
        run["metrics"] = aggregate(run)
        atomic_json(root / "result.json", run)

    def context(phase, count, source="estimate", step=0):
        run["contexts"].append({"phase": phase, "tokens": count, "source": source,
                                "step": step, "elapsed_seconds": elapsed()})

    rules = config.rules()
    system = "\n\n".join(rules.values())
    pinned = [{"role": "system", "content": system}, {"role": "user", "content": PROMPT}]
    messages = list(pinned)
    tool_tokens = estimate_tokens(TOOLS)
    calibration = 1.0
    def estimate(msgs):
        return math.ceil((estimate_tokens(msgs) + tool_tokens) * calibration)
    run["rules_footprint"] = {k + "_tokens_estimated": estimate_tokens(v) for k, v in rules.items()}
    run["rules_footprint"].update(tool_definitions_tokens_estimated=tool_tokens,
                                  total_instruction_tokens_estimated=estimate_tokens(system) + tool_tokens,
                                  instructions_sha256=fingerprint(rules))
    event("session_started")
    context("startup", tool_tokens)
    context("instructions_loaded", estimate_tokens(system) + tool_tokens)
    if initial_intervention:
        intervention(initial_intervention)
    known_files = workspace.snapshot()
    seen_calls = {}
    last_signature, consecutive = None, 0
    retry_pending = 0
    try:
        sampler.start()
        save()
        for step in range(1, config.max_steps + 1):
            if remaining() <= 0:
                run["status"] = "timeout"
                break
            current_files = workspace.snapshot()
            if current_files != known_files:
                intervention("manual_code_change")
                messages.append({"role": "user", "content": "A human changed task files. Read them again before continuing."})
                known_files = current_files
            before = estimate(messages)
            if before > config.agent_context:
                if config.context_strategy == "stop":
                    error("context_overflow")
                    run["status"] = "context_overflow"
                    break
                compaction_start = time.monotonic()
                # Retain complete assistant/tool groups; never orphan tool results.
                groups = [i for i, msg in enumerate(messages) if i >= 2 and msg["role"] == "assistant"]
                keep = messages[groups[-config.compaction_keep_turns]:] if groups else []
                messages = list(pinned) + [{"role": "user", "content":
                    "Older work history was compacted. Current files remain on disk. Read files and run_tests to recover state."}] + keep
                after = estimate(messages)
                if after >= before or after > config.agent_context:
                    error("compaction_failure")
                    run["status"] = "context_overflow"
                    break
                event("compaction", before_tokens=before, after_tokens=after,
                      tokens_removed=before - after, measurement="estimate",
                      duration_seconds=time.monotonic() - compaction_start)
                context("after_compaction", after, step=step)
            context("before_request", estimate(messages), step=step)
            event("request_started", step=step)
            if progress:
                progress("request", step, run)
            save()
            request_started = elapsed()
            try:
                response = backend.request(messages, config, TOOLS,
                                           min(config.request_timeout_seconds, remaining()))
            except (Exception, KeyboardInterrupt) as exc:
                category = "interrupted" if isinstance(exc, KeyboardInterrupt) else classify_error(exc)
                error(category)
                run["requests"].append({"step": step, "status": category,
                                        "retry_count": retry_pending,
                                        "request_duration_seconds": elapsed() - request_started})
                save()
                decision = control(category) if control and remaining() > 0 else "stop"
                if decision == "retry":
                    intervention("manual_retry" if category == "interrupted" else "manual_infrastructure_recovery")
                    retry_pending = 1
                    save()
                    continue
                if isinstance(decision, dict) and decision.get("kind") in ("manual_correction", "user_clarification"):
                    intervention(decision["kind"])
                    messages.append({"role": "user", "content": str(decision.get("message", ""))[:16000]})
                    retry_pending = 1
                    save()
                    continue
                run["status"] = "interrupted" if category == "interrupted" else "backend_error"
                break
            meta = response.get("meta", {})
            allowed = ("total_duration", "load_duration", "prompt_eval_count", "prompt_eval_cached_count",
                       "prompt_eval_duration", "eval_count", "eval_duration", "ttft_seconds",
                       "request_duration_seconds", "first_visible_action_seconds", "effective_backend_context")
            request = {k: meta.get(k) for k in allowed}
            if any(value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0)
                   for value in request.values()):
                error("model_error")
                run["status"] = "model_error"
                break
            request.update(step=step, status="ok", retry_count=retry_pending,
                           start_seconds=request_started, end_seconds=elapsed())
            retry_pending = 0
            request["prompt_tps"] = rate(request.get("prompt_eval_count"), request.get("prompt_eval_duration"))
            request["generation_tps"] = rate(request.get("eval_count"), request.get("eval_duration"))
            run["requests"].append(request)
            count = meta.get("prompt_eval_count")
            if isinstance(count, int) and count >= 0:
                context("request_processed", count, "ollama_prompt_eval_count", step)
                calibration = max(calibration, count / max(1, estimate_tokens(messages) + tool_tokens))
                if count > config.agent_context:
                    event("context_limit_exceeded", measured_tokens=count, agent_limit=config.agent_context)
                    error("context_overflow")
                    run["status"] = "context_overflow"
                    break
            effective = meta.get("effective_backend_context")
            if effective is not None and effective != config.backend_context:
                event("runtime_context_mismatch", requested=config.backend_context, observed=effective)
                run["status"] = "configuration_mismatch"
                break
            if remaining() <= 0:
                run["status"] = "timeout"
                break
            raw_calls = response.get("tool_calls") or []
            if len(raw_calls) > 16:
                error("malformed_tool_call")
                run["status"] = "model_error"
                break
            parsed = []
            after_request_files = workspace.snapshot()
            if after_request_files != known_files:
                intervention("manual_code_change")
                known_files = after_request_files
            for call in raw_calls:
                try:
                    parsed.append(parse_call(call))
                except (ValueError, TypeError, KeyError):
                    error("malformed_tool_call")
            if len(parsed) != len(raw_calls):
                # Never echo malformed / possibly secret payloads into diagnostics.
                messages.append({"role": "user", "content": "Malformed tool call. Use only listed tools and exact argument types."})
                save()
                continue
            messages.append({"role": "assistant", "content": response.get("content", ""),
                             **({"tool_calls": [{"function": {"name": name, "arguments": args}} for name, args in parsed]} if parsed else {})})
            if not parsed:
                # A model saying 'done' is never enough.
                verdict = verify_external(workspace.read("pricing.py"), timeout=min(5, remaining()))
                run["verification"] = verdict
                event("verification", success=verdict["success"], exit_code=verdict["exit_code"])
                if remaining() <= 0:
                    run["status"] = "timeout"
                    break
                if verdict["success"]:
                    run["status"] = "success"
                    run["verified_at_seconds"] = elapsed()
                    break
                error("build_test_failure")
                messages.append({"role": "user", "content": "Independent verification failed: " + json.dumps(verdict)})
            for name, args in parsed:
                if remaining() <= 0:
                    run["status"] = "timeout"
                    break
                signature = fingerprint([name, args])
                repeated = signature in seen_calls
                seen_calls[signature] = seen_calls.get(signature, 0) + 1
                consecutive = consecutive + 1 if signature == last_signature else 1
                last_signature = signature
                tool_start = elapsed()
                event("tool_started", name=name, step=step)
                save()
                category = None
                try:
                    result, success = workspace.execute(name, args, remaining())
                    after_files = workspace.snapshot()
                    # A human may change another file during a model/tool request.
                    expected_files = dict(known_files)
                    if name == "write_file":
                        expected_files["pricing.py"] = fingerprint(args["content"])
                    if after_files != expected_files:
                        intervention("manual_code_change")
                    known_files = after_files
                    if not success:
                        category = "build_test_failure" if name == "run_tests" else "tool_execution_error"
                except subprocess_timeout_types() as exc:
                    result, success, category = {"error": "verifier_timeout"}, False, "tool_execution_error"
                except Exception:
                    result, success, category = {"error": "tool_execution_error"}, False, "tool_execution_error"
                if category:
                    error(category)
                end = elapsed()
                if success and run.get("first_useful_action_seconds") is None:
                    run["first_useful_action_seconds"] = end
                run["tool_calls"].append({"name": name, "start_seconds": tool_start,
                    "end_seconds": end, "duration_seconds": end - tool_start, "success": success,
                    "arguments_bytes": len(json.dumps(args).encode("utf-8")),
                    "result_bytes": len(json.dumps(result).encode("utf-8")),
                    "repeated": repeated, "retry_count": 0, "error": category})
                messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})
                context("after_tool", estimate(messages), step=step)
                event("tool_completed", name=name, success=success, step=step)
                if remaining() <= 0:
                    run["status"] = "timeout"
                    break
                if name == "run_tests" and success:
                    run["verification"] = result
                    run["status"] = "success"
                    run["verified_at_seconds"] = end
                    break
                if consecutive >= config.loop_limit:
                    error("agent_loop")
                    run["status"] = "agent_loop"
                    break
            save()
            if run["status"] != "running":
                break
        else:
            run["status"] = "step_limit"
    except KeyboardInterrupt:
        run["status"] = "interrupted"
        event("user_stop")
    except Exception as exc:
        run["status"] = "failed"
        error(classify_error(exc))
    finally:
        # Verify final bytes again independently, including externally edited files.
        try:
            if workspace.snapshot() != known_files:
                intervention("manual_code_change")
            if run["status"] == "success":
                verdict = verify_external(workspace.read("pricing.py"), timeout=5)
                run["verification"] = verdict
                if not verdict["success"]:
                    run["status"] = "verification_failed"
        except Exception:
            run["status"] = "verification_failed"
            run["verification"] = {"success": False, "status": "verifier_error"}
        context("task_completion", estimate(messages))
        event("task_completed", status=run["status"])
        sampler.stop()
        save()
    return run, root / "result.json"


def subprocess_timeout_types():
    import subprocess
    return (subprocess.TimeoutExpired, TimeoutError)
