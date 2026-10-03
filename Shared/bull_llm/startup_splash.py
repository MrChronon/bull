"""Versioned, pre-rendered terminal splash screens.

The runtime never invokes an image viewer or a renderer such as Chafa.  Release
assets are converted at build time to a bounded ANSI art file; this keeps the
startup path offline, portable and safe for an ordinary Windows terminal.
"""

from __future__ import annotations

import base64
from pathlib import Path
import re


_ASSET_DIR = Path(__file__).resolve().parents[2] / 'Assets' / 'Brand'
_SGR_ESCAPE_RE = re.compile(r'\x1b\[[0-9;:]*m')
_CURSOR_ESCAPE_RE = re.compile(r'\x1b\[\?25[hl]')


def splash_asset_path(version: str) -> Path:
    """Return the exact versioned splash asset, without accepting a path."""
    safe = re.sub(r'[^A-Za-z0-9._-]', '', str(version or ''))
    return _ASSET_DIR / f'splash-{safe}.ansi.b64'


def load_splash(version: str) -> str | None:
    """Load only bounded colour SGR sequences from a build-time asset."""
    path = splash_asset_path(version)
    try:
        encoded = ''.join(path.read_text(encoding='ascii').split())
        if not encoded or len(encoded) > 160_000:
            return None
        rendered = _CURSOR_ESCAPE_RE.sub('', base64.b64decode(encoded, validate=True).decode('utf-8'))
    except (OSError, ValueError, UnicodeError):
        return None

    plain = _SGR_ESCAPE_RE.sub('', rendered)
    if '\x1b' in plain or any(ord(char) < 32 and char not in '\r\n' for char in plain):
        return None
    rows = plain.splitlines()
    if not 12 <= len(rows) <= 34 or any(len(row) > 64 for row in rows):
        return None
    return rendered


def progress_bar(current: int, total: int, width: int = 28) -> str:
    """Produce a fixed-width, non-deceptive stage progress bar."""
    total = max(1, int(total))
    current = min(total, max(0, int(current)))
    filled = round(width * current / total)
    return '[' + ('#' * filled) + ('-' * (width - filled)) + f'] {current}/{total}'


def render(core, version: str, stage: str, current: int, total: int) -> bool:
    """Render the static art and the current startup-gate stage.

    ``current`` reports completed startup stages, not individual regression
    tests.  The external regression runner intentionally remains captured, so
    the UI never invents per-test progress that it cannot observe.
    """
    core.clear_console()
    rendered = load_splash(version)
    if rendered is not None:
        print(rendered, end='' if rendered.endswith('\n') else '\n')
    else:
        core.white()
        print('BULL — Benchmarking & Usage of Local LLMs')
        print()
    core.white()
    print(f' BULL {version}  |  Local LLM Benchmark Lab')
    core.gray()
    print(f' {progress_bar(current, total)}  {stage}')
    core.white()
    return rendered is not None
