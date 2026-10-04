"""Dedicated BULL working Client entry point for v0.28.0.5."""

from __future__ import annotations
import os

from _bootstrap import load_compat_core


def main():
    os.environ['BULL_START_SURFACE']='home'
    return load_compat_core().main()


if __name__=='__main__':
    raise SystemExit(main())
