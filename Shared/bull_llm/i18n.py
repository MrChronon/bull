"""Small runtime localization boundary for BULL UI text only.

Benchmark prompts, scorer inputs and model responses must never pass through
fragment translation. UI modules may use ``localized_print``; model-facing code
should use ``tr`` only for explicit labels and prompts.
"""

from __future__ import annotations

import builtins
import json
import os
from functools import lru_cache
from pathlib import Path


LANGUAGE_DEFAULT = 'en'
LANGUAGE_LABELS = {'en': 'English', 'ru': 'Русский'}
_language = LANGUAGE_DEFAULT
_CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / 'Assets' / 'Localization' / 'ui.en.json'
)


def normalize_language(value):
    raw = str(value or '').strip().casefold().replace('_', '-').split('-', 1)[0]
    return 'ru' if raw in ('ru', 'rus', 'russian', 'русский') else 'en'


def set_language(value):
    global _language
    _language = normalize_language(value)
    return _language


def get_language():
    return _language


@lru_cache(maxsize=1)
def _catalog():
    try:
        document = json.loads(_CATALOG_PATH.read_text(encoding='utf-8'))
        if document.get('schema') != 'bull-ui-catalog' or document.get('version') != 1:
            return {}
        values = document.get('translations')
        if not isinstance(values, dict):
            return {}
        return {
            str(source): str(target)
            for source, target in values.items()
            if source and isinstance(target, str)
        }
    except (OSError, ValueError, TypeError):
        return {}


@lru_cache(maxsize=1)
def _fragments():
    # Never infer fragment substitutions from the ordinary catalog. Generated
    # word and phrase entries once turned unrelated words into strings such as
    # ``runs}``. UI copy is translated by exact message IDs instead. This also
    # makes it impossible for a model response to be altered accidentally.
    return ()


def _has_cyrillic(value):
    return any(('А' <= char <= 'я') or char in 'Ёё' for char in value)


def tr(value, *, fragments=False):
    """Translate a trusted UI value; return non-strings and Russian mode unchanged."""
    if not isinstance(value, str) or _language != 'en' or not _has_cyrillic(value):
        return value
    translated = _catalog().get(value)
    if translated is not None:
        return translated
    if not fragments:
        return value
    result = value
    for source, target in _fragments():
        if source in result:
            result = result.replace(source, target)
    return result


def localized_print(*values, **kwargs):
    """Print trusted UI strings with fragment translation enabled."""
    builtins.print(*(tr(value, fragments=True) for value in values), **kwargs)


def environment_language():
    value = os.environ.get('BULL_UI_LANGUAGE', '').strip()
    return normalize_language(value) if value else None
