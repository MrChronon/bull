"""Offline data-only author sources -> validated, reproducible pack ZIPs.

Installed packs and selection state are never edited. Fixture validation uses
only the existing pure user_contract_v2 scorer, never model code or inference.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import tempfile
import uuid
import zipfile
from pathlib import Path

from ..user_tests import (
    MAX_FILE_BYTES, MAX_PROMPT_CHARS, ID_RE, parse_user_test_yaml,
    score_user_test, validate_user_test,
)
from .pack_library import _directory, _entry_parts, _file_type, _lstat, _no_link
from .registry import (
    PACK_ID_RE, REF_RE, VERSION_RE, PackValidationError, canonical_sha256,
    _strict_object, _reject_constant, _version_compare, load_pack, write_pack_lock,
)

BUILDER_VERSION = 1
SOURCE_SCHEMA = "bull-pack-workspace"
FIXTURE_SCHEMA = "bull-author-fixtures"


def _fail(message, code="AUTHOR_INVALID_SOURCE"):
    raise PackValidationError(code, message)


def _keys(row, required, optional=()):
    if not isinstance(row, dict) or set(row) - set(required) - set(optional) or set(required) - set(row):
        _fail("missing or unknown fields; expected " + ", ".join(sorted(required)))


def _string(value, name, maximum=500, pattern=None):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or (pattern and not pattern.fullmatch(value)):
        _fail("invalid " + name)
    return value


def _number(value, name, minimum, maximum, *, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not minimum <= value <= maximum or not math.isfinite(value) or
            (integer and not isinstance(value, int))):
        _fail("invalid numeric " + name)
    return value


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _json(data):
    try:
        return json.loads(data.decode("utf-8-sig"), object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise PackValidationError("AUTHOR_INVALID_JSON", "invalid finite unique-key source JSON") from error


def _read_tree(root, limits):
    """Snapshot bounded regular files, refusing every link before traversal."""
    root = Path(os.path.abspath(root))
    if not _directory(root):
        _fail("workspace directory not found")
    files = {}; names = set(); total = 0; pending = [root]; entries = 0
    while pending:
        parent = pending.pop()
        for path in parent.iterdir():
            entries += 1
            if entries > limits.max_entries:
                _fail("workspace entry budget exceeded")
            relative = path.relative_to(root).as_posix()
            details = _lstat(path)
            if details is None:
                _fail("workspace changed during reading")
            _no_link(path, details)
            import stat
            _entry_parts(relative, directory=stat.S_ISDIR(details.st_mode))
            folded = relative.casefold()
            if folded in names:
                _fail("case-colliding workspace paths")
            names.add(folded)
            if stat.S_ISDIR(details.st_mode):
                pending.append(path); continue
            if not stat.S_ISREG(details.st_mode):
                _fail("workspace contains a special file")
            _file_type(tuple(relative.split("/")))
            # Tasks and documentation are small; author/fixture JSON uses registry budget.
            cap = limits.max_file_bytes if relative in {"author.json", "fixtures.json"} else MAX_FILE_BYTES
            if details.st_size > cap:
                _fail("workspace file budget exceeded")
            with path.open("rb") as stream:
                data = stream.read(cap + 1)
            if len(data) > cap:
                _fail("workspace file grew beyond budget")
            total += len(data)
            if total > limits.max_total_bytes:
                _fail("workspace total budget exceeded")
            files[relative] = data
    return files


def _parameters(raw):
    _keys(raw, (), {"primary_predict", "recovery_predict", "think_override", "benchmark_defaults"})
    result = copy.deepcopy(raw)
    for key in ("primary_predict", "recovery_predict"):
        if key in raw:
            _number(raw[key], key, 1, 32768, integer=True)
    if "think_override" in raw and type(raw["think_override"]) is not bool:
        _fail("think_override must be boolean")
    if "benchmark_defaults" in raw:
        bounds = {
            "ctx": (512, 262144, True), "num_predict": (1, 32768, True),
            "num_thread": (1, 256, True), "temperature": (0, 2, False),
            "top_p": (0, 1, False), "top_k": (0, 1000, True),
            "min_p": (0, 1, False), "repeat_penalty": (0, 2, False),
        }
        defaults = raw["benchmark_defaults"]
        _keys(defaults, (), bounds)
        for name, value in defaults.items():
            low, high, integer = bounds[name]
            _number(value, name, low, high, integer=integer)
        if "primary_predict" in raw and "num_predict" in defaults and raw["primary_predict"] != defaults["num_predict"]:
            _fail("conflicting primary_predict and benchmark_defaults.num_predict")
    return result


def _strict_task(raw):
    """Reject coercions/ignored fields without changing the established scorer."""
    _keys(raw, {"schema", "version", "id", "title", "description", "language", "prompt", "criteria"}, {"manual_review"})
    try:
        _json_bytes(raw)
    except (ValueError, RecursionError, TypeError) as error:
        raise PackValidationError("AUTHOR_INVALID_TASK", "task values must be finite JSON data") from error
    if raw["schema"] != "bull-user-test" or type(raw["version"]) is not int or raw["version"] != 1:
        _fail("task schema must be bull-user-test version 1")
    for name, maximum in (("id", 64), ("title", 120), ("description", 500), ("prompt", MAX_PROMPT_CHARS)):
        _string(raw[name], name, maximum, ID_RE if name == "id" else None)
    if not isinstance(raw["language"], str) or raw["language"] not in {"en", "ru", "auto"}:
        _fail("task language must be en, ru or auto")
    review = raw.get("manual_review", [])
    if not isinstance(review, list) or len(review) > 20:
        _fail("manual_review must be a list of at most 20 questions")
    for item in review:
        _string(item, "manual review", 500)
    if not isinstance(raw["criteria"], list) or not 1 <= len(raw["criteria"]) <= 20:
        _fail("criteria must contain 1..20 checks")
    extras = {
        "contains_all": {"values"}, "contains_any": {"values"}, "forbidden_any": {"values"},
        "word_count": {"min", "max"}, "terminal_json_equals": {"path", "expected"},
        "terminal_json_number": {"path", "expected", "tolerance_abs", "tolerance_pct"},
    }
    for row in raw["criteria"]:
        kind = row.get("type") if isinstance(row, dict) else None
        if kind not in extras:
            _fail("unsupported criterion type")
        _keys(row, {"id", "type", "description", "weight"}, extras[kind] | {"critical"})
        _string(row["description"], "criterion description", 300)
        _number(row["weight"], "criterion weight", 0, 100)
        if "critical" in row and type(row["critical"]) is not bool:
            _fail("critical must be boolean")
        if kind in {"contains_all", "contains_any", "forbidden_any"}:
            values = row.get("values")
            if not isinstance(values, list):
                _fail("values must be literal strings")
            for value in values:
                _string(value, "literal phrase", 500)
        if kind == "word_count":
            _number(row.get("min"), "min", 0, 20000, integer=True)
            _number(row.get("max"), "max", 0, 20000, integer=True)
        if kind == "terminal_json_number":
            _number(row.get("expected"), "expected", -1e100, 1e100)
            for key in ("tolerance_abs", "tolerance_pct"):
                if key in row:
                    _number(row[key], key, 0, 1e100)
    try:
        return validate_user_test(raw)
    except (ValueError, TypeError, OverflowError) as error:
        raise PackValidationError("AUTHOR_INVALID_TASK", str(error)) from error


def _fixtures(raw, cases):
    _keys(raw, {"schema", "schema_version", "cases"})
    if raw["schema"] != FIXTURE_SCHEMA or type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        _fail("unsupported author fixtures schema")
    expected = {row["id"]: row for row in cases if row["scorer_ref"] == "user_contract_v2"}
    if not isinstance(raw["cases"], list) or len(raw["cases"]) != len(expected):
        _fail("fixtures must cover every scored case exactly once; unscored tasks have no score fixtures")
    seen = set(); results = []
    for group in raw["cases"]:
        _keys(group, {"id", "answers"})
        case_id = _string(group["id"], "fixture case ID", 64)
        if case_id not in expected or case_id in seen:
            _fail("unknown or duplicate fixture case")
        seen.add(case_id)
        config = expected[case_id]["definition"]["scorer_config"]
        criteria = {row["id"] for row in config["criteria"]}
        answers = group["answers"]
        if not isinstance(answers, list) or not 2 <= len(answers) <= 64:
            _fail("each scored case needs 2..64 fixture answers")
        ids = set(); positives = 0; failed_coverage = set()
        for answer in answers:
            _keys(answer, {"id", "kind", "answer", "expected_score", "failed_checks"})
            answer_id = _string(answer["id"], "fixture ID", 64, ID_RE)
            if answer_id in ids:
                _fail("duplicate fixture ID")
            ids.add(answer_id)
            text = _string(answer["answer"], "fixture answer", MAX_FILE_BYTES)
            target = _number(answer["expected_score"], "expected_score (0..1)", 0, 1)
            failed = answer["failed_checks"]
            if (not isinstance(failed, list) or any(not isinstance(value, str) for value in failed) or
                    len(failed) != len(set(failed)) or not set(failed) <= criteria):
                _fail("failed_checks must contain distinct known criterion IDs")
            if answer["kind"] == "positive" and target == 1 and not failed:
                positives += 1
            elif answer["kind"] == "negative" and target < 1 and failed:
                failed_coverage.update(failed)
            else:
                _fail("positive must expect 1/no failures; negative must expect <1 and named failures")
            try:
                observed = score_user_test(text, config)
            except (OverflowError, RecursionError, ValueError, TypeError) as error:
                raise PackValidationError("AUTHOR_FIXTURE_INVALID_ANSWER", "fixture exceeds supported scorer parsing bounds") from error
            actual_failed = {check["name"] for check in observed["checks"] if not check["ok"]}
            passed = actual_failed == set(failed) and abs(observed["value"] - target) <= 1e-9
            results.append({"case": case_id, "fixture": answer_id, "passed": passed,
                            "score": observed["value"], "expected_score": target,
                            "failed_checks": sorted(actual_failed), "expected_failed_checks": sorted(failed)})
        if not positives or failed_coverage != criteria:
            _fail("need a passing answer and negative coverage of every criterion", "AUTHOR_FIXTURE_COVERAGE")
    return results


class AuthorWorkshop:
    def __init__(self, library):
        self.library = library

    def _workspace(self, pack_id, files):
        parent = self.library.root / "Workspaces"
        _directory(parent, create=True)
        # New exclusive directory; failure leaves an inspectable, non-runnable workspace.
        target = parent / (pack_id + "-" + uuid.uuid4().hex[:12])
        target.mkdir()
        for name, data in files.items():
            path = target.joinpath(*_entry_parts(name, directory=False))
            _file_type(tuple(name.split("/")))
            _directory(path.parent, create=True)
            with path.open("xb") as stream:
                stream.write(data)
        return target

    def create_starter(self, pack_id, *, language="en"):
        _string(pack_id, "pack ID", 64, PACK_ID_RE)
        if language not in {"en", "ru"}:
            _fail("starter language must be en or ru")
        from .author_template import starter_files
        return self._workspace(pack_id, starter_files(pack_id, language, self.library.policy.engine_version))

    def validate(self, workspace):
        files = _read_tree(workspace, self.library.limits)
        if not {"author.json", "fixtures.json", "README.md", "LICENSE.txt"} <= set(files):
            _fail("need author.json, fixtures.json, README.md and LICENSE.txt")
        source = _json(files["author.json"])
        _keys(source, {"schema", "schema_version", "id", "version", "title", "description", "status",
                       "visibility", "minimum_engine_version", "license", "provenance", "tasks"})
        if source["schema"] != SOURCE_SCHEMA or type(source["schema_version"]) is not int or source["schema_version"] != 1:
            _fail("unsupported workspace schema")
        for key, pattern, maximum in (("id", PACK_ID_RE, 64), ("version", VERSION_RE, 40),
                                     ("title", None, 120), ("description", None, 500), ("minimum_engine_version", VERSION_RE, 40)):
            _string(source[key], key, maximum, pattern)
        if (not isinstance(source["status"], str) or source["status"] not in {"experimental", "candidate"} or
                not isinstance(source["visibility"], str) or source["visibility"] not in {"public", "private"}):
            _fail("workshop status must be experimental/candidate and visibility public/private")
        if _version_compare(self.library.policy.engine_version, source["minimum_engine_version"]) < 0:
            _fail("workspace requires a newer engine", "INCOMPATIBLE_ENGINE")
        _keys(source["license"], {"id", "name"})
        for value in source["license"].values():
            _string(value, "license", 300)
        _keys(source["provenance"], {"source"}, {"author"})
        for value in source["provenance"].values():
            _string(value, "provenance", 500)
        for name in ("README.md", "LICENSE.txt"):
            _string(files[name].decode("utf-8-sig"), name, MAX_FILE_BYTES)
        tasks = source["tasks"]
        if not isinstance(tasks, list) or not 1 <= len(tasks) <= self.library.policy.max_cases:
            _fail("workspace task count exceeds registry budget or is empty")
        cases = []; ids = set(); allowed = {"author.json", "fixtures.json", "README.md", "LICENSE.txt"}
        for task in tasks:
            _keys(task, {"file", "category", "case_version"}, {"id", "title", "description", "language", "parameters"})
            name = _string(task["file"], "task file", 150)
            parts = _entry_parts(name, directory=False)
            if len(parts) != 2 or parts[0] != "Tasks" or Path(name).suffix not in {".yaml", ".yml", ".txt"}:
                _fail("task file must be Tasks/<name>.yaml, .yml or .txt")
            if name in allowed or name not in files:
                _fail("task path is duplicated or missing")
            allowed.add(name)
            category = _string(task["category"], "category", 64, REF_RE)
            version = _number(task["case_version"], "case_version", 1, 1000000, integer=True)
            try:
                text = files[name].decode("utf-8-sig")
                if name.endswith(".txt"):
                    for key in ("id", "title", "description", "language"):
                        _string(task.get(key), key, 64 if key == "id" else 120 if key == "title" else 500, ID_RE if key == "id" else None)
                    if task["language"] not in {"en", "ru", "auto"}:
                        _fail("task language must be en, ru or auto")
                    item = {"id": task["id"], "title": task["title"], "description": task["description"],
                            "language": task["language"], "prompt": _string(text.strip(), "prompt", MAX_PROMPT_CHARS)}
                    definition = {"prompt": item["prompt"], "score_type": "none", "manual_review_required": True}
                else:
                    if set(task) & {"id", "title", "description", "language"}:
                        _fail("YAML task identity belongs in the YAML, not the descriptor")
                    item = _strict_task(parse_user_test_yaml(text))
                    definition = {"prompt": item["prompt"], "result_instruction": item["result_instruction"],
                                  "score_type": "user_contract_v2", "scorer_config": {
                                      "criteria": item["criteria"], "manual_review": item["manual_review"], "language": item["language"]}}
            except (ValueError, TypeError, UnicodeError, RecursionError) as error:
                if isinstance(error, PackValidationError):
                    raise
                raise PackValidationError("AUTHOR_INVALID_TASK", "invalid task " + name) from error
            if item["id"] in ids:
                _fail("duplicate task ID")
            ids.add(item["id"])
            definition.update(version=version, category=category, title=item["title"], description=item["description"], expected_language=item["language"])
            definition.update(_parameters(task.get("parameters", {})))
            cases.append({"id": item["id"], "version": version, "category": category, "runner_ref": "single_turn_v1",
                          "scorer_ref": definition["score_type"], "verifier_ref": "benchmark_contract_v1", "definition": definition})
        if set(files) != allowed:
            _fail("undeclared files in workspace; move personal notes and outputs outside it")
        checks = _fixtures(_json(files["fixtures.json"]), cases)
        scored = sum(row["scorer_ref"] == "user_contract_v2" for row in cases)
        return {"id": source["id"], "version": source["version"], "title": source["title"], "source": source,
                "files": files, "cases": cases, "case_count": len(cases), "scored_cases": scored,
                "manual_cases": len(cases) - scored, "checks": checks, "passed": all(row["passed"] for row in checks),
                "source_sha256": canonical_sha256({name: hashlib.sha256(data).hexdigest() for name, data in files.items()})}

    def _compiled_files(self, report):
        if not report["passed"]:
            failures = [row["case"] + "/" + row["fixture"] for row in report["checks"] if not row["passed"]]
            _fail("fixture expectations differ: " + ", ".join(failures[:10]), "AUTHOR_FIXTURE_MISMATCH")
        source = report["source"]; cases = report["cases"]
        gold = {"schema": "bull-benchmark-pack-gold", "schema_version": 1, "cases": [{
            "id": row["id"], "version": row["version"], "definition_sha256": canonical_sha256(row["definition"]),
            "prompt_sha256": hashlib.sha256(row["definition"]["prompt"].encode("utf-8")).hexdigest(),
            "result_instruction_sha256": hashlib.sha256(row["definition"].get("result_instruction", "").encode("utf-8")).hexdigest(),
        } for row in cases]}
        manifest = {"schema": "bull-benchmark-pack-manifest", "schema_version": 1,
                    **{key: source[key] for key in ("id", "version", "title", "description", "status", "visibility")},
                    "engine": {"minimum_version": source["minimum_engine_version"]},
                    "license": {**source["license"], "file": "LICENSE.txt"},
                    "provenance": {**source["provenance"], "author_builder_version": BUILDER_VERSION,
                                   "author_source_sha256": report["source_sha256"]},
                    "taxonomy": sorted({row["category"] for row in cases}),
                    "content": {"cases_file": "cases.json", "sha256": canonical_sha256(cases), "case_count": len(cases)},
                    "gold": {"file": "gold.json", "sha256": canonical_sha256(gold)}, "documentation": "README.md"}
        files = {"manifest.json": _json_bytes(manifest), "cases.json": _json_bytes(cases), "gold.json": _json_bytes(gold),
                 "README.md": report["files"]["README.md"], "LICENSE.txt": report["files"]["LICENSE.txt"]}
        files.update({"Source/" + name: data for name, data in report["files"].items()})
        for name in ("cases.json", "gold.json", "manifest.json"):
            if len(files[name]) > self.library.policy.max_json_bytes:
                _fail("compiled JSON exceeds registry byte budget")
        return files

    def build(self, workspace, destination, *, expected_source_sha256=None):
        report = self.validate(workspace)
        if expected_source_sha256 is not None and report["source_sha256"] != expected_source_sha256:
            _fail("source changed after preview; validate again", "AUTHOR_SOURCE_CHANGED")
        files = self._compiled_files(report)
        output = Path(os.path.abspath(destination)); root = Path(os.path.abspath(workspace))
        _entry_parts(output.name, directory=False)
        if output == root or root in output.parents or output.suffix.casefold() != ".zip":
            _fail("ZIP output must be outside the editable workspace")
        _directory(output.parent, create=True)
        if _lstat(output) is not None:
            raise FileExistsError("author ZIP already exists; choose a new version or output file")
        temporary = None
        try:
            with tempfile.TemporaryDirectory(prefix="bull-author-compile-") as directory:
                compiled = Path(directory)
                for name, data in files.items():
                    path = compiled / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
                write_pack_lock(compiled, self.library.policy, report["source"]["visibility"])
                pack = load_pack(compiled, self.library.policy, report["source"]["visibility"])
                files["pack.lock.json"] = (compiled / "pack.lock.json").read_bytes()
                payload_size = sum(len(data) for data in files.values())
                archive_size = 22 + sum(len(data) + 76 + 2 * len(name.encode("utf-8")) for name, data in files.items())
                if (len(files) > self.library.limits.max_entries or payload_size > self.library.limits.max_total_bytes or
                        archive_size > self.library.limits.max_archive_bytes or
                        any(len(data) > self.library.limits.max_file_bytes for data in files.values())):
                    _fail("compiled ZIP exceeds file, entry or byte budget", "ZIP_LIMIT_EXCEEDED")
                fd, name = tempfile.mkstemp(prefix=".bull-author-", suffix=".zip", dir=output.parent)
                os.close(fd); temporary = Path(name)
                with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
                    for name, data in sorted(files.items()):
                        entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                        entry.external_attr = 0o100644 << 16
                        archive.writestr(entry, data)
                preview = self.library.inspect_zip(temporary)
                if preview.compiled_sha256 != pack.compiled_sha256:
                    _fail("compiled ZIP preview differs")
                # Atomic no-clobber publication, unlike replace() which overwrites.
                os.link(temporary, output)
            return output
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def copy_installed(self, pack_id, version, new_version):
        pack = self.library.get(pack_id, version)
        _string(new_version, "new version", 40, VERSION_RE)
        if new_version == version:
            _fail("editable update needs a different version")
        source_path = pack.root / "Source"
        if not _directory(source_path):
            _fail("pack has no workshop source; request editable sources from its author", "AUTHOR_SOURCE_UNAVAILABLE")
        report = self.validate(source_path)
        compiled = self._compiled_files(report)
        if _json(compiled["manifest.json"]) != pack.manifest:
            _fail("embedded author sources differ from installed content", "AUTHOR_SOURCE_MISMATCH")
        files = dict(report["files"])
        source = copy.deepcopy(report["source"]); source["version"] = new_version; source["status"] = "experimental"
        files["author.json"] = _json_bytes(source)
        return self._workspace(pack.id, files)
