"""Report renderers consume precomputed summaries and never rescore results."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .core import ArtifactClassification, ArtifactStore


class JsonReportRenderer:
    def __init__(self, classification: ArtifactClassification = ArtifactClassification.SHARE_SAFE) -> None:
        self._classification = classification

    def render(self, summary: Mapping[str, Any], store: ArtifactStore, relative_path: str | Path) -> Path:
        document = {
            "schema": "bull-report",
            "schema_version": 1,
            "summary": dict(summary),
        }
        return store.write_json(relative_path, document, self._classification)
