"""Dedicated BULL Agent Lab entry point."""
import os
from _bootstrap import load_compat_core


def main():
    os.environ["BULL_START_SURFACE"] = "agent"
    return load_compat_core().main()


if __name__ == "__main__":
    raise SystemExit(main())
