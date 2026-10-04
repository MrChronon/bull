"""Load the compatibility core while applications are extracted incrementally."""

from __future__ import annotations
import importlib.util
from pathlib import Path


def load_compat_core():
    root=Path(__file__).resolve().parents[1]
    source=root/'bull_client_v0.28.0.5.py'
    spec=importlib.util.spec_from_file_location('bull_v028_compat',source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load {source}')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
