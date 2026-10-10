"""Validated benchmark content boundary, independent of client/runtime code.

Only installed/explicitly supplied packs create runnable definitions. An empty
registry is valid; diagnostic fixtures are never used as a catalog fallback.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from .registry import LoadedPack, PackRegistry, PackValidationError, RegistryPolicy

# Capabilities belong to the engine, not to a pack's declarations. Historical
# scorers used by offline rescore remain outside this runnable-pack allowlist.
ENGINE_RUNNER_REFS = frozenset({"single_turn_v1"})
ENGINE_VERIFIER_REFS = frozenset({"benchmark_contract_v1"})
EXECUTABLE_SCORER_REFS = frozenset({"retention_d7_v5", "analytics_case_v3", "python_debug_v1"})
ENGINE_SCORER_REFS = frozenset({
    "none", "simpson_v3", "funnel_v3", "retention_d7_v5", "analytics_case_v3",
    "instruction_v4", "python_debug_v1", "structured_reference_v1",
    "groundedness_adversarial_v1", "ru_language_stress_v3",
    "ru_dialogue_contract_v1", "bilingual_language_contract_v1", "bilingual_language_contract_v2",
    "user_contract_v2",
})


def engine_registry_policy(engine_version: str) -> RegistryPolicy:
    return RegistryPolicy(
        engine_version=engine_version,
        runner_refs=ENGINE_RUNNER_REFS,
        scorer_refs=ENGINE_SCORER_REFS,
        verifier_refs=ENGINE_VERIFIER_REFS,
    )


def definitions_from_packs(packs: Iterable[LoadedPack]) -> dict[str, dict]:
    """Return independent definition copies with exact provenance.

    The aggregate form is a compatibility adapter for the existing client.
    Pack Library runs will supply exactly one explicitly selected version.
    Ambiguous case IDs (including two versions) are never silently overwritten.
    """
    result = {}
    sources = {}
    for pack in packs:
        if not pack.runnable:
            continue
        for case in pack.cases:
            if case.id in result:
                raise PackValidationError(
                    "DUPLICATE_CASE_ID",
                    f"{case.id} is declared by {sources[case.id]} and {pack.identity}",
                    pack.root,
                )
            # Do not share mutable criteria between preview and another run.
            definition = deepcopy(dict(case.definition))
            definition["_pack"] = {
                "identity": pack.identity,
                "manifest_sha256": pack.manifest_sha256,
                "compiled_sha256": pack.compiled_sha256,
                "definition_sha256": case.definition_sha256,
                "runner_ref": case.runner_ref,
                "scorer_ref": case.scorer_ref,
                "verifier_ref": case.verifier_ref,
            }
            result[case.id] = definition
            sources[case.id] = pack.identity
    return result


def catalog_from_registry(registry: PackRegistry) -> tuple[dict[str, dict], tuple[LoadedPack, ...]]:
    packs = registry.discover()
    return definitions_from_packs(packs), packs
