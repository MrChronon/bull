"""Validated configuration and privacy-preserving, atomic local storage."""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import CONFIG_SCHEMA, RUN_SCHEMA, SCHEMA_VERSION
from ..storage import atomic_json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def label(value):
    """Untrusted display labels must not contain terminal controls or paths."""
    value = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(value))
    value = re.sub(r"(?:[A-Za-z]:[\\/]|/home/|/Users/)\S+", "[path]", value)
    value = re.sub(r"(?i)(?:https?://|ssh://)\S+", "[endpoint]", value)
    value = re.sub(r"(?i)\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=]\s*\S+", "[redacted]", value)
    value = re.sub(r"\b(?:sk-|gh[pousr]_|hf_)[A-Za-z0-9_-]{20,}\b", "[redacted]", value)
    return value[:160]


@dataclass
class AgentConfig:
    model: str
    name: str = "Agent default"
    backend_context: int = 32768
    agent_context: int = 28672
    sampling: dict = field(default_factory=lambda: {
        "temperature": 0.2, "top_p": 0.9, "top_k": 40, "min_p": 0.0,
        "repeat_penalty": 1.1, "num_predict": 2048, "seed": 42,
    })
    system_prompt: str = "You are a coding agent. Solve the task using the provided tools."
    instructions: str = "Read the project requirements. Edit code, run tests, fix failures."
    project_rules: str = "Only edit the task's allowed source file. Preserve function names."
    tool_safety_rules: str = "No shell, network, imports, credentials or external files."
    rules_name: str = "Restricted Python agent v1"
    rules_version: str = "1"
    context_strategy: str = "compact"
    compaction_keep_turns: int = 2
    max_steps: int = 40
    timeout_seconds: int = 600
    request_timeout_seconds: int = 120
    loop_limit: int = 4

    @property
    def reserve(self):
        return self.backend_context - self.agent_context

    def validate(self):
        if not isinstance(self.model, str) or not self.model.strip() or len(self.model) > 200:
            raise ValueError("Выберите модель из каталога backend.")
        if any(ord(c) < 32 for c in self.model):
            raise ValueError("Недопустимое имя модели.")
        bounds = {"backend_context": (2048, 1048576), "agent_context": (1024, 1048576),
                  "max_steps": (1, 200), "timeout_seconds": (1, 7200),
                  "request_timeout_seconds": (1, 1800), "loop_limit": (2, 20),
                  "compaction_keep_turns": (1, 10)}
        for key, (low, high) in bounds.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{key}: допустимо {low}..{high}.")
        ranges = {"temperature": (0, 2), "top_p": (0, 1), "top_k": (0, 1000),
                  "min_p": (0, 1), "repeat_penalty": (0.1, 3),
                  "num_predict": (1, 32768), "seed": (0, 2147483647)}
        if not isinstance(self.sampling, dict) or set(self.sampling) != set(ranges):
            raise ValueError("Sampling должен содержать ровно семь поддерживаемых параметров.")
        for key, (low, high) in ranges.items():
            value = self.sampling[key]
            if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
                raise ValueError(f"Некорректный sampling: {key}.")
            if key in ("top_k", "num_predict", "seed") and type(value) is not int:
                raise ValueError(f"{key} должен быть целым числом.")
        if self.reserve < self.sampling["num_predict"]:
            raise ValueError("Резерв контекста должен вмещать num_predict. Уменьшите agent limit.")
        if self.context_strategy not in ("compact", "stop"):
            raise ValueError("Context strategy: compact или stop.")
        for key in ("system_prompt", "instructions", "project_rules", "tool_safety_rules"):
            if not isinstance(getattr(self, key), str) or len(getattr(self, key)) > 100000:
                raise ValueError(f"Слишком большой или неверный {key}.")
        for key in ("name", "rules_name", "rules_version"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key) or len(getattr(self, key)) > 160:
                raise ValueError(f"Некорректный {key}.")
        return self

    def warnings(self):
        return (["Малый резерв контекста: рекомендуется запас сверх максимального ответа."]
                if self.reserve < max(4096, self.sampling["num_predict"] + 1024) else [])

    def rules(self):
        return {k: getattr(self, k) for k in
                ("system_prompt", "instructions", "project_rules", "tool_safety_rules")}

    def public_snapshot(self):
        data = asdict(self)
        for key in self.rules():
            data.pop(key)
        for key in ("model", "name", "rules_name", "rules_version"):
            data[key] = label(data[key])
        return {**data, "context_reserve": self.reserve,
                "instructions_sha256": fingerprint(self.rules()),
                "configuration_sha256": fingerprint(asdict(self))}


def load_json(path):
    limit = 20 * 1024 * 1024
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("JSON exceeds 20 MiB limit.")
    try:
        data = json.loads(raw.decode("utf-8-sig"),
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        def check(value, depth=0):
            if depth > 40:
                raise ValueError("Agent JSON nesting exceeds limit.")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Agent JSON requires finite numbers.")
            if isinstance(value, (dict, list)):
                for child in value.values() if isinstance(value, dict) else value:
                    check(child, depth + 1)
        check(data)
    except RecursionError as exc:
        raise ValueError("Agent JSON nesting exceeds limit.") from exc
    if not isinstance(data, dict):
        raise ValueError("Agent JSON must be an object.")
    return data


def save_config(path, config):
    config.validate()
    atomic_json(path, {"schema": CONFIG_SCHEMA, "schema_version": SCHEMA_VERSION,
                       "config": asdict(config)})


def load_config(path):
    data = load_json(path)
    if data.get("schema") != CONFIG_SCHEMA or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Неподдерживаемая схема Agent configuration.")
    try:
        return AgentConfig(**data["config"]).validate()
    except (KeyError, TypeError) as exc:
        raise ValueError("Некорректная Agent configuration.") from exc


def load_run(path):
    data = load_json(path)
    if data.get("schema") != RUN_SCHEMA or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Неподдерживаемая схема Agent run.")
    def invalid():
        raise ValueError("Неполный или повреждённый Agent run.")
    def number(value):
        return type(value) in (int, float) and 0 <= value <= 1e18 and math.isfinite(value)
    for key in ("metrics", "config", "task", "model", "verification"):
        if not isinstance(data.get(key), dict):
            invalid()
    for key in ("run_id", "timestamp", "status"):
        if not isinstance(data.get(key), str) or not data[key]:
            invalid()
    for key in ("requests", "contexts", "events", "interventions"):
        if not isinstance(data.get(key), list) or any(not isinstance(row, dict) for row in data[key]):
            invalid()
    config = data["config"]
    if not {"model", "sampling", "backend_context", "agent_context"} <= config.keys():
        invalid()
    try:
        AgentConfig(**{f.name: config[f.name] for f in fields(AgentConfig) if f.name in config}).validate()
    except TypeError:
        invalid()
    for row in data["contexts"]:
        if not number(row.get("tokens")) or not number(row.get("elapsed_seconds")) or not isinstance(row.get("source"), str):
            invalid()
    for row in data["events"]:
        if not number(row.get("elapsed_seconds")) or not isinstance(row.get("type"), str):
            invalid()
    metrics = data["metrics"]
    for key, value in metrics.items():
        if key not in ("resources", "llm_metric_scope", "success", "autonomous_success") and value is not None and not number(value):
            invalid()
    resources = metrics.get("resources", {})
    if not isinstance(resources, dict):
        invalid()
    for scope, kinds in resources.items():
        if scope not in ("client", "backend", "client_and_backend", "unknown") or not isinstance(kinds, dict):
            invalid()
        for memory in kinds.values():
            if not isinstance(memory, dict):
                invalid()
            if any(memory.get(key) is not None and not number(memory[key]) for key in ("start_bytes", "peak_bytes", "finish_bytes", "samples")):
                invalid()
    verified = (data.get("status") == "success" and
                data.get("verification", {}).get("success") is True and
                type(data.get("verification", {}).get("exit_code")) is int and
                data.get("verification", {}).get("exit_code") == 0)
    data["metrics"]["success"] = verified
    data["metrics"]["autonomous_success"] = verified and not data.get("interventions")
    return data


def classify_error(error):
    """Only category leaves the runner; raw exceptions can contain credentials."""
    import urllib.error
    text = str(error).casefold()
    if any(s in text for s in ("context", "exceed_context_size")):
        return "context_overflow"
    if isinstance(error, TimeoutError) or "timed out" in text or "timeout" in text:
        return "backend_timeout"
    if any(s in text for s in ("10061", "econnrefused", "connection refused")):
        return "connection_refused"
    if any(s in text for s in ("10054", "econnreset", "connection reset", "incomplete stream")):
        return "connection_reset"
    if isinstance(error, urllib.error.HTTPError):
        return "backend_http_error"
    if isinstance(error, json.JSONDecodeError) or "unexpected end of json" in text:
        return "malformed_tool_call"
    return "model_error" if "model" in text else "unknown"
