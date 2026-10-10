"""Data-only, versioned benchmark pack registry for BULL.

Packs contain JSON and documentation only. They may reference engine-owned
runner/scorer/verifier IDs, but they cannot load code or name import paths.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import re
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..core.fingerprints import canonical_json


MANIFEST_SCHEMA = "bull-benchmark-pack-manifest"
MANIFEST_SCHEMA_VERSION = 1
LOCK_SCHEMA = "bull-benchmark-pack-lock"
LOCK_SCHEMA_VERSION = 1
COMPILED_SCHEMA = "bull-compiled-benchmark-pack"
COMPILED_SCHEMA_VERSION = 1
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_CASES = 1000
MAX_PROMPT_CHARS = 200_000
PACK_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
REF_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
VERSION_RE = re.compile(r"^\d+(?:\.\d+){2,3}$")
CASE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,95}$")
FORBIDDEN_EXECUTABLE_SUFFIXES = {
    ".py", ".pyc", ".pyo", ".ps1", ".cmd", ".bat", ".com", ".exe",
    ".dll", ".js", ".mjs", ".cjs", ".vbs", ".sh", ".so", ".dylib",
}


class PackStatus(str, Enum):
    EXPERIMENTAL = "experimental"
    CANDIDATE = "candidate"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class PackVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class PackValidationError(ValueError):
    def __init__(self, code: str, message: str, path: str | Path | None = None) -> None:
        self.code = code
        self.path = Path(path) if path is not None else None
        suffix = f" [{self.path}]" if self.path is not None else ""
        super().__init__(f"{code}: {message}{suffix}")


@dataclass(frozen=True)
class RegistryPolicy:
    engine_version: str
    runner_refs: frozenset[str]
    scorer_refs: frozenset[str]
    verifier_refs: frozenset[str]
    max_json_bytes: int = MAX_JSON_BYTES
    max_cases: int = MAX_CASES

    def __post_init__(self) -> None:
        _version_tuple(self.engine_version, "engine_version")
        if self.max_json_bytes <= 0 or self.max_cases <= 0:
            raise ValueError("Registry limits must be positive")


@dataclass(frozen=True)
class PackCase:
    id: str
    version: int
    category: str
    runner_ref: str
    scorer_ref: str
    verifier_ref: str | None
    definition: Mapping[str, Any]
    definition_sha256: str


@dataclass(frozen=True)
class LoadedPack:
    root: Path
    id: str
    version: str
    title: str
    status: PackStatus
    visibility: PackVisibility
    manifest: Mapping[str, Any]
    cases: tuple[PackCase, ...]
    manifest_sha256: str
    compiled_sha256: str
    source_kind: str

    @property
    def identity(self) -> str:
        return f"{self.id}@{self.version}"

    @property
    def runnable(self) -> bool:
        return self.status is not PackStatus.RETIRED

    def legacy_definitions(self) -> dict[str, dict[str, Any]]:
        return {case.id: copy.deepcopy(dict(case.definition)) for case in self.cases}

    def inspect_summary(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "title": self.title,
            "status": self.status.value,
            "visibility": self.visibility.value,
            "source_kind": self.source_kind,
            "minimum_engine_version": self.manifest["engine"]["minimum_version"],
            "runner_refs": sorted({case.runner_ref for case in self.cases}),
            "scorer_refs": sorted({case.scorer_ref for case in self.cases}),
            "verifier_refs": sorted({case.verifier_ref for case in self.cases if case.verifier_ref}),
            "case_count": len(self.cases),
            "cases": [
                {
                    "id": case.id,
                    "version": case.version,
                    "category": case.category,
                    "runner_ref": case.runner_ref,
                    "scorer_ref": case.scorer_ref,
                    "verifier_ref": case.verifier_ref,
                    "definition_sha256": case.definition_sha256,
                }
                for case in self.cases
            ],
            "manifest_sha256": self.manifest_sha256,
            "compiled_sha256": self.compiled_sha256,
        }


@dataclass(frozen=True)
class RegistryFinding:
    path: Path
    source_kind: str
    pack: LoadedPack | None = None
    error_code: str | None = None
    error_message: str | None = None


def _version_tuple(value: str, field: str) -> tuple[int, ...]:
    text = str(value or "").strip().lstrip("v")
    if not VERSION_RE.fullmatch(text):
        raise PackValidationError("INVALID_VERSION", f"{field} must be numeric dotted version")
    return tuple(int(part) for part in text.split("."))


def _version_compare(left: str, right: str) -> int:
    a = _version_tuple(left, "version")
    b = _version_tuple(right, "version")
    width = max(len(a), len(b))
    a += (0,) * (width - len(a))
    b += (0,) * (width - len(b))
    return (a > b) - (a < b)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PackValidationError("DUPLICATE_JSON_KEY", f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise PackValidationError("NONFINITE_JSON", f"non-finite JSON constant {value}")


def _load_json(path: Path, limit: int) -> Any:
    if not path.is_file() or path.is_symlink():
        raise PackValidationError("MISSING_FILE", "required regular file is missing", path)
    size = path.stat().st_size
    if size > limit:
        raise PackValidationError("FILE_TOO_LARGE", f"JSON exceeds {limit} bytes", path)
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as error:
        raise PackValidationError("INVALID_UTF8", str(error), path) from error
    except json.JSONDecodeError as error:
        raise PackValidationError("INVALID_JSON", str(error), path) from error


def _safe_relative(root: Path, value: Any, field: str) -> Path:
    text = str(value or "").strip()
    if not text:
        raise PackValidationError("MISSING_PATH", f"{field} is required", root)
    relative = Path(text)
    if relative.is_absolute() or ".." in relative.parts:
        raise PackValidationError("PATH_TRAVERSAL", f"unsafe {field}: {text}", root)
    target = (root / relative).resolve()
    resolved_root = root.resolve()
    if target != resolved_root and resolved_root not in target.parents:
        raise PackValidationError("PATH_TRAVERSAL", f"unsafe {field}: {text}", root)
    return target


def _require_text(row: Mapping[str, Any], field: str, *, pattern: re.Pattern[str] | None = None) -> str:
    value = str(row.get(field) or "").strip()
    if not value:
        raise PackValidationError("MISSING_FIELD", f"{field} is required")
    if pattern is not None and not pattern.fullmatch(value):
        raise PackValidationError("INVALID_FIELD", f"invalid {field}: {value!r}")
    return value


def _scan_no_executable_files(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            raise PackValidationError("PACK_LINK_FORBIDDEN", "links are not allowed in packs", path)
        if path.is_file() and path.suffix.casefold() in FORBIDDEN_EXECUTABLE_SUFFIXES:
            raise PackValidationError("EXECUTABLE_CONTENT_FORBIDDEN", "pack contains executable content", path)


def _replace_template(value: Any, values: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        result = value
        for key, replacement in values.items():
            result = result.replace("{{" + key + "}}", str(replacement))
        return result
    if isinstance(value, list):
        return [_replace_template(item, values) for item in value]
    if isinstance(value, dict):
        return {key: _replace_template(item, values) for key, item in value.items()}
    return value


def _generate_cases(generator: Mapping[str, Any], policy: RegistryPolicy) -> list[dict[str, Any]]:
    if set(generator) - {"type", "version", "template_case", "variables"}:
        raise PackValidationError("GENERATOR_FIELD_UNKNOWN", "generator contains unknown fields")
    if generator.get("type") != "cartesian_v1" or generator.get("version") != 1:
        raise PackValidationError("UNKNOWN_GENERATOR", "only cartesian_v1 version 1 is allowed")
    template = generator.get("template_case")
    variables = generator.get("variables")
    if not isinstance(template, dict) or not isinstance(variables, dict) or not variables:
        raise PackValidationError("INVALID_GENERATOR", "generator needs template_case and variables")
    names = sorted(variables)
    value_lists: list[list[Any]] = []
    for name in names:
        if not REF_RE.fullmatch(str(name)):
            raise PackValidationError("INVALID_GENERATOR", f"invalid variable name: {name}")
        values = variables[name]
        if not isinstance(values, list) or not values:
            raise PackValidationError("INVALID_GENERATOR", f"variable {name} must be a non-empty list")
        value_lists.append(values)
    count = 1
    for values in value_lists:
        count *= len(values)
    if count > policy.max_cases:
        raise PackValidationError("TOO_MANY_CASES", f"generator expands to {count} cases")
    return [
        _replace_template(copy.deepcopy(template), dict(zip(names, combination)))
        for combination in itertools.product(*value_lists)
    ]


def _validate_manifest(manifest: Any, root: Path, policy: RegistryPolicy, source_kind: str) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise PackValidationError("INVALID_MANIFEST", "manifest root must be an object", root)
    required = {
        "schema", "schema_version", "id", "version", "title", "description", "status",
        "visibility", "engine", "license", "provenance", "taxonomy", "content", "gold", "documentation",
    }
    missing = sorted(required - set(manifest))
    if missing:
        raise PackValidationError("MISSING_FIELD", "missing manifest fields: " + ", ".join(missing), root)
    unknown = sorted(set(manifest) - required)
    if unknown:
        raise PackValidationError("UNKNOWN_MANIFEST_FIELD", "unknown manifest fields: " + ", ".join(unknown), root)
    if manifest["schema"] != MANIFEST_SCHEMA or manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise PackValidationError("UNSUPPORTED_MANIFEST_SCHEMA", "unsupported manifest schema/version", root)
    _require_text(manifest, "id", pattern=PACK_ID_RE)
    _require_text(manifest, "version", pattern=VERSION_RE)
    _require_text(manifest, "title")
    _require_text(manifest, "description")
    try:
        PackStatus(str(manifest["status"]))
        visibility = PackVisibility(str(manifest["visibility"]))
    except ValueError as error:
        raise PackValidationError("INVALID_LIFECYCLE", str(error), root) from error
    expected_visibility = PackVisibility.PRIVATE if source_kind == "private" else PackVisibility.PUBLIC
    if visibility is not expected_visibility:
        raise PackValidationError("VISIBILITY_MISMATCH", f"{source_kind} root requires {expected_visibility.value}", root)
    engine = manifest["engine"]
    if not isinstance(engine, dict) or set(engine) - {"minimum_version", "maximum_version"}:
        raise PackValidationError("INVALID_ENGINE_RANGE", "engine must contain minimum_version and optional maximum_version", root)
    minimum = _require_text(engine, "minimum_version", pattern=VERSION_RE)
    maximum = str(engine.get("maximum_version") or "").strip()
    if _version_compare(policy.engine_version, minimum) < 0 or (maximum and _version_compare(policy.engine_version, maximum) > 0):
        raise PackValidationError("INCOMPATIBLE_ENGINE", f"engine {policy.engine_version} is outside supported range", root)
    license_row = manifest["license"]
    if not isinstance(license_row, dict) or not str(license_row.get("id") or "").strip() or not str(license_row.get("name") or "").strip():
        raise PackValidationError("LICENSE_METADATA_REQUIRED", "license id and name are required", root)
    if set(license_row) - {"id", "name", "file"}:
        raise PackValidationError("INVALID_LICENSE", "license contains unknown fields", root)
    if license_row.get("file"):
        license_path = _safe_relative(root, license_row["file"], "license.file")
        if not license_path.is_file():
            raise PackValidationError("LICENSE_FILE_MISSING", "declared license file is missing", license_path)
    provenance = manifest["provenance"]
    if not isinstance(provenance, dict) or not str(provenance.get("source") or "").strip():
        raise PackValidationError("PROVENANCE_REQUIRED", "provenance.source is required", root)
    if not isinstance(manifest["taxonomy"], list) or not manifest["taxonomy"]:
        raise PackValidationError("TAXONOMY_REQUIRED", "taxonomy must be a non-empty array", root)
    for category in manifest["taxonomy"]:
        if not isinstance(category, str) or not REF_RE.fullmatch(category):
            raise PackValidationError("INVALID_TAXONOMY", f"invalid category: {category!r}", root)
    content = manifest["content"]
    if not isinstance(content, dict):
        raise PackValidationError("INVALID_CONTENT", "content must be an object", root)
    has_file = "cases_file" in content
    has_generator = "generator" in content
    if has_file == has_generator:
        raise PackValidationError("INVALID_CONTENT", "content needs exactly one of cases_file or generator", root)
    if set(content) - {"cases_file", "generator", "sha256", "case_count"}:
        raise PackValidationError("INVALID_CONTENT", "content contains unknown fields", root)
    if not isinstance(content.get("case_count"), int) or not 1 <= content["case_count"] <= policy.max_cases:
        raise PackValidationError("INVALID_CASE_COUNT", "content.case_count is invalid", root)
    if not re.fullmatch(r"[0-9a-f]{64}", str(content.get("sha256") or "")):
        raise PackValidationError("INVALID_HASH", "content.sha256 must be lowercase SHA-256", root)
    gold = manifest["gold"]
    if not isinstance(gold, dict) or set(gold) != {"file", "sha256"}:
        raise PackValidationError("INVALID_GOLD", "gold needs file and sha256", root)
    if not re.fullmatch(r"[0-9a-f]{64}", str(gold.get("sha256") or "")):
        raise PackValidationError("INVALID_HASH", "gold.sha256 must be lowercase SHA-256", root)
    _safe_relative(root, manifest["documentation"], "documentation")
    return copy.deepcopy(manifest)


def _validate_cases(raw_cases: Any, manifest: Mapping[str, Any], policy: RegistryPolicy) -> tuple[PackCase, ...]:
    if not isinstance(raw_cases, list) or not raw_cases:
        raise PackValidationError("INVALID_CASES", "cases must be a non-empty array")
    if len(raw_cases) > policy.max_cases:
        raise PackValidationError("TOO_MANY_CASES", f"pack contains {len(raw_cases)} cases")
    taxonomy = set(manifest["taxonomy"])
    seen: set[tuple[str, int]] = set()
    result: list[PackCase] = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise PackValidationError("INVALID_CASE", "case must be an object")
        required = {"id", "version", "category", "runner_ref", "scorer_ref", "verifier_ref", "definition"}
        if set(raw) != required:
            raise PackValidationError("INVALID_CASE", "case fields must exactly match the v1 contract")
        case_id = _require_text(raw, "id", pattern=CASE_ID_RE)
        version = raw["version"]
        if not isinstance(version, int) or version < 1:
            raise PackValidationError("INCOMPATIBLE_CASE_VERSION", f"invalid case version for {case_id}")
        identity = (case_id, version)
        if identity in seen:
            raise PackValidationError("DUPLICATE_CASE", f"duplicate case {case_id} v{version}")
        seen.add(identity)
        category = _require_text(raw, "category", pattern=REF_RE)
        if category not in taxonomy:
            raise PackValidationError("UNKNOWN_CATEGORY", f"case {case_id} category is not declared")
        runner_ref = _require_text(raw, "runner_ref", pattern=REF_RE)
        scorer_ref = _require_text(raw, "scorer_ref", pattern=REF_RE)
        verifier_ref = raw["verifier_ref"]
        if verifier_ref is not None and (not isinstance(verifier_ref, str) or not REF_RE.fullmatch(verifier_ref)):
            raise PackValidationError("INVALID_REFERENCE", f"invalid verifier_ref for {case_id}")
        if runner_ref not in policy.runner_refs:
            raise PackValidationError("UNKNOWN_RUNNER", runner_ref)
        if scorer_ref not in policy.scorer_refs:
            raise PackValidationError("UNKNOWN_SCORER", scorer_ref)
        if verifier_ref is not None and verifier_ref not in policy.verifier_refs:
            raise PackValidationError("UNKNOWN_VERIFIER", verifier_ref)
        definition = raw["definition"]
        if not isinstance(definition, dict):
            raise PackValidationError("INVALID_DEFINITION", f"definition for {case_id} must be an object")
        prompt = definition.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
            raise PackValidationError("INVALID_PROMPT", f"prompt for {case_id} is missing or too large")
        if int(definition.get("version") or 0) != version:
            raise PackValidationError("INCOMPATIBLE_CASE_VERSION", f"definition version mismatch for {case_id}")
        if str(definition.get("category") or "") != category:
            raise PackValidationError("INVALID_CASE", f"definition category mismatch for {case_id}")
        if str(definition.get("score_type") or "none") != scorer_ref:
            raise PackValidationError("INVALID_CASE", f"definition scorer mismatch for {case_id}")
        result.append(PackCase(
            id=case_id,
            version=version,
            category=category,
            runner_ref=runner_ref,
            scorer_ref=scorer_ref,
            verifier_ref=verifier_ref,
            definition=copy.deepcopy(definition),
            definition_sha256=canonical_sha256(definition),
        ))
    return tuple(sorted(result, key=lambda case: (case.id, case.version)))


def _validate_gold(raw_gold: Any, cases: Sequence[PackCase]) -> None:
    if not isinstance(raw_gold, dict) or raw_gold.get("schema") != "bull-benchmark-pack-gold" or raw_gold.get("schema_version") != 1:
        raise PackValidationError("INVALID_GOLD", "unsupported gold schema/version")
    rows = raw_gold.get("cases")
    if not isinstance(rows, list) or len(rows) != len(cases):
        raise PackValidationError("INVALID_GOLD", "gold must cover every case exactly once")
    expected = {(case.id, case.version): case for case in cases}
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "id", "version", "definition_sha256", "prompt_sha256", "result_instruction_sha256"
        }:
            raise PackValidationError("INVALID_GOLD", "gold case fields are invalid")
        identity = (str(row.get("id") or ""), row.get("version"))
        case = expected.get(identity)
        if case is None or identity in seen:
            raise PackValidationError("INVALID_GOLD", f"unknown or duplicate gold case {identity}")
        seen.add(identity)
        definition = case.definition
        prompt_hash = hashlib.sha256(str(definition.get("prompt") or "").encode("utf-8")).hexdigest()
        result_hash = hashlib.sha256(str(definition.get("result_instruction") or "").encode("utf-8")).hexdigest()
        if row["definition_sha256"] != case.definition_sha256 or row["prompt_sha256"] != prompt_hash or row["result_instruction_sha256"] != result_hash:
            raise PackValidationError("GOLD_MISMATCH", f"gold snapshot mismatch for {case.id}")


def _read_pack(root: Path, policy: RegistryPolicy, source_kind: str, *, verify_lock: bool) -> tuple[LoadedPack, dict[str, Any]]:
    root = root.resolve()
    if not root.is_dir() or root.is_symlink():
        raise PackValidationError("INVALID_PACK_PATH", "pack must be a regular directory", root)
    _scan_no_executable_files(root)
    manifest_raw = _load_json(root / "manifest.json", policy.max_json_bytes)
    manifest = _validate_manifest(manifest_raw, root, policy, source_kind)
    content = manifest["content"]
    if "cases_file" in content:
        cases_path = _safe_relative(root, content["cases_file"], "content.cases_file")
        raw_cases = _load_json(cases_path, policy.max_json_bytes)
    else:
        raw_cases = _generate_cases(content["generator"], policy)
    if canonical_sha256(raw_cases) != content["sha256"]:
        raise PackValidationError("CONTENT_HASH_MISMATCH", "case content hash does not match manifest", root)
    if len(raw_cases) != content["case_count"]:
        raise PackValidationError("CASE_COUNT_MISMATCH", "case count does not match manifest", root)
    cases = _validate_cases(raw_cases, manifest, policy)
    gold_path = _safe_relative(root, manifest["gold"]["file"], "gold.file")
    raw_gold = _load_json(gold_path, policy.max_json_bytes)
    if canonical_sha256(raw_gold) != manifest["gold"]["sha256"]:
        raise PackValidationError("GOLD_HASH_MISMATCH", "gold hash does not match manifest", root)
    _validate_gold(raw_gold, cases)
    documentation = _safe_relative(root, manifest["documentation"], "documentation")
    if not documentation.is_file() or documentation.suffix.casefold() not in {".md", ".txt"}:
        raise PackValidationError("DOCUMENTATION_MISSING", "documentation file is missing", documentation)
    manifest_hash = canonical_sha256(manifest)
    compiled = {
        "schema": COMPILED_SCHEMA,
        "schema_version": COMPILED_SCHEMA_VERSION,
        "pack": {"id": manifest["id"], "version": manifest["version"]},
        "manifest_sha256": manifest_hash,
        "cases": [
            {
                "id": case.id,
                "version": case.version,
                "category": case.category,
                "runner_ref": case.runner_ref,
                "scorer_ref": case.scorer_ref,
                "verifier_ref": case.verifier_ref,
                "definition": copy.deepcopy(dict(case.definition)),
            }
            for case in cases
        ],
    }
    compiled_hash = canonical_sha256(compiled)
    lock = {
        "schema": LOCK_SCHEMA,
        "schema_version": LOCK_SCHEMA_VERSION,
        "pack": {"id": manifest["id"], "version": manifest["version"]},
        "manifest_sha256": manifest_hash,
        "content_sha256": canonical_sha256(raw_cases),
        "gold_sha256": canonical_sha256(raw_gold),
        "compiled_sha256": compiled_hash,
    }
    if verify_lock:
        actual_lock = _load_json(root / "pack.lock.json", policy.max_json_bytes)
        if actual_lock != lock:
            raise PackValidationError("PACK_LOCK_MISMATCH", "pack.lock.json is stale or damaged", root)
    pack = LoadedPack(
        root=root,
        id=manifest["id"],
        version=manifest["version"],
        title=manifest["title"],
        status=PackStatus(manifest["status"]),
        visibility=PackVisibility(manifest["visibility"]),
        manifest=manifest,
        cases=cases,
        manifest_sha256=manifest_hash,
        compiled_sha256=compiled_hash,
        source_kind=source_kind,
    )
    return pack, lock


def compile_pack(root: str | Path, policy: RegistryPolicy, source_kind: str = "public") -> dict[str, Any]:
    pack, _lock = _read_pack(Path(root), policy, source_kind, verify_lock=False)
    return {
        "schema": COMPILED_SCHEMA,
        "schema_version": COMPILED_SCHEMA_VERSION,
        "pack": {"id": pack.id, "version": pack.version},
        "manifest_sha256": pack.manifest_sha256,
        "cases": [
            {
                "id": case.id,
                "version": case.version,
                "category": case.category,
                "runner_ref": case.runner_ref,
                "scorer_ref": case.scorer_ref,
                "verifier_ref": case.verifier_ref,
                "definition": copy.deepcopy(dict(case.definition)),
            }
            for case in pack.cases
        ],
    }


def write_pack_lock(root: str | Path, policy: RegistryPolicy, source_kind: str = "public") -> Path:
    path = Path(root).resolve()
    _pack, lock = _read_pack(path, policy, source_kind, verify_lock=False)
    target = path / "pack.lock.json"
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    payload = (json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    try:
        with temp.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def load_pack(root: str | Path, policy: RegistryPolicy, source_kind: str = "public") -> LoadedPack:
    return _read_pack(Path(root), policy, source_kind, verify_lock=True)[0]


class PackRegistry:
    def __init__(
        self,
        public_roots: Iterable[str | Path],
        private_roots: Iterable[str | Path],
        policy: RegistryPolicy,
    ) -> None:
        self.public_roots = tuple(Path(path).resolve() for path in public_roots)
        self.private_roots = tuple(Path(path).resolve() for path in private_roots)
        self.policy = policy

    @staticmethod
    def _candidate_dirs(root: Path) -> list[Path]:
        if not root.exists():
            return []
        if not root.is_dir() or root.is_symlink():
            raise PackValidationError("INVALID_REGISTRY_ROOT", "registry root must be a regular directory", root)
        return sorted(
            [path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")],
            key=lambda path: path.name.casefold(),
        )

    def scan(self) -> tuple[RegistryFinding, ...]:
        findings: list[RegistryFinding] = []
        identities: dict[tuple[str, str], Path] = {}
        for source_kind, roots in (("public", self.public_roots), ("private", self.private_roots)):
            for registry_root in roots:
                try:
                    candidates = self._candidate_dirs(registry_root)
                except PackValidationError as error:
                    findings.append(RegistryFinding(registry_root, source_kind, error_code=error.code, error_message=str(error)))
                    continue
                for path in candidates:
                    try:
                        pack = load_pack(path, self.policy, source_kind)
                        identity = (pack.id, pack.version)
                        if identity in identities:
                            raise PackValidationError(
                                "DUPLICATE_PACK_ID",
                                f"{pack.identity} already loaded from {identities[identity]}",
                                path,
                            )
                        identities[identity] = path
                        findings.append(RegistryFinding(path, source_kind, pack=pack))
                    except PackValidationError as error:
                        findings.append(RegistryFinding(path, source_kind, error_code=error.code, error_message=str(error)))
        return tuple(findings)

    def discover(self, *, include_retired: bool = False) -> tuple[LoadedPack, ...]:
        findings = self.scan()
        failures = [finding for finding in findings if finding.pack is None]
        if failures:
            first = failures[0]
            raise PackValidationError(first.error_code or "PACK_INVALID", first.error_message or "invalid pack", first.path)
        packs = [finding.pack for finding in findings if finding.pack is not None]
        if not include_retired:
            packs = [pack for pack in packs if pack.runnable]
        return tuple(sorted(packs, key=lambda pack: (pack.id, _version_tuple(pack.version, "pack.version"))))

    def get(self, pack_id: str, version: str | None = None, *, include_retired: bool = False) -> LoadedPack:
        matches = [pack for pack in self.discover(include_retired=include_retired) if pack.id == pack_id]
        if version is not None:
            matches = [pack for pack in matches if pack.version == version]
        if not matches:
            raise KeyError(f"Benchmark pack not found: {pack_id}" + (f"@{version}" if version else ""))
        return max(matches, key=lambda pack: _version_tuple(pack.version, "pack.version"))


__all__ = [
    "COMPILED_SCHEMA",
    "LoadedPack",
    "PackCase",
    "PackRegistry",
    "PackStatus",
    "PackValidationError",
    "PackVisibility",
    "RegistryFinding",
    "RegistryPolicy",
    "canonical_sha256",
    "compile_pack",
    "load_pack",
    "write_pack_lock",
]
