"""Backend protocol and BULL Core adapter contracts."""

from __future__ import annotations
from typing import Any,Protocol

from .core import BackendAdapter, BackendCapabilities, BackendKind
from .runtime import LlamaCppAdapter, OllamaAdapter, legacy_core_adapter


class Backend(Protocol):
    name: str

    def health(self,timeout: float=3.0) -> bool: ...
    def models(self) -> list[dict[str,Any]]: ...
    def chat(self,messages: list[dict[str,Any]],options: dict[str,Any]) -> dict[str,Any]: ...
    def unload(self,model: str) -> None: ...
