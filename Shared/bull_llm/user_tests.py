"""Safe, dependency-free loading and scoring of user-owned benchmark tasks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


MAX_FILE_BYTES = 256 * 1024
MAX_PROMPT_CHARS = 50_000
MAX_TESTS = 100
ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
PATH_RE = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){0,7}$")
SUPPORTED_CRITERIA = {
    "contains_all",
    "contains_any",
    "forbidden_any",
    "terminal_json_equals",
    "terminal_json_number",
    "word_count",
}


class UserTestError(ValueError):
    pass


def _scalar(text: str) -> Any:
    value = text.strip()
    if not value:
        return ""
    if value.startswith("[") or value.startswith("{") or value.startswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise UserTestError(f"invalid JSON-style YAML scalar: {exc}") from exc
    if value.startswith("'"):
        if not value.endswith("'") or len(value) < 2:
            raise UserTestError("unterminated single-quoted scalar")
        return value[1:-1].replace("''", "'")
    low = value.casefold()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    try:
        return float(value) if any(char in value for char in ".eE") else int(value)
    except ValueError:
        return value


def parse_user_test_yaml(text: str) -> dict[str, Any]:
    """Parse the documented BULL YAML subset without executing tags or aliases."""
    if "\t" in text:
        raise UserTestError("tabs are not allowed; use spaces")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    document: dict[str, Any] = {}
    criteria: list[dict[str, Any]] = []
    manual_review: list[str] = []
    index = 0
    while index < len(lines):
        raw = lines[index]
        index += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(" "):
            raise UserTestError(f"unexpected indentation on line {index}")
        if ":" not in raw:
            raise UserTestError(f"expected key: value on line {index}")
        key, value = raw.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", key):
            raise UserTestError(f"invalid key on line {index}: {key}")
        if key in document or (key == "criteria" and criteria) or (key == "manual_review" and manual_review):
            raise UserTestError(f"duplicate key: {key}")
        value = value.strip()
        if key == "prompt":
            if value != "|":
                raise UserTestError("prompt must use a literal block: prompt: |")
            block = []
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith("  ")):
                line = lines[index]
                block.append(line[2:] if line.startswith("  ") else "")
                index += 1
            document[key] = "\n".join(block).rstrip()
            continue
        if key == "manual_review":
            if value:
                raise UserTestError("manual_review must be a list")
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith("  ")):
                line = lines[index]; index += 1
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if not line.startswith("  - "):
                    raise UserTestError(f"manual_review item expected on line {index}")
                manual_review.append(str(_scalar(line[4:])))
            document[key] = manual_review
            continue
        if key == "criteria":
            if value:
                raise UserTestError("criteria must be a list")
            current = None
            while index < len(lines) and (not lines[index].strip() or lines[index].startswith("  ")):
                line = lines[index]; index += 1
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if line.startswith("  - "):
                    current = {}
                    criteria.append(current)
                    remainder = line[4:]
                    if ":" not in remainder:
                        raise UserTestError(f"criterion must start with key: value on line {index}")
                    subkey, subvalue = remainder.split(":", 1)
                    current[subkey.strip()] = _scalar(subvalue)
                    continue
                if current is None or not line.startswith("    ") or line.startswith("      "):
                    raise UserTestError(f"invalid criterion indentation on line {index}")
                remainder = line[4:]
                if ":" not in remainder:
                    raise UserTestError(f"criterion key expected on line {index}")
                subkey, subvalue = remainder.split(":", 1)
                subkey = subkey.strip(); subvalue = subvalue.strip()
                if subkey in current:
                    raise UserTestError(f"duplicate criterion key: {subkey}")
                if subkey == "values":
                    if subvalue:
                        parsed = _scalar(subvalue)
                        if not isinstance(parsed, list):
                            raise UserTestError("values must be a list")
                        current[subkey] = parsed
                        continue
                    values = []
                    while index < len(lines) and (not lines[index].strip() or lines[index].startswith("      ")):
                        nested = lines[index]; index += 1
                        if not nested.strip() or nested.lstrip().startswith("#"):
                            continue
                        if not nested.startswith("      - "):
                            raise UserTestError(f"values item expected on line {index}")
                        values.append(_scalar(nested[8:]))
                    current[subkey] = values
                else:
                    current[subkey] = _scalar(subvalue)
            document[key] = criteria
            continue
        document[key] = _scalar(value)
    return document


def _validate_criterion(raw: Mapping[str, Any], index: int) -> dict[str, Any]:
    criterion = dict(raw)
    criterion_id = str(criterion.get("id") or "")
    if not ID_RE.fullmatch(criterion_id):
        raise UserTestError(f"criteria[{index}].id must match {ID_RE.pattern}")
    kind = str(criterion.get("type") or "")
    if kind not in SUPPORTED_CRITERIA:
        raise UserTestError(f"criteria[{index}].type must be one of: {', '.join(sorted(SUPPORTED_CRITERIA))}")
    try:
        weight = float(criterion.get("weight"))
    except (TypeError, ValueError) as exc:
        raise UserTestError(f"criteria[{index}].weight must be a number") from exc
    if not 0 < weight <= 100:
        raise UserTestError(f"criteria[{index}].weight must be in (0, 100]")
    criterion["weight"] = weight
    criterion["critical"] = bool(criterion.get("critical", False))
    criterion["description"] = str(criterion.get("description") or criterion_id)[:300]
    if kind in ("contains_all", "contains_any", "forbidden_any"):
        values = criterion.get("values")
        if not isinstance(values, list) or not values or len(values) > 30:
            raise UserTestError(f"criteria[{index}].values must contain 1..30 strings")
        criterion["values"] = [str(value) for value in values]
        if any(not value or len(value) > 500 for value in criterion["values"]):
            raise UserTestError(f"criteria[{index}].values contains an empty or oversized string")
    elif kind in ("terminal_json_equals", "terminal_json_number"):
        path = str(criterion.get("path") or "")
        if not PATH_RE.fullmatch(path):
            raise UserTestError(f"criteria[{index}].path must be a dotted JSON path")
        criterion["path"] = path
        if "expected" not in criterion:
            raise UserTestError(f"criteria[{index}].expected is required")
        if kind == "terminal_json_number":
            try:
                criterion["expected"] = float(criterion["expected"])
            except (TypeError, ValueError) as exc:
                raise UserTestError(f"criteria[{index}].expected must be numeric") from exc
            absolute = criterion.get("tolerance_abs")
            percent = criterion.get("tolerance_pct")
            if (absolute is None) == (percent is None):
                raise UserTestError(f"criteria[{index}] needs exactly one of tolerance_abs or tolerance_pct")
            key = "tolerance_abs" if absolute is not None else "tolerance_pct"
            try:
                criterion[key] = float(criterion[key])
            except (TypeError, ValueError) as exc:
                raise UserTestError(f"criteria[{index}].{key} must be numeric") from exc
            if criterion[key] < 0:
                raise UserTestError(f"criteria[{index}].{key} must be non-negative")
    elif kind == "word_count":
        minimum = int(criterion.get("min", 0)); maximum = int(criterion.get("max", MAX_PROMPT_CHARS))
        if minimum < 0 or maximum < minimum or maximum > 20_000:
            raise UserTestError(f"criteria[{index}] word_count bounds are invalid")
        criterion["min"], criterion["max"] = minimum, maximum
    return criterion


def validate_user_test(document: Mapping[str, Any], source_name: str = "user.yaml") -> dict[str, Any]:
    raw = dict(document)
    if raw.get("schema") != "bull-user-test" or int(raw.get("version") or 0) != 1:
        raise UserTestError("schema must be bull-user-test and version must be 1")
    test_id = str(raw.get("id") or "")
    if not ID_RE.fullmatch(test_id):
        raise UserTestError(f"id must match {ID_RE.pattern}")
    prompt = str(raw.get("prompt") or "").strip()
    if not prompt or len(prompt) > MAX_PROMPT_CHARS:
        raise UserTestError(f"prompt must contain 1..{MAX_PROMPT_CHARS} characters")
    criteria_raw = raw.get("criteria")
    if not isinstance(criteria_raw, list) or not 1 <= len(criteria_raw) <= 20:
        raise UserTestError("criteria must contain 1..20 deterministic checks")
    criteria = [_validate_criterion(item, index) for index, item in enumerate(criteria_raw, 1) if isinstance(item, Mapping)]
    if len(criteria) != len(criteria_raw):
        raise UserTestError("every criteria item must be a mapping")
    if len({item["id"] for item in criteria}) != len(criteria):
        raise UserTestError("criterion ids must be unique")
    if abs(sum(item["weight"] for item in criteria) - 100.0) > 1e-6:
        raise UserTestError("criterion weights must sum to exactly 100")
    review = raw.get("manual_review") or []
    if not isinstance(review, list) or len(review) > 20 or any(not str(item).strip() for item in review):
        raise UserTestError("manual_review must be a list of at most 20 non-empty strings")
    needs_json = any(item["type"].startswith("terminal_json_") for item in criteria)
    json_paths = [item["path"] for item in criteria if item["type"].startswith("terminal_json_")]
    result_instruction = ""
    if needs_json:
        result_instruction = (
            "For deterministic BULL checks, finish the answer with the line BENCHMARK_RESULT and one JSON object. "
            "After that JSON write nothing. Required JSON paths: " + ", ".join(json_paths) + "."
        )
    return {
        "id": test_id,
        "title": str(raw.get("title") or test_id)[:120],
        "description": str(raw.get("description") or "User-defined structured task")[:500],
        "language": str(raw.get("language") or "auto")[:20],
        "prompt": prompt,
        "criteria": criteria,
        "manual_review": [str(item).strip()[:500] for item in review],
        "result_instruction": result_instruction,
        "source_name": Path(source_name).name,
    }


def _slug(stem: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", stem.casefold()).strip("_")
    if not value or not value[0].isalpha():
        value = "task_" + value
    return value[:58] or "task"


def load_user_tests(root: str | Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    base = Path(root)
    if not base.exists():
        return {}, []
    tests: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, str]] = []
    candidates = sorted(
        path for path in base.rglob("*")
        if path.is_file()
        and ".example." not in path.name.casefold()
        and path.suffix.casefold() in (".txt", ".yaml", ".yml")
    )
    for path in candidates[: MAX_TESTS + 1]:
        relative = path.relative_to(base).as_posix()
        if len(tests) >= MAX_TESTS:
            findings.append({"file": relative, "error": f"only the first {MAX_TESTS} valid tests are loaded"})
            break
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise UserTestError(f"file is larger than {MAX_FILE_BYTES} bytes")
            text = path.read_text(encoding="utf-8-sig")
            if path.suffix.casefold() == ".txt":
                prompt = text.strip()
                if not prompt or len(prompt) > MAX_PROMPT_CHARS:
                    raise UserTestError(f"text prompt must contain 1..{MAX_PROMPT_CHARS} characters")
                test_id = _slug(path.stem)
                item = {
                    "version": 1,
                    "description": f"User prompt from {path.name}",
                    "prompt": prompt,
                    "category": "user_tasks",
                    "score_type": "none",
                    "source": "user_file",
                    "source_name": path.name,
                    "manual_review_required": True,
                }
            else:
                validated = validate_user_test(parse_user_test_yaml(text), path.name)
                test_id = validated["id"]
                item = {
                    "version": 1,
                    "description": validated["description"],
                    "prompt": validated["prompt"],
                    "result_instruction": validated["result_instruction"],
                    "category": "user_tasks",
                    "score_type": "user_contract_v2",
                    "scorer_config": {
                        "criteria": validated["criteria"],
                        "manual_review": validated["manual_review"],
                        "language": validated["language"],
                    },
                    "source": "user_file",
                    "source_name": validated["source_name"],
                }
            public_id = "user_" + test_id
            if public_id in tests:
                raise UserTestError(f"duplicate test id: {public_id}")
            tests[public_id] = item
        except (OSError, UnicodeError, UserTestError, ValueError, TypeError) as exc:
            findings.append({"file": relative, "error": str(exc)})
    return tests, findings


def _terminal_json(answer: str) -> tuple[Any, str | None]:
    marker = "BENCHMARK_RESULT"
    position = str(answer or "").rfind(marker)
    if position < 0:
        return None, "missing_benchmark_result"
    tail = str(answer)[position + len(marker) :].lstrip()
    try:
        value, end = json.JSONDecoder().raw_decode(tail)
    except json.JSONDecodeError:
        return None, "invalid_terminal_json"
    if tail[end:].strip():
        return value, "trailing_text_after_terminal_json"
    return value, None


def _path_value(root: Any, path: str) -> tuple[bool, Any]:
    current = root
    for key in path.split("."):
        if not isinstance(current, Mapping) or key not in current:
            return False, None
        current = current[key]
    return True, current


def _phrase_present(value: str, text: str, *, word_boundaries: bool) -> bool:
    """Match a declared literal safely, without treating a word stem as a token."""
    needle = str(value).casefold()
    if not word_boundaries or not re.fullmatch(r"\w+", needle, flags=re.UNICODE):
        return needle in text
    return re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", text, flags=re.UNICODE) is not None


def _json_equals(observed: Any, expected: Any) -> bool:
    """JSON equality that never equates ``true`` with numeric ``1``."""
    if isinstance(observed, bool) or isinstance(expected, bool):
        return isinstance(observed, bool) and isinstance(expected, bool) and observed is expected
    if isinstance(observed, Mapping) and isinstance(expected, Mapping):
        return set(observed) == set(expected) and all(_json_equals(observed[key], expected[key]) for key in observed)
    if isinstance(observed, list) and isinstance(expected, list):
        return len(observed) == len(expected) and all(_json_equals(a, b) for a, b in zip(observed, expected))
    return observed == expected


def _score_user_test(
    answer: str,
    scorer_config: Mapping[str, Any],
    *,
    revision: str,
    strict_terminal_json: bool,
    word_boundaries: bool,
) -> dict[str, Any]:
    text = str(answer or "")
    prose = text.rsplit("BENCHMARK_RESULT", 1)[0] if "BENCHMARK_RESULT" in text else text
    folded = prose.casefold()
    criteria = list(scorer_config.get("criteria") or [])
    needs_json = any(str(item.get("type")).startswith("terminal_json_") for item in criteria)
    structured, parse_error = _terminal_json(text) if needs_json else (None, None)
    checks = []
    critical_failures = []
    for criterion in criteria:
        kind = criterion["type"]
        evidence = ""
        if kind == "contains_all":
            missing = [value for value in criterion["values"] if not _phrase_present(value, folded, word_boundaries=word_boundaries)]
            ok = not missing; evidence = "missing: " + ", ".join(missing[:5]) if missing else "all declared phrases present"
        elif kind == "contains_any":
            present = [value for value in criterion["values"] if _phrase_present(value, folded, word_boundaries=word_boundaries)]
            ok = bool(present); evidence = "present: " + ", ".join(present[:5]) if present else "none of the declared phrases present"
        elif kind == "forbidden_any":
            present = [value for value in criterion["values"] if _phrase_present(value, folded, word_boundaries=word_boundaries)]
            ok = not present; evidence = "forbidden present: " + ", ".join(present[:5]) if present else "no forbidden phrase present"
        elif kind == "word_count":
            count = len(re.findall(r"\b\w+(?:[-'][\w]+)*\b", prose, flags=re.UNICODE))
            ok = int(criterion["min"]) <= count <= int(criterion["max"]); evidence = f"word_count={count}"
        elif kind in ("terminal_json_equals", "terminal_json_number"):
            exists, observed = _path_value(structured, criterion["path"])
            if kind == "terminal_json_equals":
                ok = bool(exists and (parse_error is None or not strict_terminal_json) and _json_equals(observed, criterion["expected"]))
            else:
                try:
                    if strict_terminal_json and isinstance(observed, bool):
                        raise TypeError("JSON boolean is not a numeric result")
                    observed_number = float(observed)
                    tolerance = float(criterion.get("tolerance_abs")) if criterion.get("tolerance_abs") is not None else abs(float(criterion["expected"])) * float(criterion["tolerance_pct"]) / 100.0
                    ok = bool(exists and (parse_error is None or not strict_terminal_json) and abs(observed_number - float(criterion["expected"])) <= tolerance)
                except (TypeError, ValueError):
                    ok = False
            evidence = f"path={criterion['path']}; observed={observed!r}; expected={criterion['expected']!r}"
        else:
            ok = False; evidence = "unsupported criterion"
        check = {
            "name": criterion["id"], "description": criterion["description"],
            "ok": bool(ok), "weight": float(criterion["weight"]) / 100.0,
            "critical": bool(criterion.get("critical")), "evidence": evidence[:500],
        }
        checks.append(check)
        if not ok and check["critical"]:
            critical_failures.append({"criterion": criterion["id"], "reason": "declared_critical_check_failed", "evidence": evidence[:500]})
    value = sum(check["weight"] for check in checks if check["ok"])
    caps = []
    if critical_failures and value > 0.59:
        value = 0.59
        caps.append({"name": "declared_critical_failure", "value": 0.59})
    review = [str(item) for item in (scorer_config.get("manual_review") or [])]
    return {
        "method": revision,
        "value": value,
        "automatic_score": value,
        "semantic_score": None,
        "structural_score": (None if not needs_json else (1.0 if parse_error is None else 0.0)),
        "parse_error": parse_error,
        "structured_result": structured,
        "checks": checks,
        "critical_failures": critical_failures,
        "caps_applied": caps,
        "manual_review_required": bool(review or critical_failures),
        "manual_review": review,
        "scope": "deterministic declared criteria only; not a semantic judge",
    }


def score_user_test_v1(answer: str, scorer_config: Mapping[str, Any]) -> dict[str, Any]:
    """Historical scorer retained for explicit v1 artifacts and rescoring."""
    return _score_user_test(answer, scorer_config, revision="user_contract_v1", strict_terminal_json=False, word_boundaries=False)


def score_user_test(answer: str, scorer_config: Mapping[str, Any]) -> dict[str, Any]:
    """Current v2 scorer for newly discovered YAML tasks."""
    return _score_user_test(answer, scorer_config, revision="user_contract_v2", strict_terminal_json=True, word_boundaries=True)


__all__ = [
    "MAX_FILE_BYTES", "MAX_PROMPT_CHARS", "MAX_TESTS", "SUPPORTED_CRITERIA",
    "UserTestError", "load_user_tests", "parse_user_test_yaml", "score_user_test", "score_user_test_v1", "validate_user_test",
]
