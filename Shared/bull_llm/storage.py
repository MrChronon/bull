"""Crash-resistant replacement: independent temporary file per writer."""
from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_text(path, encoding="utf-8", newline="\n"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding=encoding, newline=newline) as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_json(path, value):
    with atomic_text(path) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
