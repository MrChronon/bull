"""Regression contracts for the BULL data-only benchmark registry."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Shared.bull_llm.evaluation.registry import (
    PackRegistry,
    PackValidationError,
    RegistryPolicy,
    canonical_sha256,
    compile_pack,
    load_pack,
    write_pack_lock,
)


PUBLIC_PACK = ROOT / "BenchmarkPacks" / "bull_chat_core"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _policy(mod) -> RegistryPolicy:
    scorers = {"none"}
    scorers.update(str(row.get("score_type") or "none") for row in mod.builtin_benchmarks().values())
    return RegistryPolicy(
        engine_version="0.25.0.0",
        runner_refs=frozenset({"single_turn_v1"}),
        scorer_refs=frozenset(scorers),
        verifier_refs=frozenset({"benchmark_contract_v1"}),
    )


def _make_pack(
    parent: Path,
    policy: RegistryPolicy,
    *,
    pack_id: str = "private_safe_task",
    version: str = "1.0.0",
    visibility: str = "private",
) -> Path:
    root = parent / (pack_id + "-" + version)
    root.mkdir(parents=True)
    definition = {
        "version": 1,
        "category": "custom",
        "score_type": "none",
        "description": "Safe private task",
        "prompt": "Return exactly OK.",
        "result_instruction": "",
        "num_ctx": 2048,
        "primary_predict": 64,
    }
    cases = [{
        "id": "safe_task",
        "version": 1,
        "category": "custom",
        "runner_ref": "single_turn_v1",
        "scorer_ref": "none",
        "verifier_ref": "benchmark_contract_v1",
        "definition": definition,
    }]
    gold = {
        "schema": "bull-benchmark-pack-gold",
        "schema_version": 1,
        "cases": [{
            "id": "safe_task",
            "version": 1,
            "definition_sha256": canonical_sha256(definition),
            "prompt_sha256": _text_hash(definition["prompt"]),
            "result_instruction_sha256": _text_hash(""),
        }],
    }
    manifest = {
        "schema": "bull-benchmark-pack-manifest",
        "schema_version": 1,
        "id": pack_id,
        "version": version,
        "title": "Private safe task",
        "description": "Fixture demonstrating a task added without editing the client.",
        "status": "experimental",
        "visibility": visibility,
        "engine": {"minimum_version": "0.25.0.0"},
        "license": {"id": "LicenseRef-Test", "name": "Test notice", "file": "LICENSE.txt"},
        "provenance": {"source": "registry regression fixture"},
        "taxonomy": ["custom"],
        "content": {"cases_file": "cases.json", "sha256": canonical_sha256(cases), "case_count": 1},
        "gold": {"file": "gold.json", "sha256": canonical_sha256(gold)},
        "documentation": "README.md",
    }
    _write(root / "cases.json", cases)
    _write(root / "gold.json", gold)
    _write(root / "manifest.json", manifest)
    (root / "LICENSE.txt").write_text("fixture\n", encoding="utf-8")
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    write_pack_lock(root, policy, visibility)
    return root


def _expect(code: str, action) -> None:
    try:
        action()
    except PackValidationError as error:
        assert error.code == code, (error.code, str(error))
    else:
        raise AssertionError(f"expected {code}")


def run_suite(mod) -> int:
    policy = _policy(mod)
    checks = []

    def check(name, fn):
        fn()
        checks.append(name)
        print("OK  Registry " + name)

    def public_pack_is_exact():
        pack = load_pack(PUBLIC_PACK, policy, "public")
        assert pack.id == "bull_chat_core" and pack.status.value == "stable"
        expected = {name: mod.builtin_benchmarks()[name] for name in mod.CHAT_CORE_TESTS}
        assert pack.legacy_definitions() == expected
        assert len(pack.cases) == len(mod.CHAT_CORE_TESTS) == 12
        summary = json.dumps(pack.inspect_summary(), ensure_ascii=False)
        assert '"prompt"' not in summary and '"definition"' not in summary
        client_source = (ROOT / "bull_client_v0.25.0.0.py").read_text(encoding="utf-8")
        for command in ("/bench pack list", "/bench pack validate", "/bench pack inspect"):
            assert command in client_source

    check("CHAT Core exact extraction", public_pack_is_exact)

    with tempfile.TemporaryDirectory(prefix="bull-registry-") as temporary:
        root = Path(temporary)

        def private_task_without_client_edit():
            private_root = root / "private"
            pack_root = _make_pack(private_root, policy)
            registry = PackRegistry([], [private_root], policy)
            packs = registry.discover()
            assert [pack.id for pack in packs] == ["private_safe_task"]
            assert packs[0].cases[0].definition["prompt"] == "Return exactly OK."
            assert pack_root.is_dir()

        check("private data-only task discovery", private_task_without_client_edit)

        def duplicate_identity_rejected():
            left = root / "duplicate-left"
            right = root / "duplicate-right"
            _make_pack(left, policy, visibility="private")
            _make_pack(right, policy, visibility="private")
            _expect("DUPLICATE_PACK_ID", lambda: PackRegistry([], [left, right], policy).discover())

        check("duplicate pack identity rejected", duplicate_identity_rejected)

        mutation_root = root / "mutations"
        mutation_root.mkdir()

        def fresh(name: str) -> Path:
            target = mutation_root / name
            shutil.copytree(PUBLIC_PACK, target)
            return target

        def incompatible_engine():
            pack = fresh("engine")
            manifest = _json(pack / "manifest.json")
            manifest["engine"]["minimum_version"] = "99.0.0"
            _write(pack / "manifest.json", manifest)
            _expect("INCOMPATIBLE_ENGINE", lambda: load_pack(pack, policy, "public"))

        check("incompatible engine rejected", incompatible_engine)

        def unknown_runner():
            pack = fresh("runner")
            cases = _json(pack / "cases.json")
            cases[0]["runner_ref"] = "load_arbitrary_python"
            _write(pack / "cases.json", cases)
            manifest = _json(pack / "manifest.json")
            manifest["content"]["sha256"] = canonical_sha256(cases)
            _write(pack / "manifest.json", manifest)
            _expect("UNKNOWN_RUNNER", lambda: load_pack(pack, policy, "public"))

        check("unknown runner rejected", unknown_runner)

        def unknown_scorer():
            pack = fresh("scorer")
            cases = _json(pack / "cases.json")
            cases[0]["scorer_ref"] = "unknown_scorer"
            cases[0]["definition"]["score_type"] = "unknown_scorer"
            _write(pack / "cases.json", cases)
            manifest = _json(pack / "manifest.json")
            manifest["content"]["sha256"] = canonical_sha256(cases)
            _write(pack / "manifest.json", manifest)
            _expect("UNKNOWN_SCORER", lambda: load_pack(pack, policy, "public"))

        check("unknown scorer rejected", unknown_scorer)

        def broken_hash():
            pack = fresh("hash")
            cases = _json(pack / "cases.json")
            cases[0]["definition"]["description"] += " changed"
            _write(pack / "cases.json", cases)
            _expect("CONTENT_HASH_MISMATCH", lambda: load_pack(pack, policy, "public"))

        check("broken content hash rejected", broken_hash)

        def missing_license():
            pack = fresh("license")
            (pack / "LICENSE.txt").unlink()
            _expect("LICENSE_FILE_MISSING", lambda: load_pack(pack, policy, "public"))

        check("missing license rejected", missing_license)

        def path_traversal():
            pack = fresh("traversal")
            manifest = _json(pack / "manifest.json")
            manifest["content"]["cases_file"] = "../cases.json"
            _write(pack / "manifest.json", manifest)
            _expect("PATH_TRAVERSAL", lambda: load_pack(pack, policy, "public"))

        check("path traversal rejected", path_traversal)

        def incompatible_case_version():
            pack = fresh("case-version")
            cases = _json(pack / "cases.json")
            cases[0]["version"] += 1
            _write(pack / "cases.json", cases)
            manifest = _json(pack / "manifest.json")
            manifest["content"]["sha256"] = canonical_sha256(cases)
            _write(pack / "manifest.json", manifest)
            _expect("INCOMPATIBLE_CASE_VERSION", lambda: load_pack(pack, policy, "public"))

        check("incompatible case version rejected", incompatible_case_version)

        def executable_content():
            pack = fresh("executable")
            (pack / "hook.py").write_text("raise SystemExit\n", encoding="utf-8")
            _expect("EXECUTABLE_CONTENT_FORBIDDEN", lambda: load_pack(pack, policy, "public"))

        check("executable pack content rejected", executable_content)

        def deterministic_generator():
            pack = _make_pack(root / "generated", policy, pack_id="generated_pack")
            manifest = _json(pack / "manifest.json")
            template = _json(pack / "cases.json")[0]
            template["id"] = "case_{{tone}}"
            template["definition"]["prompt"] = "Tone={{tone}}"
            generated = []
            for tone in ("formal", "plain"):
                row = copy.deepcopy(template)
                row["id"] = row["id"].replace("{{tone}}", tone)
                row["definition"]["prompt"] = row["definition"]["prompt"].replace("{{tone}}", tone)
                generated.append(row)
            generated.sort(key=lambda row: (row["id"], row["version"]))
            gold = {
                "schema": "bull-benchmark-pack-gold",
                "schema_version": 1,
                "cases": [{
                    "id": row["id"],
                    "version": row["version"],
                    "definition_sha256": canonical_sha256(row["definition"]),
                    "prompt_sha256": _text_hash(row["definition"]["prompt"]),
                    "result_instruction_sha256": _text_hash(""),
                } for row in generated],
            }
            manifest["content"] = {
                "generator": {
                    "type": "cartesian_v1",
                    "version": 1,
                    "template_case": template,
                    "variables": {"tone": ["formal", "plain"]},
                },
                "sha256": canonical_sha256(generated),
                "case_count": 2,
            }
            manifest["gold"]["sha256"] = canonical_sha256(gold)
            _write(pack / "gold.json", gold)
            _write(pack / "manifest.json", manifest)
            write_pack_lock(pack, policy, "private")
            assert compile_pack(pack, policy, "private") == compile_pack(pack, policy, "private")
            assert [case.id for case in load_pack(pack, policy, "private").cases] == ["case_formal", "case_plain"]

        check("generator output deterministic", deterministic_generator)

    return len(checks)


if __name__ == "__main__":
    import importlib.util

    spec = importlib.util.spec_from_file_location("bull_registry_test_core", ROOT / "bull_client_v0.25.0.0.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load compatibility core")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    count = run_suite(core)
    print(f"PASS {count}/{count}")
