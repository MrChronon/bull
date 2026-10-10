"""Reap only child processes created by this client, never external LLM servers."""
from __future__ import annotations
import atexit
import threading

_owned = {}
_lock = threading.RLock()


def own(process):
    with _lock:
        _owned[id(process)] = process
    return process


def reap(process):
    if process is None:
        return
    try:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=3)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=3)
        except Exception:
            pass
    for name in ('stdin', 'stdout', 'stderr'):
        stream = getattr(process, name, None)
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass
    with _lock:
        _owned.pop(id(process), None)


def close_all():
    with _lock:
        processes = list(_owned.values())
    for process in processes:
        reap(process)


atexit.register(close_all)
