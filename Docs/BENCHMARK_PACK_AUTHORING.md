# BULL Benchmark Pack Authoring Guide

Current contract: **BULL v0.29.0.1 Pack Library**, pre-release for user testing.
Updated **11 October 2026**; publication and manual acceptance are separate.

Versioned benchmark packs let BULL discover a new safe task without editing the
central client. A pack is data, not a plug-in: it can select only runner, scorer
and verifier IDs implemented and allowlisted by the installed BULL engine.

## Locations

The production catalog uses one explicitly selected version from the shared
Windows library `%LOCALAPPDATA%/BULL/BenchmarkPacks`. It does not aggregate packs
from the application tree or use an embedded fallback.

- Installed public/private versions: `Installed/public/<id>@<version>/` or
  `Installed/private/<id>@<version>/` under the shared library.
- Editable author sources: `Workspaces/`; built ZIPs: `PackExports/` under that library.
- Optional base archives shipped with BULL: `BasePacks/*.zip`. The source
  `BenchmarkPacks/<pack>/` directories are maintained build/reference inputs,
  not automatically installed or discovered production tasks.
- `Runtime/BenchmarkPacks` is a historical registry location, not the current
  import destination. Do not place a new pack there expecting it to become runnable.

Install a ZIP through **Home → Test settings**, then select its exact version and
all or selected tasks. `public` / `private` classify intended distribution; neither
uploads anything. User library contents and Runtime never enter a public release.
See [library rules](PACK_LIBRARY_SPEC.md) and the
[English](en/PACK_LIBRARY_GUIDE.md) / [Russian](ru/PACK_LIBRARY_GUIDE.md) workflow.
For cloud LLM drafting, supply the entire paired instruction
([EN](en/PACK_AUTHOR_LLM.md), [RU](ru/PACK_AUTHOR_LLM.md)) and Author Workshop guide
([EN](en/AUTHOR_WORKSHOP.md), [RU](ru/AUTHOR_WORKSHOP.md)).

## Required files

```text
<pack>/
  manifest.json
  cases.json                 # or a manifest-owned cartesian_v1 generator
  gold.json
  pack.lock.json
  README.md
  LICENSE.txt                # name may differ when declared in the manifest
```

Executable files, links and import paths are rejected. In particular, a pack
cannot contain or launch Python, PowerShell, shell, JavaScript, DLL or EXE code.

## Manifest v1

The authoritative JSON Schema is
`Schemas/bull_benchmark_pack_manifest_v1.schema.json`. Required identity fields
are `id`, dotted `version`, `title`, `description`, `status` and `visibility`.
Lifecycle status is one of:

- `experimental` — unstable development pack;
- `candidate` — content frozen for validation;
- `stable` — approved reproducible pack;
- `deprecated` — readable and runnable, but superseded;
- `retired` — discoverable only when explicitly requested and not runnable.

The manifest must also declare an engine version range, license, provenance,
taxonomy, case source, gold file and documentation. Every referenced path is
relative to the pack root; absolute paths and `..` are forbidden.

## Case v1

Each case contains exactly:

```json
{
  "id": "safe_task",
  "version": 1,
  "category": "custom",
  "runner_ref": "single_turn_v1",
  "scorer_ref": "none",
  "verifier_ref": "benchmark_contract_v1",
  "definition": {
    "version": 1,
    "category": "custom",
    "score_type": "none",
    "prompt": "Return exactly OK."
  }
}
```

The three references are identifiers, never module names. Unknown references
fail validation before any inference. `definition.version`, category and scorer
must agree with the case envelope. Prompts are size-limited.

## Gold snapshots and lock

`gold.json` freezes, for every case, the canonical definition hash and the raw
UTF-8 hashes of `prompt` and `result_instruction`. `pack.lock.json` binds the
manifest, content, gold and compiled pack hashes. JSON hashes use sorted,
compact, finite canonical JSON; formatting and key order do not change them.

After editing a development pack, regenerate its lock through the registry API
or an engine-owned build tool. Never edit hashes by hand for a stable pack.
`Tools/build_chat_core_pack.py` is the reproducible reference builder for the
bundled CHAT Core.

For normal author work, `Tools/build_author_pack.py` compiles declared YAML/TXT
sources into `user_contract_v2` / `none`, validates positive/negative fixtures,
and generates manifest/gold/lock. It neither installs nor publishes the ZIP.
Edit a workspace and release a new explicit version; never edit installed content
in place. A hash proves identity, not the truth of a domain reference.

## Deterministic generator

Manifest v1 optionally supports only `cartesian_v1`. It expands a data template
over sorted variable names and declared value order. Expansion is bounded by the
registry case limit and its canonical output hash is stored in the manifest.
No expressions, random source, filesystem access or code execution are allowed.

## Validation in BULL

From Home or Chat, after explicitly installing the pack:

```text
/bench pack list
/bench pack validate
/bench pack validate bull_chat_core@1.0.0
/bench pack inspect bull_chat_core@1.0.0
```

`inspect` prints metadata, references and hashes but not prompts or gold answers.
An explicit target requires `ID@VERSION`; the current engine never guesses the
latest version. `validate` without a target checks the whole installed library
and fails if any entry is invalid. The library can still display invalid entries;
they cannot be selected. A run validates its selected exact pack/subset before
backend access; an unrelated invalid entry does not supply a fallback or replace
the selection. Duplicate pack identities and duplicate case IDs are errors.

## Promotion checklist

1. Start as `experimental` with explicit provenance and license metadata.
2. Validate content, gold and lock on a clean checkout.
3. Add deterministic positive and negative fixtures.
4. Freeze prompts and scorer references before `candidate`.
5. Confirm repeated compilation produces the same hash.
6. Promote to `stable` only with review and release notes.
7. Deprecate or retire by a new version; never rewrite an already published pack.
