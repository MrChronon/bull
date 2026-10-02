"""Dedicated BULL Benchmark Lab entry point for v0.27.0.0."""

from __future__ import annotations
import os

from _bootstrap import load_compat_core


def main():
    os.environ['BULL_START_SURFACE']='benchmark'
    return load_compat_core().main()


if __name__=='__main__':
    raise SystemExit(main())
