"""Crash-resistant replacement: independent temporary file per writer."""
from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_text(path, encoding="utf-8", newline="\n", *, preserve_failed=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    retained = False
    try:
        with temp.open("x", encoding=encoding, newline=newline) as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        # Readers (including virus scanners) may briefly deny replacement on Windows.
        # Never truncate the previous file or regenerate the already durable payload.
        delays = (0.05, 0.1, 0.2, 0.4, 0.8)
        for attempt in range(len(delays) + 1):
            try:
                os.replace(temp, path)
                break
            except OSError as error:
                if getattr(error, 'winerror', None) in (5, 32, 33) and attempt < len(delays):
                    time.sleep(delays[attempt])
                    continue
                if preserve_failed:
                    retained = True
                    error.recovery_path = str(temp)
                raise
    finally:
        if not retained:
            temp.unlink(missing_ok=True)


def atomic_json(path, value, *, preserve_failed=False):
    with atomic_text(path, preserve_failed=preserve_failed) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
