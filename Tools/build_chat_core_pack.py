"""Rebuild the public CHAT Core benchmark pack without changing its cases."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "Tests" / "Fixtures" / "engine_boundary_gold.json"
PACK_ROOT = ROOT / "BenchmarkPacks" / "bull_chat_core"


def _load_source():
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    if source.get("schema") != "bull-engine-boundary-gold" or source.get("schema_version") != 1:
        raise ValueError("Unsupported frozen CHAT source")
    return source


def _write_json(path: Path, value) -> None:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    path.write_text(payload, encoding="utf-8", newline="\n")


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from Shared.bull_llm.evaluation.registry import (
        canonical_sha256,
        write_pack_lock,
    )
    from Shared.bull_llm.evaluation.catalog import engine_registry_policy

    source = _load_source()
    builtins = source["definitions"]
    selected = tuple(source["chat_core_tests"])
    cases = []
    for case_id in selected:
        definition = builtins[case_id]
        if canonical_sha256(definition) != source["fingerprints"][case_id]["definition_sha256"]:
            raise ValueError("Frozen CHAT source changed: " + case_id)
        cases.append({
            "id": case_id,
            "version": int(definition["version"]),
            "category": definition["category"],
            "runner_ref": "single_turn_v1",
            "scorer_ref": definition.get("score_type", "none"),
            "verifier_ref": "benchmark_contract_v1",
            "definition": definition,
        })

    cases.sort(key=lambda row: (row["id"], row["version"]))
    gold = {
        "schema": "bull-benchmark-pack-gold",
        "schema_version": 1,
        "cases": [
            {
                "id": row["id"],
                "version": row["version"],
                "definition_sha256": canonical_sha256(row["definition"]),
                "prompt_sha256": _text_sha256(str(row["definition"].get("prompt") or "")),
                "result_instruction_sha256": _text_sha256(
                    str(row["definition"].get("result_instruction") or "")
                ),
            }
            for row in cases
        ],
    }
    taxonomy = sorted({row["category"] for row in cases})
    manifest = {
        "schema": "bull-benchmark-pack-manifest",
        "schema_version": 1,
        "id": "bull_chat_core",
        "version": "1.0.0",
        "title": "BULL CHAT Core",
        "description": "Frozen CHAT quality suite migrated without prompt or scorer changes.",
        "status": "stable",
        "visibility": "public",
        "engine": {"minimum_version": "0.24.0.0"},
        "license": {
            "id": "LicenseRef-BULL-Project-Notice",
            "name": "BULL project benchmark notice",
            "file": "LICENSE.txt",
        },
        "provenance": {
            "source": "BULL builtin_benchmarks/CHAT_CORE_TESTS",
            "migration": "data-only extraction",
            "prompts_changed": False,
            "scorers_changed": False,
        },
        "taxonomy": taxonomy,
        "content": {
            "cases_file": "cases.json",
            "sha256": canonical_sha256(cases),
            "case_count": len(cases),
        },
        "gold": {"file": "gold.json", "sha256": canonical_sha256(gold)},
        "documentation": "README.md",
    }

    PACK_ROOT.mkdir(parents=True, exist_ok=True)
    _write_json(PACK_ROOT / "cases.json", cases)
    _write_json(PACK_ROOT / "gold.json", gold)
    _write_json(PACK_ROOT / "manifest.json", manifest)
    (PACK_ROOT / "LICENSE.txt").write_text(
        "BULL project benchmark notice\n\n"
        "This benchmark pack is part of the BULL project. No separate license grant "
        "is created by this metadata file; use is governed by the license and notices "
        "of the repository that distributes the pack.\n",
        encoding="utf-8",
        newline="\n",
    )
    (PACK_ROOT / "README.md").write_text(
        "# BULL CHAT Core 1.0.0\n\n"
        "This stable public pack is the data-only extraction of the CHAT Core. "
        "Prompts, result instructions, scorer IDs and case definitions are byte-for-byte "
        "equivalent after canonical JSON serialization. `gold.json` freezes their hashes.\n\n"
        "The pack contains no executable code. Runner, scorer and verifier references are "
        "resolved only through BULL's engine-owned allowlists.\n",
        encoding="utf-8",
        newline="\n",
    )
    policy = engine_registry_policy("0.24.0.0")
    write_pack_lock(PACK_ROOT, policy, "public")
    print(f"Built {PACK_ROOT} ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
