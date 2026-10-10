"""Persistent explicit pack selection; no implicit bundle or latest fallback."""
from __future__ import annotations

import stat
from copy import deepcopy

from ..storage import atomic_json
from .catalog import definitions_from_packs, EXECUTABLE_SCORER_REFS
from .pack_library import PackLibrary, _directory, _lstat, _no_link
from .registry import PACK_ID_RE, VERSION_RE, PackValidationError, _load_json

STATE_SCHEMA = "bull-pack-library-state"
STATE_LIMIT = 256 * 1024


class PackSelection:
    def __init__(self, library: PackLibrary):
        self.library = library
        self.path = library.root / "library_state.json"

    def read(self):
        empty = {"schema": STATE_SCHEMA, "schema_version": 1, "onboarding_complete": False, "selection": None}
        if not _directory(self.library.root):
            return empty
        details = _lstat(self.path)
        if details is None:
            return empty
        _no_link(self.path, details)
        if not stat.S_ISREG(details.st_mode):
            raise PackValidationError("PACK_SELECTION_INVALID", "selection state must be a regular JSON file")
        state = _load_json(self.path, STATE_LIMIT)
        self._validate(state)
        return state

    @staticmethod
    def _validate(state):
        if (not isinstance(state, dict) or set(state) != {"schema", "schema_version", "onboarding_complete", "selection"} or
                state.get("schema") != STATE_SCHEMA or type(state.get("schema_version")) is not int or
                state["schema_version"] != 1 or type(state.get("onboarding_complete")) is not bool):
            raise PackValidationError("PACK_SELECTION_INVALID", "unsupported library state schema")
        selection = state["selection"]
        if selection is None:
            return
        keys = {"id", "version", "manifest_sha256", "compiled_sha256", "case_ids", "reason", "approved_code_cases"}
        if (not isinstance(selection, dict) or set(selection) != keys or
                not isinstance(selection["id"], str) or not PACK_ID_RE.fullmatch(selection["id"]) or
                not isinstance(selection["version"], str) or not VERSION_RE.fullmatch(selection["version"]) or
                selection["reason"] not in {"whole_pack", "user_subset"}):
            raise PackValidationError("PACK_SELECTION_INVALID", "invalid selected pack identity")
        for key in ("manifest_sha256", "compiled_sha256"):
            value = selection[key]
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise PackValidationError("PACK_SELECTION_INVALID", "invalid selection digest")
        ids = selection["case_ids"]
        if (not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids) or
                len(ids) != len(set(ids))):
            raise PackValidationError("PACK_SELECTION_INVALID", "selection needs distinct nonempty case IDs")
        approved = selection["approved_code_cases"]
        if (not isinstance(approved, list) or any(not isinstance(x, str) or x not in ids for x in approved) or
                len(approved) != len(set(approved))):
            raise PackValidationError("PACK_SELECTION_INVALID", "invalid code-check approval")

    def _save(self, state):
        self._validate(state)
        _directory(self.library.root, create=True)
        details = _lstat(self.path)
        if details is not None:
            _no_link(self.path, details)
            if not stat.S_ISREG(details.st_mode):
                raise PackValidationError("PACK_SELECTION_INVALID", "selection state must be a regular file")
        atomic_json(self.path, state)

    def finish_onboarding(self):
        state = self.read()
        state["onboarding_complete"] = True
        self._save(state)

    def select(self, pack_id, version, case_ids=None, *, allow_code_execution=False):
        pack = self.library.get(pack_id, version)
        if not pack.runnable:
            raise PackValidationError("PACK_NOT_RUNNABLE", "retired pack cannot be selected")
        all_ids = [case.id for case in pack.cases]
        ids = all_ids if case_ids is None else list(case_ids)
        if not ids or len(ids) != len(set(ids)) or any(x not in all_ids for x in ids):
            raise PackValidationError("PACK_SELECTION_INVALID", "select at least one distinct case from this pack")
        # Keep the author's declared order, independent of typed number order.
        ids = [x for x in all_ids if x in ids]
        state = self.read()
        state.update(onboarding_complete=True, selection={
            "id": pack.id, "version": pack.version,
            "manifest_sha256": pack.manifest_sha256, "compiled_sha256": pack.compiled_sha256,
            "case_ids": ids, "reason": "whole_pack" if len(ids) == len(all_ids) else "user_subset",
            "approved_code_cases": [case.id for case in pack.cases if case.id in ids and
                                    case.scorer_ref in EXECUTABLE_SCORER_REFS] if allow_code_execution is True else [],
        })
        self._save(state)
        return self.snapshot()

    def active_pack(self):
        selection = self.read()["selection"]
        if selection is None:
            return None
        pack = self.library.get(selection["id"], selection["version"])
        self._match(pack, selection)
        return pack

    @staticmethod
    def _match(pack, selection):
        if (not pack.runnable or pack.manifest_sha256 != selection["manifest_sha256"] or
                pack.compiled_sha256 != selection["compiled_sha256"]):
            raise PackValidationError("PACK_SELECTION_CHANGED", "selected version changed; select and review it again")
        all_ids = {case.id for case in pack.cases}
        if any(x not in all_ids for x in selection["case_ids"]):
            raise PackValidationError("PACK_SELECTION_CHANGED", "selected case is no longer available")

    def snapshot(self, case_ids=None):
        selection = self.read()["selection"]
        if selection is None:
            return None
        pack = self.library.get(selection["id"], selection["version"])
        self._match(pack, selection)
        ids = selection["case_ids"] if case_ids is None else list(case_ids)
        all_ids = [case.id for case in pack.cases]
        if not ids or len(ids) != len(set(ids)) or any(x not in all_ids for x in ids):
            raise PackValidationError("PACK_SELECTION_INVALID", "run cases must belong to one selected pack")
        code_cases = [case.id for case in pack.cases if case.id in ids and case.scorer_ref in EXECUTABLE_SCORER_REFS]
        return {**deepcopy(selection), "identity": pack.identity, "title": pack.title,
                "case_ids": ids, "total_cases": len(all_ids), "selected_cases": len(ids),
                "coverage": "full_pack" if set(ids) == set(all_ids) else "subset",
                "reason": "whole_pack" if set(ids) == set(all_ids) else "user_subset",
                "status": pack.status.value, "visibility": pack.visibility.value,
                "code_execution_cases": code_cases,
                "code_execution_approved": all(x in selection["approved_code_cases"] for x in code_cases)}

    def catalog_for_snapshot(self, snapshot):
        # Only exact identity/digests/cases bind execution. UI selection may have
        # changed since a checkpoint was created; it must never substitute it.
        pack = self.library.get(snapshot["id"], snapshot["version"])
        self._match(pack, snapshot)
        definitions = definitions_from_packs((pack,))
        ids = snapshot["case_ids"]
        if not ids or len(ids) != len(set(ids)):
            raise PackValidationError("PACK_SELECTION_INVALID", "checkpoint case selection is empty or ambiguous")
        required = {case.id for case in pack.cases if case.id in ids and case.scorer_ref in EXECUTABLE_SCORER_REFS}
        if required and (snapshot.get("code_execution_approved") is not True or
                         not required.issubset(set(snapshot.get("approved_code_cases") or []))):
            raise PackValidationError("PACK_CODE_PERMISSION_REQUIRED", "explicit approval is required for engine code checks")
        return {x: definitions[x] for x in ids}

    def clear(self):
        state = self.read()
        state["selection"] = None
        self._save(state)


class SelectedPackRegistry:
    """Existing client catalog protocol backed by one explicit library version."""
    def __init__(self, selection: PackSelection):
        self.selection = selection

    def discover(self, *, include_retired=False):
        if include_retired:
            findings = self.scan()
            invalid = next((row for row in findings if row.pack is None), None)
            if invalid:
                raise PackValidationError(invalid.error_code, invalid.error_message, invalid.path)
            return tuple(row.pack for row in findings)
        pack = self.selection.active_pack()
        return () if pack is None else (pack,)

    def scan(self):
        return self.selection.library.scan()

    def get(self, pack_id, version=None, *, include_retired=False):
        if version is None:
            raise PackValidationError("PACK_VERSION_REQUIRED", "specify an exact installed version")
        pack = self.selection.library.get(pack_id, version)
        if not include_retired and not pack.runnable:
            raise PackValidationError("PACK_NOT_RUNNABLE", "retired pack cannot be selected")
        return pack
