"""Data-only author CLI. No inference, downloads or automatic installation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Shared.bull_llm.evaluation.author_workshop import AuthorWorkshop
from Shared.bull_llm.evaluation.catalog import engine_registry_policy
from Shared.bull_llm.evaluation.pack_library import PackLibrary, default_pack_library_root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root", type=Path, help="override the shared Windows library (for isolated tests)")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create a private editable starter")
    create.add_argument("id"); create.add_argument("--language", choices=("en", "ru"), default="en")
    validate = commands.add_parser("validate", help="validate source fields and positive/negative fixtures")
    validate.add_argument("workspace", type=Path)
    build = commands.add_parser("build", help="build an independently installable ZIP without overwriting")
    build.add_argument("workspace", type=Path); build.add_argument("--output", required=True, type=Path)
    duplicate = commands.add_parser("copy", help="copy a workshop-authored installed version")
    duplicate.add_argument("id"); duplicate.add_argument("version"); duplicate.add_argument("new_version")
    args = parser.parse_args(argv)
    try:
        library = PackLibrary(args.library_root or default_pack_library_root(), engine_registry_policy("0.29.0.1"))
        workshop = AuthorWorkshop(library)
        if args.command == "create":
            print(workshop.create_starter(args.id, language=args.language))
        elif args.command == "copy":
            print(workshop.copy_installed(args.id, args.version, args.new_version))
        elif args.command == "build":
            print(workshop.build(args.workspace, args.output))
        else:
            report = workshop.validate(args.workspace)
            print(f"{report['id']}@{report['version']}: {report['case_count']} cases; {report['scored_cases']} scored; {report['manual_cases']} manual")
            for row in report["checks"]:
                print(("PASS" if row["passed"] else "FAIL") + f" {row['case']}/{row['fixture']}: {row['score']:.0%}; failed=" + ",".join(row["failed_checks"]))
            print("Declared machine criteria only; references still require human review.")
            return 0 if report["passed"] else 1
        return 0
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
