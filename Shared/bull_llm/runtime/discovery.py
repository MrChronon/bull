"""Model discovery service kept separate from menus and terminal rendering."""

from __future__ import annotations

from ..core import BackendAdapter, ModelDescriptor


class ModelDiscoveryService:
    def __init__(self, backend: BackendAdapter) -> None:
        self._backend = backend

    def discover(self) -> tuple[ModelDescriptor, ...]:
        return tuple(sorted(self._backend.list_models(), key=lambda item: item.name.casefold()))

    def describe(self, model_id: str) -> ModelDescriptor:
        return self._backend.describe_model(model_id)
