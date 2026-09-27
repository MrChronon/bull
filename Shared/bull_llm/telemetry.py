"""Telemetry contracts plus the stable legacy identity helper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Sequence

from .core import TelemetrySnapshot
from .core.fingerprints import stable_fingerprint


@dataclass(frozen=True)
class CallableTelemetryProvider:
    """Adapter for optional hardware providers with explicit capabilities."""

    collector: Callable[[], Mapping[str, float | int | str | bool | None]]
    capability_names: tuple[str, ...] = ()

    def capabilities(self) -> Sequence[str]:
        return self.capability_names

    def snapshot(self) -> TelemetrySnapshot:
        return TelemetrySnapshot(
            collected_at_utc=datetime.now(timezone.utc).isoformat(),
            values=dict(self.collector()),
            capabilities=self.capability_names,
        )


__all__ = ["CallableTelemetryProvider", "TelemetrySnapshot", "stable_fingerprint"]
