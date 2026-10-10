"""Private immutable task snapshots and an allowlisted public coverage summary.

No filesystem lookup, import from a pack, model call or newest-version fallback.
Checksums detect accidental changes, not malicious authors or forged consent.
"""
from __future__ import annotations

import json
from copy import deepcopy

from .catalog import EXECUTABLE_SCORER_REFS
from .registry import (COMPILED_SCHEMA, COMPILED_SCHEMA_VERSION, PackValidationError,
                       _validate_cases, _version_compare, canonical_sha256)

SNAPSHOT_SCHEMA = "bull-pack-run-snapshot"
MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024


def _invalid(message):
    raise PackValidationError("PACK_SNAPSHOT_INVALID", message)


def _bounded(value, limit):
    try:
        payload = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise PackValidationError("PACK_SNAPSHOT_INVALID", "snapshot must be finite bounded JSON") from error
    if len(payload) > limit:
        _invalid("snapshot exceeds the documented JSON budget")


def capture_snapshot(pack, selection, policy):
    compiled = {
        "schema": COMPILED_SCHEMA, "schema_version": COMPILED_SCHEMA_VERSION,
        "pack": {"id": pack.id, "version": pack.version}, "manifest_sha256": pack.manifest_sha256,
        "cases": [{"id": c.id, "version": c.version, "category": c.category,
                   "runner_ref": c.runner_ref, "scorer_ref": c.scorer_ref, "verifier_ref": c.verifier_ref,
                   "definition": deepcopy(dict(c.definition))} for c in pack.cases],
    }
    snapshot = {"schema": SNAPSHOT_SCHEMA, "schema_version": 1,
                "engine_version": policy.engine_version, "selection": deepcopy(selection),
                "manifest": deepcopy(dict(pack.manifest)), "compiled": compiled}
    snapshot["snapshot_sha256"] = canonical_sha256(snapshot)
    snapshot_catalog(snapshot, selection, policy)
    return snapshot


def snapshot_catalog(snapshot, selection, policy):
    _bounded(snapshot, MAX_SNAPSHOT_BYTES)
    if (not isinstance(snapshot, dict) or set(snapshot) != {
            "schema", "schema_version", "engine_version", "selection", "manifest", "compiled", "snapshot_sha256"} or
            snapshot.get("schema") != SNAPSHOT_SCHEMA or type(snapshot.get("schema_version")) is not int or
            snapshot["schema_version"] != 1 or not isinstance(snapshot["engine_version"], str)):
        _invalid("unsupported task snapshot schema")
    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if canonical_sha256(body) != snapshot["snapshot_sha256"]:
        _invalid("task snapshot checksum changed")
    if not isinstance(selection, dict):
        _invalid("missing exact selection")
    # Always recheck engine-code capabilities, even when the outer digest was
    # regenerated. Consent must never be inferred from a scorer declaration.
    approved = selection.get("approved_code_cases")
    compiled = snapshot["compiled"]
    if (not isinstance(compiled, dict) or set(compiled) != {
            "schema", "schema_version", "pack", "manifest_sha256", "cases"} or
            compiled["schema"] != COMPILED_SCHEMA or compiled["schema_version"] != COMPILED_SCHEMA_VERSION):
        _invalid("unsupported compiled content")
    manifest = snapshot["manifest"]
    _bounded(compiled, policy.max_json_bytes)
    _bounded(manifest, policy.max_json_bytes)
    if not isinstance(manifest, dict) or canonical_sha256(manifest) != selection.get("manifest_sha256"):
        _invalid("manifest differs from the selected immutable version")
    if (canonical_sha256(compiled) != selection.get("compiled_sha256") or
            compiled["manifest_sha256"] != selection.get("manifest_sha256") or
            compiled["pack"] != {"id": selection.get("id"), "version": selection.get("version")} or
            manifest.get("id") != selection.get("id") or manifest.get("version") != selection.get("version")):
        _invalid("compiled content differs from the selected immutable version")
    engine = manifest.get("engine") or {}
    if (_version_compare(policy.engine_version, engine.get("minimum_version", "")) < 0 or
            (engine.get("maximum_version") and _version_compare(policy.engine_version, engine["maximum_version"]) > 0)):
        raise PackValidationError("INCOMPATIBLE_ENGINE", "captured pack requires a different engine")
    cases = _validate_cases(compiled["cases"], manifest, policy)
    definitions = {}
    for case in cases:
        if case.id in definitions:
            _invalid("ambiguous case identity")
        definitions[case.id] = {**deepcopy(dict(case.definition)), "_pack": {
            "identity": f"{manifest['id']}@{manifest['version']}",
            "manifest_sha256": selection["manifest_sha256"], "compiled_sha256": selection["compiled_sha256"],
            "definition_sha256": case.definition_sha256, "runner_ref": case.runner_ref,
            "scorer_ref": case.scorer_ref, "verifier_ref": case.verifier_ref}}
    ids = selection.get("case_ids")
    if (not isinstance(ids, list) or not ids or any(not isinstance(x, str) or x not in definitions for x in ids) or
            len(ids) != len(set(ids))):
        _invalid("captured selection must contain distinct cases from the captured pack")
    code_cases = [x for x in ids if definitions[x]["_pack"]["scorer_ref"] in EXECUTABLE_SCORER_REFS]
    if code_cases and (selection.get("code_execution_approved") is not True or not isinstance(approved, list) or
                       any(x not in approved for x in code_cases)):
        raise PackValidationError("PACK_CODE_PERMISSION_REQUIRED", "captured engine code checks require explicit consent")
    if selection != snapshot["selection"]:
        _invalid("checkpoint selection changed after capture")
    full = set(ids) == set(definitions)
    if (type(selection.get("total_cases")) is not int or selection["total_cases"] != len(cases) or
            type(selection.get("selected_cases")) is not int or selection["selected_cases"] != len(ids) or
            selection.get("coverage") != ("full_pack" if full else "subset") or
            selection.get("identity") != f"{manifest['id']}@{manifest['version']}"):
        _invalid("captured coverage is inconsistent")
    return {x: definitions[x] for x in ids}


def public_scope(snapshot):
    """No author text, titles, paths, prompts, sources or expected answers."""
    selection = snapshot["selection"]
    return {key: deepcopy(selection[key]) for key in (
        "id", "version", "identity", "manifest_sha256", "compiled_sha256",
        "total_cases", "selected_cases", "coverage", "reason")} | {
            "snapshot_sha256": snapshot["snapshot_sha256"], "engine_version": snapshot["engine_version"]}
