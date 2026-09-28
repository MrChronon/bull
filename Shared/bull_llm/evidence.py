"""Versioned evidence artifacts for BULL Benchmark Lab.

The module is deliberately independent from inference and scoring.  It turns
already-computed records and summaries into explicit private and share-safe
documents, hashes their provenance, and supports copy-only legacy migration.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import uuid
from typing import Any, Iterable, Mapping, Sequence

from .core.fingerprints import stable_fingerprint


RECORD_SCHEMA = "bull-benchmark-record"
RECORD_SCHEMA_VERSION = 1
SUMMARY_SCHEMA = "bull-benchmark-summary"
SUMMARY_SCHEMA_VERSION = 1
PROVENANCE_SCHEMA = "bull-evidence-provenance"
PROVENANCE_SCHEMA_VERSION = 1
MAX_EVIDENCE_BYTES = 128 * 1024 * 1024
METRIC_SPACES = (
    "quality.native",
    "quality.assisted",
    "contract",
    "runtime",
    "resources",
    "recovery",
    "reliability",
    "security",
    "human",
)

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_PRIVATE_KEYS = {
    "answer", "answers", "prompt", "prompts", "messages", "reasoning",
    "endpoint", "endpoints", "url", "urls", "identity_file", "private_key",
    "api_key", "token", "password", "home_path", "source_path", "raw_response",
}
_PRIVATE_TEXT_PATTERNS = (
    re.compile(r"(?i)[a-z]:[\\/]users[\\/][^\\/\s]+"),
    re.compile(r"(?i)/(?:home|users)/[^/\s]+"),
    re.compile(r"(?i)\b(?:https?|ssh)://[^\s]+"),
    re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
)


class EvidenceValidationError(ValueError):
    pass


def _clone(value: Any) -> Any:
    """Return a finite, JSON-only deep copy."""
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _at(value: Mapping[str, Any] | None, path: str, default: Any = None) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = current[part]
    return current


def _unique(values: Iterable[Any]) -> list[str]:
    return sorted({str(value) for value in values if value not in (None, "")})


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evidence_paths(raw_json_path: str | Path) -> tuple[Path, Path]:
    base = Path(raw_json_path)
    return (
        base.with_name(base.stem + "_evidence_private.json"),
        base.with_name(base.stem + "_evidence_share_safe.json"),
    )


def _case_provenance(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cases: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        identity = _at(record, "identity", {}) or {}
        score = _at(record, "score.native", {}) or {}
        scorer_ref = identity.get("scorer_ref") or score.get("method") or "none"
        verifier_ref = identity.get("verifier_ref") or "benchmark_contract_v1"
        execution_hash = identity.get("benchmark_execution_sha256") or ""
        scorer_hash = identity.get("scorer_sha256") or stable_fingerprint({
            "scorer_ref": scorer_ref,
            "execution_sha256": execution_hash,
        })
        verifier_hash = identity.get("verifier_sha256") or stable_fingerprint({
            "verifier_ref": verifier_ref,
            "execution_sha256": execution_hash,
        })
        row = {
            "id": str(identity.get("benchmark") or "unknown"),
            "version": int(identity.get("benchmark_version") or 1),
            "category": str(identity.get("benchmark_category") or "unknown"),
            "pack_identity": identity.get("benchmark_pack_identity"),
            "pack_manifest_sha256": identity.get("benchmark_pack_manifest_sha256"),
            "definition_sha256": identity.get("benchmark_definition_sha256"),
            "prompt_sha256": identity.get("benchmark_prompt_sha256") or "",
            "reference_sha256": identity.get("benchmark_reference_sha256") or "",
            "execution_sha256": execution_hash,
            "scorer": {"ref": str(scorer_ref), "sha256": str(scorer_hash)},
            "verifier": {"ref": str(verifier_ref), "sha256": str(verifier_hash)},
        }
        key = (
            row["id"], row["version"], row["prompt_sha256"], row["execution_sha256"],
            row["scorer"]["sha256"], row["verifier"]["sha256"],
        )
        cases[key] = row
    return [cases[key] for key in sorted(cases, key=lambda item: tuple(str(part) for part in item))]


def build_provenance(
    records: Sequence[Mapping[str, Any]],
    *,
    spec: Mapping[str, Any] | None = None,
    engine_version: str,
    source_sha256: str | None = None,
    created_at_utc: str | None = None,
    migration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    records = list(records or [])
    spec = dict(spec or {})
    if source_sha256 is not None and not _HASH_RE.fullmatch(str(source_sha256)):
        raise EvidenceValidationError("source_sha256 must be lowercase SHA-256")
    created = created_at_utc or datetime.now(timezone.utc).isoformat(timespec="seconds")
    cases = _case_provenance(records)
    pack_rows: dict[str, dict[str, Any]] = {}
    for case in cases:
        identity = case.get("pack_identity")
        if identity:
            pack_rows[str(identity)] = {
                "identity": str(identity),
                "manifest_sha256": case.get("pack_manifest_sha256"),
            }
    execution_order = []
    for record in records:
        schedule = _at(record, "schedule", {}) or {}
        identity = _at(record, "identity", {}) or {}
        execution_order.append({
            "benchmark": identity.get("benchmark"),
            "model": identity.get("model"),
            "run": identity.get("run"),
            "attempt": identity.get("attempt"),
            "global_position": schedule.get("global_position"),
            "round_position": schedule.get("round_position"),
            "block_position": schedule.get("block_position"),
            "post_resume": bool(schedule.get("post_resume")),
        })
    fingerprints = {
        "launch": _unique(
            _at(row, "config.backend_launch_fingerprint")
            or _at(row, "config.backend_runtime_fingerprint") for row in records
        ),
        "effective_runtime_request": _unique(
            _at(row, "config.effective_runtime_request_fingerprint") for row in records
        ),
        "observed_runtime": _unique(
            _at(row, "telemetry.runtime.observed_fingerprint") for row in records
        ),
        "effective_profile": _unique(
            _at(row, "config.effective_profile_fingerprint") for row in records
        ),
    }
    block: dict[str, Any] = {
        "schema": PROVENANCE_SCHEMA,
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "immutable": True,
        "created_at_utc": created,
        "engine": {"name": "BULL", "version": str(engine_version)},
        "source": {"sha256": source_sha256, "record_count": len(records)},
        "benchmark_spec_sha256": spec.get("spec_fingerprint") or stable_fingerprint(spec),
        "packs": list(pack_rows.values()),
        "cases": cases,
        "fingerprints": fingerprints,
        "execution_order_sha256": stable_fingerprint(execution_order),
    }
    if migration:
        block["migration"] = _clone(migration)
    block["provenance_sha256"] = stable_fingerprint(block)
    return block


def validate_provenance(value: Mapping[str, Any]) -> None:
    block = _clone(value)
    digest = block.pop("provenance_sha256", None)
    if block.get("schema") != PROVENANCE_SCHEMA or block.get("schema_version") != PROVENANCE_SCHEMA_VERSION:
        raise EvidenceValidationError("unsupported provenance schema")
    if block.get("immutable") is not True:
        raise EvidenceValidationError("provenance must be immutable")
    if not isinstance(digest, str) or stable_fingerprint(block) != digest:
        raise EvidenceValidationError("provenance hash mismatch")
    fingerprints = block.get("fingerprints")
    if not isinstance(fingerprints, dict) or set(fingerprints) != {
        "launch", "effective_runtime_request", "observed_runtime", "effective_profile"
    }:
        raise EvidenceValidationError("runtime fingerprint spaces are incomplete")


def _quality(row: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "mean": row.get(prefix + "_score_avg"),
        "sd": row.get(prefix + "_score_sd"),
        "min": row.get(prefix + "_score_min"),
        "max": row.get(prefix + "_score_max"),
        "ci95_low": row.get(prefix + "_score_ci95_low"),
        "ci95_high": row.get(prefix + "_score_ci95_high"),
        "valid_runs": row.get(prefix + "_score_valid_runs"),
        "worst_seed": row.get(prefix + "_score_worst_seed"),
        "content": row.get(prefix + "_content_score") if prefix == "native" else row.get("assisted_content_score"),
        "format": row.get(prefix + "_format_score") if prefix == "native" else row.get("assisted_format_score"),
    }


def normalize_case_metric(row: Mapping[str, Any]) -> dict[str, Any]:
    launch = row.get("backend_launch_fingerprints") or [row.get("backend_launch_fingerprint")]
    effective = row.get("effective_runtime_request_fingerprints") or [row.get("effective_runtime_request_fingerprint")]
    observed = row.get("observed_runtime_fingerprints") or [row.get("observed_runtime_fingerprint")]
    return {
        "identity": {
            "benchmark": row.get("benchmark"),
            "category": row.get("benchmark_category"),
            "version": row.get("benchmark_version"),
            "model": row.get("model"),
            "backend": row.get("backend"),
        },
        "quality": {
            "native": _quality(row, "native"),
            "assisted": _quality(row, "final"),
        },
        "contract": {
            "native_generation_rate": row.get("native_generation_completion_rate"),
            "native_task_rate": row.get("native_task_completion_rate"),
            "native_structure_rate": row.get("native_structural_completion_rate"),
            "native_schema_rate": row.get("native_schema_exact_rate"),
            "assisted_generation_rate": row.get("generation_completion_rate"),
            "assisted_task_rate": row.get("task_completion_rate"),
            "assisted_structure_rate": row.get("final_structural_completion_rate"),
            "assisted_schema_rate": row.get("final_schema_exact_rate"),
        },
        "runtime": {
            "context_length": row.get("context_length"),
            "context_lengths": _clone(row.get("context_lengths") or []),
            "warm_tokens_per_second": row.get("primary_eval_warm_avg"),
            "tokens_per_second": {
                "mean": row.get("primary_eval_avg"), "sd": row.get("primary_eval_sd"),
                "min": row.get("primary_eval_min"), "max": row.get("primary_eval_max"),
            },
            "latency_seconds": {
                "mean": row.get("pipeline_wall_avg"), "sd": row.get("pipeline_wall_sd"),
                "min": row.get("pipeline_wall_min"), "max": row.get("pipeline_wall_max"),
                "ci95_low": row.get("pipeline_wall_ci95_low"),
                "ci95_high": row.get("pipeline_wall_ci95_high"),
            },
            "load_states": _clone(row.get("load_states") or []),
        },
        "resources": {
            "vram_peak_mib": row.get("vram_peak_mib"),
            "gpu_utilization_mean": row.get("gpu_util_avg"),
            "gpu_offload_percent": row.get("gpu_offload_last_pct"),
        },
        "recovery": {
            "used_rate": row.get("recovery_rate"),
            "dependency": row.get("recovery_dependency"),
            "client_attempts": row.get("client_attempts"),
            "transport_failures": row.get("client_transport_failures"),
            "resumed_runs": row.get("client_resumed_runs"),
            "excluded_from_model_score": row.get("client_recovery_excluded_from_model_score") is True,
        },
        "reliability": {
            "runs_planned": row.get("runs_planned"),
            "runs_executed": row.get("runs_executed"),
            "errors": row.get("errors"),
            "seeds": _clone(row.get("seeds") or []),
            "worst_seed": row.get("score_worst_seed"),
            "rank_stability": row.get("rank_stability"),
            "rank_stability_status": row.get("rank_stability_status"),
            "pareto_status": row.get("pareto_status"),
        },
        "security": {"status": "not_evaluated", "dimensions": {}},
        "human": {"status": "not_reviewed"},
        "fingerprints": {
            "launch": _unique(launch),
            "effective_runtime_request": _unique(effective),
            "observed_runtime": _unique(observed),
        },
    }


def normalize_model_metric(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "identity": {"model": row.get("model"), "backend": row.get("backend")},
        "quality": {
            "native": {
                "score": row.get("chat_native_score", row.get("overall_native_score")),
                "partial_score": row.get("chat_native_score_partial"),
                "mean": row.get("chat_native_mean"), "sd": row.get("chat_native_sd"),
                "min": row.get("chat_native_min"), "max": row.get("chat_native_max"),
                "ci95_low": _at(row, "chat_native_ci95.0") if isinstance(row.get("chat_native_ci95"), Mapping) else (row.get("chat_native_ci95") or [None, None])[0],
                "ci95_high": _at(row, "chat_native_ci95.1") if isinstance(row.get("chat_native_ci95"), Mapping) else (row.get("chat_native_ci95") or [None, None])[1],
            },
            "assisted": {
                "score": row.get("chat_assisted_score", row.get("overall_assisted_score")),
                "partial_score": row.get("chat_assisted_score_partial"),
                "mean": row.get("chat_assisted_mean"), "sd": row.get("chat_assisted_sd"),
                "min": row.get("chat_assisted_min"), "max": row.get("chat_assisted_max"),
            },
            "categories_native": _clone(row.get("chat_category_scores_native") or {}),
            "categories_assisted": _clone(row.get("chat_category_scores_assisted") or {}),
        },
        "contract": {
            "native_generation_rate": row.get("native_generation_completion_rate"),
            "native_task_rate": row.get("native_task_completion_rate"),
            "assisted_generation_rate": row.get("generation_completion_rate"),
            "assisted_task_rate": row.get("task_completion_rate"),
        },
        "runtime": {"warm_tokens_per_second": row.get("primary_eval_warm_avg")},
        "resources": {"vram_peak_mib": row.get("vram_peak_mib")},
        "recovery": {
            "used_rate": row.get("recovery_rate", row.get("overall_recovery_rate")),
            "excluded_from_model_score": True,
        },
        "reliability": {
            "critical_failure_count": row.get("critical_failure_count"),
            "worst_test": row.get("worst_test"),
            "worst_seed": row.get("chat_native_worst_seed"),
            "suite_status": row.get("chat_suite_status"),
        },
        "security": {"status": "not_evaluated", "dimensions": {}},
        "human": {"status": "not_reviewed"},
    }


def _analytics(model_metrics: Sequence[Mapping[str, Any]], case_metrics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    confidence = []
    latency = []
    curves: dict[str, list[dict[str, Any]]] = {}
    heatmap = []
    for row in case_metrics:
        identity = row["identity"]
        native = row["quality"]["native"]
        wall = row["runtime"]["latency_seconds"]
        confidence.append({
            "benchmark": identity.get("benchmark"), "model": identity.get("model"),
            "mean": native.get("mean"), "low": native.get("ci95_low"), "high": native.get("ci95_high"),
            "available": None not in (native.get("ci95_low"), native.get("ci95_high")),
        })
        latency.append({
            "benchmark": identity.get("benchmark"), "model": identity.get("model"),
            **_clone(wall),
        })
        context = row["runtime"].get("context_length")
        if context is not None:
            curves.setdefault(str(identity.get("model")), []).append({
                "context_length": context,
                "native_score": native.get("mean"),
                "warm_tokens_per_second": row["runtime"].get("warm_tokens_per_second"),
            })
    for row in model_metrics:
        model = row["identity"].get("model")
        for category, value in row["quality"].get("categories_native", {}).items():
            heatmap.append({"model": model, "category": category, "native_score": value})
    for model, points in curves.items():
        unique = {(point["context_length"], point["native_score"], point["warm_tokens_per_second"]): point for point in points}
        curves[model] = sorted(unique.values(), key=lambda point: float(point["context_length"]))
    return {
        "confidence_intervals": confidence,
        "latency_distributions": latency,
        "context_curves": [{"model": model, "points": points} for model, points in sorted(curves.items())],
        "category_heatmap": heatmap,
    }


def build_private_record_document(
    records: Sequence[Mapping[str, Any]], provenance: Mapping[str, Any]
) -> dict[str, Any]:
    validate_provenance(provenance)
    return {
        "schema": RECORD_SCHEMA,
        "schema_version": RECORD_SCHEMA_VERSION,
        "artifact_classification": "private",
        "provenance": _clone(provenance),
        "records": _clone(list(records)),
    }


def build_share_safe_summary_document(
    model_rows: Sequence[Mapping[str, Any]],
    case_rows: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    validate_provenance(provenance)
    model_metrics = [normalize_model_metric(row) for row in model_rows]
    case_metrics = [normalize_case_metric(row) for row in case_rows]
    document = {
        "schema": SUMMARY_SCHEMA,
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "artifact_classification": "share_safe",
        "provenance": _clone(provenance),
        "metric_spaces": list(METRIC_SPACES),
        "statistics_policy": {
            "sd_minimum_samples": 2,
            "confidence_interval": "normal_approximation_95pct_when_n_gte_2",
            "warm_state": "observed_load_duration",
            "pareto": "uncertainty_aware",
            "single_run_superiority_claim": False,
        },
        "metrics": {"model": model_metrics, "case": case_metrics},
        "analytics": _analytics(model_metrics, case_metrics),
    }
    audit_share_safe(document)
    return document


def audit_share_safe(value: Any) -> None:
    findings: list[str] = []

    def visit(current: Any, path: str) -> None:
        if isinstance(current, Mapping):
            for key, item in current.items():
                normalized = str(key).casefold()
                child = f"{path}.{key}" if path else str(key)
                dynamic_metric_key = path.endswith((
                    ".categories_native", ".categories_assisted", ".dimensions"
                ))
                if normalized in _PRIVATE_KEYS and not dynamic_metric_key:
                    findings.append(child)
                visit(item, child)
        elif isinstance(current, list):
            for index, item in enumerate(current):
                visit(item, f"{path}[{index}]")
        elif isinstance(current, float) and not math.isfinite(current):
            findings.append(path + ":nonfinite")
        elif isinstance(current, str):
            for pattern in _PRIVATE_TEXT_PATTERNS:
                if pattern.search(current):
                    findings.append(path + ":private_text")
                    break

    visit(value, "")
    if findings:
        raise EvidenceValidationError("share-safe privacy audit failed: " + ", ".join(findings[:10]))


def _write_atomic_json(path: Path, value: Mapping[str, Any]) -> Path:
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    if len(payload) > MAX_EVIDENCE_BYTES:
        raise EvidenceValidationError("evidence artifact exceeds size limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return path


def _write_new_json(path: Path, value: Mapping[str, Any]) -> Path:
    if path.exists():
        raise FileExistsError(path)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    if len(payload) > MAX_EVIDENCE_BYTES:
        raise EvidenceValidationError("evidence artifact exceeds size limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            raise
        except OSError:
            with path.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
    finally:
        temp.unlink(missing_ok=True)
    return path


def save_evidence_artifacts(
    raw_json_path: str | Path,
    *,
    spec: Mapping[str, Any] | None,
    records: Sequence[Mapping[str, Any]],
    model_rows: Sequence[Mapping[str, Any]],
    case_rows: Sequence[Mapping[str, Any]],
    engine_version: str,
) -> tuple[Path, Path, dict[str, Any]]:
    source = Path(raw_json_path)
    source_hash = _file_sha256(source)
    provenance = build_provenance(
        records, spec=spec, engine_version=engine_version, source_sha256=source_hash
    )
    private_document = build_private_record_document(records, provenance)
    share_document = build_share_safe_summary_document(model_rows, case_rows, provenance)
    private_path, share_path = evidence_paths(source)
    _write_atomic_json(private_path, private_document)
    _write_atomic_json(share_path, share_document)
    return private_path, share_path, share_document


def _read_legacy_json(path: Path) -> Any:
    if path.stat().st_size > MAX_EVIDENCE_BYTES:
        raise EvidenceValidationError("legacy artifact exceeds size limit")
    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=lambda value: (_ for _ in ()).throw(EvidenceValidationError("non-finite JSON")))


def migrate_legacy_record_copy(
    source_path: str | Path, destination_path: str | Path, *, engine_version: str
) -> Path:
    source = Path(source_path).resolve()
    destination = Path(destination_path).resolve()
    if source == destination:
        raise EvidenceValidationError("migration destination must differ from source")
    before = _file_sha256(source)
    value = _read_legacy_json(source)
    records = value.get("records") if isinstance(value, dict) else value
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise EvidenceValidationError("legacy record source must contain a record array")
    provenance = build_provenance(
        records,
        engine_version=engine_version,
        source_sha256=before,
        migration={"mode": "copy_only", "source_schema": "legacy_benchmark_record"},
    )
    result = _write_new_json(destination, build_private_record_document(records, provenance))
    if _file_sha256(source) != before:
        result.unlink(missing_ok=True)
        raise EvidenceValidationError("source changed during migration")
    return result


def migrate_legacy_summary_copy(
    source_path: str | Path, destination_path: str | Path, *, engine_version: str
) -> Path:
    source = Path(source_path).resolve()
    destination = Path(destination_path).resolve()
    if source == destination:
        raise EvidenceValidationError("migration destination must differ from source")
    before = _file_sha256(source)
    rows = _read_legacy_json(source)
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise EvidenceValidationError("legacy summary source must contain a row array")
    provenance = build_provenance(
        [],
        engine_version=engine_version,
        source_sha256=before,
        migration={"mode": "copy_only", "source_schema": "legacy_benchmark_summary"},
    )
    result = _write_new_json(destination, build_share_safe_summary_document([], rows, provenance))
    if _file_sha256(source) != before:
        result.unlink(missing_ok=True)
        raise EvidenceValidationError("source changed during migration")
    return result


__all__ = [
    "EvidenceValidationError",
    "METRIC_SPACES",
    "PROVENANCE_SCHEMA",
    "PROVENANCE_SCHEMA_VERSION",
    "RECORD_SCHEMA",
    "RECORD_SCHEMA_VERSION",
    "SUMMARY_SCHEMA",
    "SUMMARY_SCHEMA_VERSION",
    "audit_share_safe",
    "build_private_record_document",
    "build_provenance",
    "build_share_safe_summary_document",
    "evidence_paths",
    "migrate_legacy_record_copy",
    "migrate_legacy_summary_copy",
    "normalize_case_metric",
    "normalize_model_metric",
    "save_evidence_artifacts",
    "validate_provenance",
]
