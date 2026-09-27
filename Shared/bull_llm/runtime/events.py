"""Inference event collection primitives with no terminal dependency."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core import InferenceEvent


def discard_event(_event: InferenceEvent) -> None:
    return None


@dataclass
class CollectingEventSink:
    events: list[InferenceEvent] = field(default_factory=list)

    def __call__(self, event: InferenceEvent) -> None:
        self.events.append(event)
