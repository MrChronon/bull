# BULL Benchmark Pack Authoring Guide

Versioned benchmark packs let BULL discover a new safe task without editing the
central client. A pack is data, not a plug-in: it can select only runner, scorer
and verifier IDs implemented and allowlisted by the installed BULL engine.

## Locations

- Public packs shipped with a release: `BenchmarkPacks/<pack>/`.
- User-owned private packs: `Runtime/BenchmarkPacks/<pack>/`.

`Runtime` is never included in a public release. A public root accepts only a
manifest with `visibility: public`; a private root accepts only `private`.

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

## Deterministic generator

Manifest v1 optionally supports only `cartesian_v1`. It expands a data template
over sorted variable names and declared value order. Expansion is bounded by the
registry case limit and its canonical output hash is stored in the manifest.
No expressions, random source, filesystem access or code execution are allowed.

## Validation in BULL

From the command menu or main screen:

```text
/bench pack list
/bench pack validate
/bench pack validate bull_chat_core@1.0.0
/bench pack inspect bull_chat_core
```

`inspect` prints metadata, references and hashes but not prompts or gold answers.
Any invalid installed pack makes discovery fail closed before benchmark
inference. Duplicate pack identities and duplicate case IDs are errors.

## Promotion checklist

1. Start as `experimental` with explicit provenance and license metadata.
2. Validate content, gold and lock on a clean checkout.
3. Add deterministic positive and negative fixtures.
4. Freeze prompts and scorer references before `candidate`.
5. Confirm repeated compilation produces the same hash.
6. Promote to `stable` only with review and release notes.
7. Deprecate or retire by a new version; never rewrite an already published pack.
