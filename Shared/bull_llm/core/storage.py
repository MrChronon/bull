"""Bounded, atomic artifact storage independent of benchmark orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

from .contracts import ArtifactClassification


class AtomicArtifactStore:
    def __init__(self, root: str | Path, *, max_json_bytes: int = 64 * 1024 * 1024) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        if max_json_bytes <= 0:
            raise ValueError("max_json_bytes must be positive")
        self._max_json_bytes = max_json_bytes

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, relative_path: str | Path) -> Path:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Artifact path must remain inside store root")
        target = (self._root / relative).resolve()
        if target != self._root and self._root not in target.parents:
            raise ValueError("Artifact path escapes store root")
        return target

    def write_json(
        self,
        relative_path: str | Path,
        value: Any,
        classification: ArtifactClassification,
    ) -> Path:
        target = self._resolve(relative_path)
        if target.suffix.casefold() != ".json":
            raise ValueError("JSON artifact must use .json suffix")
        payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
        if len(payload) > self._max_json_bytes:
            raise ValueError("Artifact exceeds configured JSON size limit")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target)
            marker = target.with_suffix(target.suffix + ".classification")
            marker.write_text(classification.value + "\n", encoding="ascii")
        finally:
            temp.unlink(missing_ok=True)
        return target

    def read_json(self, relative_path: str | Path) -> Any:
        target = self._resolve(relative_path)
        if target.stat().st_size > self._max_json_bytes:
            raise ValueError("Artifact exceeds configured JSON size limit")
        with target.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def sha256(self, relative_path: str | Path) -> str:
        target = self._resolve(relative_path)
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
