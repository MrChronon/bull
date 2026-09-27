"""Backend adapters around injected runtime functions.

This layer does not import the monolithic client or any UI module.  The app may
inject the proven v0.22 functions while the runtime is extracted incrementally.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ..core import (
    BackendCapabilities,
    BackendKind,
    GenerationRequest,
    GenerationResponse,
    InferenceEvent,
    InferenceEventKind,
    ModelDescriptor,
    TokenUsage,
)
from .events import discard_event


HealthFn = Callable[[float], Mapping[str, Any] | bool | None]
ListModelsFn = Callable[[], Sequence[Mapping[str, Any]]]
DescribeModelFn = Callable[[str], Mapping[str, Any]]
GenerateFn = Callable[[GenerationRequest], GenerationResponse | tuple[str, str, Mapping[str, Any]]]
CancelFn = Callable[[str], bool]
FingerprintFn = Callable[[], str]


@dataclass(frozen=True)
class BackendPorts:
    health: HealthFn
    list_models: ListModelsFn
    describe_model: DescribeModelFn
    generate: GenerateFn
    cancel: CancelFn
    fingerprint: FingerprintFn
    capabilities: BackendCapabilities


class FunctionBackendAdapter:
    """Contract adapter shared by Ollama and llama.cpp ports."""

    def __init__(self, kind: BackendKind, ports: BackendPorts) -> None:
        self._kind = kind
        self._ports = ports

    @property
    def kind(self) -> BackendKind:
        return self._kind

    def health(self, timeout_seconds: float = 2.0) -> Mapping[str, Any]:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        result = self._ports.health(timeout_seconds)
        if isinstance(result, Mapping):
            return dict(result)
        return {"ok": bool(result), "backend": self.kind.value}

    def capabilities(self) -> BackendCapabilities:
        return self._ports.capabilities

    @staticmethod
    def _descriptor(raw: Mapping[str, Any], fallback_id: str = "") -> ModelDescriptor:
        name = str(raw.get("name") or raw.get("model") or raw.get("id") or fallback_id).strip()
        model_id = str(raw.get("id") or name or fallback_id).strip()
        caps = raw.get("capabilities") or ()
        return ModelDescriptor(
            id=model_id,
            name=name or model_id,
            digest=str(raw.get("digest") or ""),
            capabilities=tuple(str(item).casefold() for item in caps),
            metadata=dict(raw),
        )

    def list_models(self) -> tuple[ModelDescriptor, ...]:
        return tuple(self._descriptor(row) for row in self._ports.list_models())

    def describe_model(self, model_id: str) -> ModelDescriptor:
        if not model_id.strip():
            raise ValueError("model_id must not be empty")
        raw = dict(self._ports.describe_model(model_id) or {})
        model_info = raw.get("model_info")
        if isinstance(model_info, Mapping):
            merged = dict(model_info)
            merged.setdefault("capabilities", raw.get("capabilities") or ())
            raw = merged
        raw.setdefault("name", model_id)
        return self._descriptor(raw, model_id)

    def generate(self, request: GenerationRequest, event_sink=None) -> GenerationResponse:
        sink = event_sink or discard_event
        started = time.monotonic()
        sink(InferenceEvent(InferenceEventKind.STARTED, request.request_id, started))
        try:
            raw = self._ports.generate(request)
            if isinstance(raw, GenerationResponse):
                response = raw
            else:
                content, reasoning, metadata = raw
                meta = dict(metadata or {})
                prompt_tokens = meta.get("prompt_eval_count")
                completion_tokens = meta.get("eval_count")
                total_tokens = (
                    prompt_tokens + completion_tokens
                    if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int)
                    else None
                )
                response = GenerationResponse(
                    request_id=request.request_id,
                    model=request.model,
                    content=str(content or ""),
                    reasoning=str(reasoning or ""),
                    finish_reason=str(meta.get("done_reason") or meta.get("finish_reason") or "") or None,
                    usage=TokenUsage(prompt_tokens, completion_tokens, total_tokens),
                    runtime_metadata=meta,
                    raw_metadata=meta,
                )
            now = time.monotonic()
            if response.reasoning:
                sink(InferenceEvent(InferenceEventKind.REASONING, request.request_id, now, response.reasoning))
            if response.content:
                sink(InferenceEvent(InferenceEventKind.TEXT, request.request_id, now, response.content))
            sink(InferenceEvent(InferenceEventKind.METRICS, request.request_id, now, data=dict(response.runtime_metadata)))
            sink(InferenceEvent(InferenceEventKind.COMPLETED, request.request_id, now))
            return response
        except Exception as error:
            sink(InferenceEvent(
                InferenceEventKind.ERROR,
                request.request_id,
                time.monotonic(),
                data={"error_type": type(error).__name__},
            ))
            raise

    def cancel(self, request_id: str) -> bool:
        if not request_id.strip():
            raise ValueError("request_id must not be empty")
        return bool(self._ports.cancel(request_id))

    def runtime_fingerprint(self) -> str:
        value = str(self._ports.fingerprint())
        if not value:
            raise ValueError("Runtime fingerprint must not be empty")
        return value


class OllamaAdapter(FunctionBackendAdapter):
    def __init__(self, ports: BackendPorts) -> None:
        super().__init__(BackendKind.OLLAMA, ports)


class LlamaCppAdapter(FunctionBackendAdapter):
    def __init__(self, ports: BackendPorts) -> None:
        super().__init__(BackendKind.LLAMA_CPP, ports)


def legacy_core_adapter(core: Any, kind: BackendKind | str) -> FunctionBackendAdapter:
    """Wrap current client functions without changing its selected backend."""
    selected = BackendKind(kind)

    def ensure_active() -> None:
        if getattr(core, "ACTIVE_BACKEND", None) != selected.value:
            raise RuntimeError(
                f"Adapter {selected.value} cannot use active backend "
                f"{getattr(core, 'ACTIVE_BACKEND', None)!r}"
            )

    if selected is BackendKind.OLLAMA:
        health_fn = lambda timeout: core.version(timeout) or False
        list_fn = core._ollama_installed_models
        describe_fn = core._ollama_model_show
        caps = BackendCapabilities(True, tools=True, thinking=None, structured_output=True, cancellation=False, telemetry=True)
    else:
        health_fn = lambda timeout: core.llama_health(timeout)
        list_fn = lambda: core.llama_installed_models(False)
        describe_fn = core.llama_model_show
        caps = BackendCapabilities(True, tools=True, thinking=None, structured_output=True, cancellation=False, telemetry=True)

    def generate(request: GenerationRequest):
        ensure_active()
        config = dict(request.options)
        config["model"] = request.model
        return core.stream_chat(
            request.legacy_messages(),
            config,
            show_thinking=True,
            think_override=request.think,
            tools=list(request.tools) or None,
            response_format=dict(request.response_format) if request.response_format else None,
            silent=True,
        )

    def fingerprint() -> str:
        ensure_active()
        return core.backend_runtime_fingerprint()

    ports = BackendPorts(
        health=health_fn,
        list_models=list_fn,
        describe_model=describe_fn,
        generate=generate,
        cancel=lambda _request_id: False,
        fingerprint=fingerprint,
        capabilities=caps,
    )
    return OllamaAdapter(ports) if selected is BackendKind.OLLAMA else LlamaCppAdapter(ports)
