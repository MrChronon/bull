"""Typed, UI-independent public contracts for BULL Core.

The contracts are deliberately transport-neutral.  Runtime adapters return
native model output; evaluation and presentation are separate consumers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence, runtime_checkable


JsonObject = Mapping[str, Any]
EventSink = Callable[["InferenceEvent"], None]


class BackendKind(str, Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"


class InferenceEventKind(str, Enum):
    STARTED = "started"
    TEXT = "text"
    REASONING = "reasoning"
    TOOL = "tool"
    METRICS = "metrics"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ArtifactClassification(str, Enum):
    SHARE_SAFE = "share_safe"
    PRIVATE = "private"


@dataclass(frozen=True)
class BackendCapabilities:
    streaming: bool
    tools: bool | None = None
    thinking: bool | None = None
    structured_output: bool | None = None
    cancellation: bool | None = None
    telemetry: bool | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelDescriptor:
    id: str
    name: str
    digest: str = ""
    capabilities: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Model id and name must not be empty")


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant", "tool"}:
            raise ValueError(f"Unsupported chat role: {self.role}")

    def as_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            row["name"] = self.name
        if self.tool_call_id is not None:
            row["tool_call_id"] = self.tool_call_id
        return row


@dataclass(frozen=True)
class GenerationRequest:
    request_id: str
    model: str
    messages: tuple[ChatMessage, ...]
    options: Mapping[str, Any] = field(default_factory=dict)
    think: bool | str | None = None
    tools: tuple[Mapping[str, Any], ...] = ()
    response_format: Mapping[str, Any] | None = None
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not self.messages:
            raise ValueError("messages must not be empty")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    def legacy_messages(self) -> list[dict[str, Any]]:
        return [message.as_dict() for message in self.messages]


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class GenerationResponse:
    request_id: str
    model: str
    content: str
    reasoning: str = ""
    finish_reason: str | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)
    raw_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InferenceEvent:
    kind: InferenceEventKind
    request_id: str
    monotonic_seconds: float
    text: str = ""
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    prompt: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreResult:
    score: float
    passed: bool
    dimensions: Mapping[str, float] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class TelemetrySnapshot:
    collected_at_utc: str
    values: Mapping[str, float | int | str | bool | None]
    capabilities: tuple[str, ...] = ()


@runtime_checkable
class BackendAdapter(Protocol):
    @property
    def kind(self) -> BackendKind: ...
    def health(self, timeout_seconds: float = 2.0) -> Mapping[str, Any]: ...
    def capabilities(self) -> BackendCapabilities: ...
    def list_models(self) -> Sequence[ModelDescriptor]: ...
    def describe_model(self, model_id: str) -> ModelDescriptor: ...
    def generate(self, request: GenerationRequest, event_sink: EventSink | None = None) -> GenerationResponse: ...
    def cancel(self, request_id: str) -> bool: ...
    def runtime_fingerprint(self) -> str: ...


@runtime_checkable
class BenchmarkPack(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def version(self) -> str: ...
    def list_cases(self) -> Sequence[BenchmarkCase]: ...
    def validate(self) -> Sequence[str]: ...


@runtime_checkable
class Runner(Protocol):
    def run_case(self, case: BenchmarkCase, request: GenerationRequest) -> GenerationResponse: ...
    def resume(self, checkpoint: Mapping[str, Any]) -> Iterable[GenerationResponse]: ...


@runtime_checkable
class Scorer(Protocol):
    def score(self, case: BenchmarkCase, response: GenerationResponse, context: Mapping[str, Any]) -> ScoreResult: ...


@runtime_checkable
class Verifier(Protocol):
    def verify(self, case: BenchmarkCase, response: GenerationResponse) -> VerificationResult: ...


@runtime_checkable
class TelemetryProvider(Protocol):
    def capabilities(self) -> Sequence[str]: ...
    def snapshot(self) -> TelemetrySnapshot: ...


@runtime_checkable
class ArtifactStore(Protocol):
    @property
    def root(self) -> Path: ...
    def write_json(self, relative_path: str | Path, value: Any, classification: ArtifactClassification) -> Path: ...
    def read_json(self, relative_path: str | Path) -> Any: ...
    def sha256(self, relative_path: str | Path) -> str: ...


@runtime_checkable
class ReportRenderer(Protocol):
    def render(self, summary: Mapping[str, Any], store: ArtifactStore, relative_path: str | Path) -> Path: ...


@runtime_checkable
class SchemaMigration(Protocol):
    @property
    def source_schema(self) -> str: ...
    @property
    def source_version(self) -> int: ...
    @property
    def target_schema(self) -> str: ...
    @property
    def target_version(self) -> int: ...
    def migrate_copy(self, document: Mapping[str, Any]) -> Mapping[str, Any]: ...
