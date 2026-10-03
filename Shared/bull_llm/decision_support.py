"""Transparent model-choice profiles built only from precomputed run metrics.

This module never scores model answers and never changes benchmark quality.  It
turns already reported native-quality, speed, task-completion and memory metrics
into an explicitly labelled decision aid for one benchmark run.
"""

from __future__ import annotations

from collections import Counter
from math import log1p
from typing import Any, Iterable, Mapping


PROFILE_DEFINITIONS = {
    "quality": {
        "label": "Quality",
        "weights": {"quality": 0.85, "speed": 0.05, "reliability": 0.10, "memory": 0.0},
    },
    "speed": {
        "label": "Speed",
        "weights": {"quality": 0.20, "speed": 0.70, "reliability": 0.10, "memory": 0.0},
    },
    "balance": {
        "label": "Balance",
        "weights": {"quality": 0.55, "speed": 0.30, "reliability": 0.10, "memory": 0.05},
    },
    "low_memory": {
        "label": "Low memory",
        "weights": {"quality": 0.45, "speed": 0.15, "reliability": 0.10, "memory": 0.30},
    },
}


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def _scale(values: Mapping[str, float], *, invert: bool = False, logarithmic: bool = False) -> dict[str, float]:
    if not values:
        return {}
    prepared = {key: log1p(max(0.0, value)) if logarithmic else value for key, value in values.items()}
    low, high = min(prepared.values()), max(prepared.values())
    if high == low:
        scaled = {key: 1.0 for key in prepared}
    else:
        scaled = {key: (value - low) / (high - low) for key, value in prepared.items()}
    return {key: 1.0 - value for key, value in scaled.items()} if invert else scaled


def _native_quality(row: Mapping[str, Any]) -> tuple[float | None, float | None, bool]:
    """Return observed mean, conservative choice value, and partial coverage.

    A confidence-interval lower bound is useful for a conservative *choice*,
    but it is never the observed Native score and must not be shown as one.
    """
    complete = _number(row.get("chat_native_score"))
    if complete is not None:
        conservative = _number(row.get("chat_native_ci95_low"))
        return complete, conservative if conservative is not None else complete, False
    overall = _number(row.get("overall_native_score"))
    return overall, overall, overall is not None


def build_decision_support(
    rows: Iterable[Mapping[str, Any]],
    custom_weights: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return comparable points and profile winners for this run only.

    Profiles are unavailable when native quality is unavailable.  A speed-led
    recommendation also applies a transparent quality/task gate so a very fast
    but unusable result is not presented as the best working choice.
    """

    source_rows = list(rows)
    model_counts = Counter(str(row.get("model") or "?") for row in source_rows)
    prepared = []
    for row in source_rows:
        quality, decision_quality, partial = _native_quality(row)
        model_id = str(row.get("model") or "?")
        backend = str(row.get("backend") or "")
        label = f"{model_id} [{backend}]" if model_counts[model_id] > 1 and backend else model_id
        prepared.append(
            {
                "model": label,
                "model_id": model_id,
                "backend": backend or None,
                "quality": quality,
                "decision_quality": decision_quality,
                "decision_quality_basis": "ci95_low" if decision_quality != quality else "native_mean",
                "quality_partial": partial,
                "speed": _number(row.get("primary_eval_warm_avg") or row.get("primary_eval_avg")),
                "reliability": _number(
                    row.get("native_task_completion_rate")
                    if row.get("native_task_completion_rate") is not None
                    else row.get("native_completion_rate")
                ),
                "vram_mib": _number(row.get("vram_peak_mib")),
                "critical_failures": int(row.get("critical_failure_count") or 0),
            }
        )

    quality_values = {row["model"]: row["quality"] for row in prepared if row["quality"] is not None}
    decision_quality_values = {
        row["model"]: row["decision_quality"]
        for row in prepared if row["decision_quality"] is not None
    }
    speed_values = {row["model"]: row["speed"] for row in prepared if row["speed"] is not None}
    memory_values = {row["model"]: row["vram_mib"] for row in prepared if row["vram_mib"] is not None}
    quality_norm = _scale(quality_values)
    decision_quality_norm = _scale(decision_quality_values)
    speed_norm = _scale(speed_values, logarithmic=True)
    memory_norm = _scale(memory_values, invert=True)

    best_decision_quality = max(decision_quality_values.values(), default=None)
    for row in prepared:
        model = row["model"]
        row["quality_norm"] = quality_norm.get(model)
        row["decision_quality_norm"] = decision_quality_norm.get(model)
        row["speed_norm"] = speed_norm.get(model)
        row["memory_norm"] = memory_norm.get(model)
        row["quality_gate"] = bool(
            best_decision_quality is not None
            and row["decision_quality"] is not None
            and row["decision_quality"] >= max(0.60, best_decision_quality - 0.10)
            and (row["reliability"] is None or row["reliability"] >= 0.80)
        )

    profiles = dict(PROFILE_DEFINITIONS)
    if custom_weights is not None:
        weights = {key: max(0.0, _number(custom_weights.get(key)) or 0.0) for key in ("quality", "speed", "reliability", "memory")}
        total = sum(weights.values())
        if total <= 0:
            raise ValueError("custom decision weights must contain a positive value")
        profiles["custom"] = {"label": "Custom", "weights": {key: value / total for key, value in weights.items()}}

    results = []
    for profile_id, profile in profiles.items():
        weights = profile["weights"]
        candidates = []
        for row in prepared:
            if row["quality"] is None:
                continue
            if profile_id in ("speed", "balance", "low_memory", "custom") and not row["quality_gate"]:
                continue
            values = {
                "quality": row["decision_quality_norm"],
                "speed": row["speed_norm"],
                "reliability": row["reliability"],
                "memory": row["memory_norm"],
            }
            required = [name for name, weight in weights.items() if weight > 0]
            if any(values[name] is None for name in required):
                continue
            utility = sum(weights[name] * float(values[name]) for name in required)
            candidates.append((utility, row))
        if not candidates:
            results.append(
                {
                    "id": profile_id,
                    "label": profile["label"],
                    "weights": dict(weights),
                    "winner": None,
                    "utility": None,
                    "reason": "insufficient comparable metrics or no model passed the quality gate",
                }
            )
            continue
        best_utility = max(item[0] for item in candidates)
        tied = [row for utility, row in candidates if abs(utility - best_utility) <= 1e-12]
        if len(tied) > 1:
            results.append(
                {
                    "id": profile_id,
                    "label": profile["label"],
                    "weights": dict(weights),
                    "winner": None,
                    "tied_models": sorted(row["model"] for row in tied),
                    "utility": best_utility,
                    "reason": "equal decision utility; no arbitrary winner is selected",
                }
            )
            continue
        winner = tied[0]
        results.append(
            {
                "id": profile_id,
                "label": profile["label"],
                "weights": dict(weights),
                "winner": winner["model"],
                "utility": best_utility,
                "quality": winner["quality"],
                "decision_quality": winner["decision_quality"],
                "decision_quality_basis": winner["decision_quality_basis"],
                "speed": winner["speed"],
                "reliability": winner["reliability"],
                "vram_mib": winner["vram_mib"],
                "reason": "highest within-run decision utility among models that passed the gate",
            }
        )

    warnings = [
        "Decision profiles are relative to this run and are not new benchmark quality scores.",
        "Speed-led profiles require native quality within 10 percentage points of the best result, at least 60%, and task completion of at least 80% when available.",
    ]
    if any(row["quality_partial"] for row in prepared):
        warnings.append("Some recommendations use non-CHAT selected-test quality; compare only like-for-like runs.")
    if any(row["decision_quality_basis"] == "ci95_low" for row in prepared):
        warnings.append("Native score is the observed mean; the lower 95% CI is used separately as a conservative decision value.")
    if any(row["vram_mib"] is None for row in prepared):
        warnings.append("Memory is unknown for one or more models; the Low memory profile stays unavailable without comparable VRAM measurements.")
    if any(row["speed"] is None for row in prepared):
        warnings.append("Speed is unknown for one or more models; profiles requiring speed stay unavailable for those rows.")
    return {"schema": "bull-model-decision-support", "version": 1, "points": prepared, "profiles": results, "warnings": warnings}


__all__ = ["PROFILE_DEFINITIONS", "build_decision_support"]
