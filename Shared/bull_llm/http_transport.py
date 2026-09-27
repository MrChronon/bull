"""Bounded HTTP bodies shared by Client and Benchmark Lab (stdlib only)."""
from __future__ import annotations

import json
import math
import socket
import threading
import time
import urllib.error
import urllib.request

MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_STREAM_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Backend redirect blocked; use the final endpoint", headers, fp)


class BoundedResponse:
    """Own the response and interrupt body reads at a monotonic deadline.

    urllib's connection/header phase still uses its socket idle timeout. Once
    headers arrive, their elapsed time is subtracted from the body deadline.
    """
    def __init__(self, response, deadline, max_bytes=MAX_STREAM_BYTES):
        self.response, self.deadline, self.max_bytes = response, deadline, max_bytes
        self.received = 0
        self.expired = threading.Event()
        self.timer = threading.Timer(max(0, deadline - time.monotonic()), self._abort)
        self.timer.daemon = True
        self.timer.start()

    def _abort(self):
        self.expired.set()
        sock = getattr(getattr(getattr(self.response, "fp", None), "raw", None), "_sock", None)
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        # Do not call buffered close here: it can wait on a blocked reader's lock.

    def _read(self, method, limit):
        if self.expired.is_set() or time.monotonic() >= self.deadline:
            raise TimeoutError("Backend response deadline exceeded")
        try:
            data = method(limit)
        except (OSError, ValueError) as exc:
            if self.expired.is_set():
                raise TimeoutError("Backend response deadline exceeded") from exc
            raise
        if self.expired.is_set() or time.monotonic() >= self.deadline:
            raise TimeoutError("Backend response deadline exceeded")
        self.received += len(data)
        if self.received > self.max_bytes:
            raise ValueError("Backend response exceeds byte limit")
        return data

    def read(self, size=-1):
        limit = MAX_JSON_BYTES if size < 0 else min(size, MAX_JSON_BYTES)
        data = self._read(self.response.read, limit + 1)
        if len(data) > limit:
            raise ValueError("Backend JSON exceeds byte limit")
        return data

    def __iter__(self):
        while True:
            data = self._read(self.response.readline, MAX_LINE_BYTES + 1)
            if len(data) > MAX_LINE_BYTES:
                raise ValueError("Backend stream line exceeds byte limit")
            if not data:
                return
            yield data

    def close(self):
        self.timer.cancel()
        self.response.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open_response(opener, request, timeout):
    deadline = time.monotonic() + timeout
    response = opener.open(request, timeout=timeout)
    return BoundedResponse(response, deadline)


def decode_object(raw):
    def invalid_constant(value):
        raise ValueError("Non-finite backend JSON number")
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            invalid_constant(value)
        return number
    try:
        data = json.loads(raw, parse_constant=invalid_constant, parse_float=finite_float)
    except RecursionError as exc:
        raise ValueError("Backend JSON nesting limit exceeded") from exc
    if not isinstance(data, dict):
        raise ValueError("Backend JSON must be an object")
    return data


def json_object(response):
    return decode_object(response.read().decode("utf-8"))
