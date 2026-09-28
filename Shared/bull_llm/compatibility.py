"""Read-only recognition of artifact formats supported by the BULL bridge."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

from .schemas import (
    BENCH_CHECKPOINT_SCHEMA_VERSION,
    BENCH_CONFIG_SCHEMA_VERSION,
    BENCH_RECORD_SCHEMA_VERSION,
    BENCH_SPEC_SCHEMA_VERSION,
    BENCH_SUMMARY_SCHEMA_VERSION,
    PROMPT_INDEX_SCHEMA,
    PROMPT_INDEX_SCHEMA_VERSION,
    TESTED_PROFILE_SCHEMA,
    TESTED_PROFILE_SCHEMA_VERSION,
    USER_BENCHMARK_SCHEMA,
    USER_BENCHMARK_SCHEMA_VERSION,
    BULL_RECORD_SCHEMA,
    BULL_RECORD_SCHEMA_VERSION,
    BULL_SUMMARY_SCHEMA,
    BULL_SUMMARY_SCHEMA_VERSION,
)

MAX_ARTIFACT_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class CompatibilityInfo:
    artifact: str
    schema: str | None
    version: int
    can_read: bool = True
    can_resume: bool = False
    migration: str = "copy-only"


_NAMED_SCHEMAS = {
    (BULL_RECORD_SCHEMA, BULL_RECORD_SCHEMA_VERSION): CompatibilityInfo(
        "bull_benchmark_record", BULL_RECORD_SCHEMA, BULL_RECORD_SCHEMA_VERSION,
        migration="native"
    ),
    (BULL_SUMMARY_SCHEMA, BULL_SUMMARY_SCHEMA_VERSION): CompatibilityInfo(
        "bull_benchmark_summary", BULL_SUMMARY_SCHEMA, BULL_SUMMARY_SCHEMA_VERSION,
        migration="native"
    ),
    (TESTED_PROFILE_SCHEMA, TESTED_PROFILE_SCHEMA_VERSION): CompatibilityInfo(
        "tested_profile", TESTED_PROFILE_SCHEMA, TESTED_PROFILE_SCHEMA_VERSION
    ),
    (PROMPT_INDEX_SCHEMA, PROMPT_INDEX_SCHEMA_VERSION): CompatibilityInfo(
        "prompt_index", PROMPT_INDEX_SCHEMA, PROMPT_INDEX_SCHEMA_VERSION
    ),
    (USER_BENCHMARK_SCHEMA, USER_BENCHMARK_SCHEMA_VERSION): CompatibilityInfo(
        "user_benchmark", USER_BENCHMARK_SCHEMA, USER_BENCHMARK_SCHEMA_VERSION
    ),
    ("local-llm-agent-config", 1): CompatibilityInfo(
        "agent_configuration", "local-llm-agent-config", 1, migration="private-copy-only"
    ),
    ("local-llm-agent-run", 1): CompatibilityInfo(
        "agent_run", "local-llm-agent-run", 1
    ),
    ("local-llm-gpu-experiment", 1): CompatibilityInfo(
        "gpu_experiment", "local-llm-gpu-experiment", 1
    ),
}

_VERSION_ONLY = {
    ("benchmark_config", BENCH_CONFIG_SCHEMA_VERSION): CompatibilityInfo(
        "benchmark_config", None, BENCH_CONFIG_SCHEMA_VERSION
    ),
    ("benchmark_spec", BENCH_SPEC_SCHEMA_VERSION): CompatibilityInfo(
        "benchmark_spec", None, BENCH_SPEC_SCHEMA_VERSION
    ),
    ("benchmark_record", BENCH_RECORD_SCHEMA_VERSION): CompatibilityInfo(
        "benchmark_record", None, BENCH_RECORD_SCHEMA_VERSION
    ),
    ("benchmark_summary", BENCH_SUMMARY_SCHEMA_VERSION): CompatibilityInfo(
        "benchmark_summary", None, BENCH_SUMMARY_SCHEMA_VERSION
    ),
    ("benchmark_checkpoint", BENCH_CHECKPOINT_SCHEMA_VERSION): CompatibilityInfo(
        "benchmark_checkpoint", None, BENCH_CHECKPOINT_SCHEMA_VERSION,
        can_resume=False, migration="validated-copy-only"
    ),
}


def supported_legacy_artifacts() -> tuple[CompatibilityInfo, ...]:
    """Return an immutable description of formats accepted by this release."""
    return tuple(_NAMED_SCHEMAS.values()) + tuple(_VERSION_ONLY.values())


def _version(value: dict[str, Any]) -> int | None:
    for key in ("schema_version", "version"):
        raw = value.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool):
            return raw
    return None


def _kind(value: dict[str, Any], hint: str | None) -> str | None:
    explicit = value.get("artifact_type") or value.get("kind")
    if isinstance(explicit, str):
        normalized = explicit.strip().lower().replace("-", "_")
        if (normalized, _version(value)) in _VERSION_ONLY:
            return normalized
    name = (hint or "").lower()
    for kind in ("benchmark_checkpoint", "benchmark_summary", "benchmark_record",
                 "benchmark_spec", "benchmark_config"):
        token = kind.removeprefix("benchmark_")
        if token in name:
            return kind
    return None


def inspect_legacy_document(value: Any, *, filename_hint: str | None = None) -> CompatibilityInfo:
    """Classify a parsed legacy object without changing it."""
    if not isinstance(value, dict):
        raise ValueError("artifact root must be a JSON object")
    schema = value.get("schema")
    version = _version(value)
    if isinstance(schema, str) and version is not None:
        match = _NAMED_SCHEMAS.get((schema, version))
        if match:
            return match
        raise ValueError(f"unsupported legacy schema: {schema} v{version}")
    kind = _kind(value, filename_hint)
    match = _VERSION_ONLY.get((kind, version)) if kind and version is not None else None
    if match:
        return match
    raise ValueError("artifact type or supported schema version is not identifiable")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value is not allowed: {value}")


def _finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_finite(k) and _finite(v) for k, v in value.items())
    if isinstance(value, list):
        return all(_finite(item) for item in value)
    return True


def read_legacy_artifact(path: str | Path) -> tuple[CompatibilityInfo, dict[str, Any]]:
    """Read and validate a supported JSON artifact; never write or migrate it."""
    source = Path(path)
    size = source.stat().st_size
    if size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"artifact exceeds {MAX_ARTIFACT_BYTES} bytes")
    with source.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle, parse_constant=_reject_constant)
    if not _finite(value):
        raise ValueError("artifact contains a non-finite number")
    info = inspect_legacy_document(value, filename_hint=source.name)
    return info, deepcopy(value)
