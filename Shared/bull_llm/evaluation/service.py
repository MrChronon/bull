"""Pure evaluation of already-produced native model responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..core import BenchmarkCase, GenerationResponse, ScoreResult, Scorer, VerificationResult, Verifier


@dataclass(frozen=True)
class EvaluationResult:
    native_response: GenerationResponse
    verification: VerificationResult
    native_score: ScoreResult


def evaluate_native(
    case: BenchmarkCase,
    native_response: GenerationResponse,
    scorer: Scorer,
    verifier: Verifier,
    context: Mapping[str, Any] | None = None,
) -> EvaluationResult:
    """Score model-native output; recovery output remains a separate caller concern."""
    verification = verifier.verify(case, native_response)
    score = scorer.score(case, native_response, context or {})
    return EvaluationResult(native_response, verification, score)
