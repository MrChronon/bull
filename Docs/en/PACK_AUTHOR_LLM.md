# Creating BULL test packs with a cloud LLM

[Русская версия](../ru/PACK_AUTHOR_LLM.md)

Use this instruction to commission a domain-specific test pack. The LLM drafts
tasks and assessment criteria; the owner validates them. It must not change BULL
code, execute model answers or certify real-world professional decisions.

## Availability

The editable formats work in v0.29.0.1 through [Author Workshop](AUTHOR_WORKSHOP.md):
offline fixture validation and source-to-ZIP building. Loose `UserTests` remain
a separate workflow. Generated sources are a draft until the actual builder
validates them and a person reviews domain references. Runnable packs use manifest v1, described in
`Docs/BENCHMARK_PACK_AUTHORING.md`.

When commissioning a runnable source project, give the LLM this entire document
and `AUTHOR_WORKSHOP.md`, or the generated starter files plus that guide. The
copyable instruction alone does not supply the complete workspace/fixture schema.

## 1. Supply a brief

Tell the LLM:

- domain and concrete decisions the comparison should help make;
- typical tasks, input sizes, language(s) and desired output;
- allowed assumptions, formulas, references, units and forbidden additions;
- what makes an answer unusable versus merely imperfect;
- whether automatic checks are meaningful or manual review is required;
- number and diversity of tasks; intended quick or full assessment;
- known model/context limitations, without requiring a particular model brand;
- whether the pack is private or intended for redistribution, and data rights.

Use synthetic or explicitly permitted data. Remove names, secrets, endpoints,
account details and confidential documents before sending a brief to a cloud LLM.
Cloud authoring is a deliberate user action, not an automatic BULL connection.

## 2. Copy this author instruction

> You are preparing editable data-only tests for BULL. First identify missing
> information that would change the reference answer, domain assumptions or
> scoring. Ask focused questions; do not invent standards, citations or formulas.
>
> Design a representative set of independent, self-contained tasks, not repeated
> paraphrases of one example. Group them by skill and difficulty. A mixed-domain
> pack is allowed. Describe coverage and what is intentionally not measured.
>
> Use UTF-8 `.txt` for tasks without an honest deterministic score. Use the safe
> `bull-user-test` YAML contract below for tasks with machine-checkable criteria.
> No scripts, imports, API calls, regex rules, tools or executable payloads.
>
> Keep all inputs and requirements in each prompt. State units, rounding,
> assumptions, permitted evidence and response format. Do not include gold
> answers or criterion weights in the prompt sent to the tested model. An
> expected output schema is allowed; the computed answer is not a hint.
>
> Derive every expected value and tolerance independently from the inputs.
> Explain the derivation in review documentation, not in the tested prompt.
> If a reference cannot be verified, flag it for human review; do not label it
> correct or stable. Do not adjust criteria after seeing model outputs.
>
> For YAML, use only the six documented criterion types and weights summing to
> exactly 100. Put meaning, creativity, style and real-world applicability in
> `manual_review` when deterministic rules cannot measure them. Literal word
> matches are not proof of reasoning or semantic correctness.
>
> For each scored task provide a passing answer, a failing answer per critical
> criterion, a missing-field answer, and an invalid/trailing JSON example when
> JSON is used. State the expected failed checks and score/cap. Do not claim that
> fixtures were run unless you actually ran the installed BULL validator.
>
> Deliver editable sources, a user-facing README, provenance/license questions
> and review fixtures. Explain each task and its limitations in plain language.
> Do not add implementation diaries or comments about having edited a file.
> If asked for a runnable ZIP, use the supplied engine-owned builder and exact
> manifest contract. Never fabricate hashes, a lock, a download or a passing
> validation result. If no builder is supplied, hand over draft sources clearly.

For the PK1.4 builder, deliver exactly `author.json`, `fixtures.json`, `README.md`,
`LICENSE.txt`, and the declared `Tasks/*.yaml`, `.yml` or `.txt` files. Follow the
complete [workspace contract](AUTHOR_WORKSHOP.md); copy the generated starter
when available. Do not invent additional keys or include scripts and personal
notes. Each scored case needs a positive fixture and negative coverage of every
criterion with exact failed IDs and expected score fractions. Unscored cases have
no automatic score fixtures. Defaults must use only the documented parameter
allowlist. Never claim that cloud drafting itself performed local validation.

## 3. Supported editable formats

### Unscored text

One UTF-8 `.txt` file contains one full prompt. There is no automatic quality
number. Use it for initial exploration, creative work and tasks awaiting a
validated rubric. Compare answers manually and keep measured time/resources
separate from judgment. Do not add fake keyword checks just to obtain a ranking.

### Scored YAML

Top-level fields are `schema: bull-user-test`, `version: 1`, `id`, `title`,
`description`, `language`, `prompt`, `criteria` and optional `manual_review`.
IDs use lowercase ASCII letters, digits and underscores, start with a letter,
and contain 3–64 characters. Criterion IDs are unique within a task. Prompt uses
`prompt: |` with two-space-indented lines. Language can be `en`, `ru` or `auto`;
it describes the task, not the interface language or a semantic scoring claim.

Use spaces, not tabs. Use JSON-style lists/objects and quote strings where
needed. Avoid YAML tags, anchors, aliases, nested custom structures and inline
comments. Keep comments on their own lines. Current limits: 256 KiB per source,
50,000 prompt characters and 1–20 criteria. The v0.29.0.1 `UserTests` directory
loader also has a 100-task limit; this is not the future Pack Library contract.

Each criterion has `id`, `type`, `description`, `weight` and optional boolean
`critical`. Weight is positive, at most 100, and all weights sum to exactly 100.

| Type | Additional fields | What it actually checks |
| --- | --- | --- |
| `contains_all` | `values` | All declared literal phrases occur in prose |
| `contains_any` | `values` | At least one literal phrase occurs in prose |
| `forbidden_any` | `values` | None of the declared literal phrases occurs in prose |
| `word_count` | `min`, `max` | Prose word count lies within inclusive bounds |
| `terminal_json_equals` | `path`, `expected` | A declared JSON-path value equals the reference |
| `terminal_json_number` | `path`, `expected`, exactly one of `tolerance_abs` / `tolerance_pct` | Numeric result lies within the declared tolerance |

Phrase matching is case-insensitive; a single word uses Unicode word boundaries.
Prose checks exclude the terminal `BENCHMARK_RESULT` block. A forbidden phrase
can also occur in a correct denial: choose specific rules and test negatives.
`values` has 1–30 non-empty strings, each at most 500 characters. Word count must
use non-negative inclusive bounds, with `max` no more than 20,000. JSON paths are
dot-separated object keys, not array expressions or arbitrary code.

JSON checks require the final `BENCHMARK_RESULT` marker followed by one JSON
object and no additional text. BULL adds this technical instruction. Write the
required field names and units in the original prompt too. JSON boolean `true`
is not equal to number `1`; numeric comparisons should use JSON numbers, not
formatted unit strings. A path check does not validate every key in the object.
This contract does not provide an arbitrary JSON Schema criterion.

Numeric tolerance is inclusive. Percentage tolerance is
`abs(expected) * tolerance_pct / 100`; an expected value of zero therefore needs
an explicit absolute tolerance if a non-zero margin is intended. Choose the
margin before model testing from task accuracy, not from observed answers.

A failed critical check caps the score at **59%**; it does not always set it to
zero. Reserve `critical` for genuinely unusable answers. `manual_review` is a list
of up to 20 human review questions; it has no hidden numeric weight. A passing
machine score cannot certify those questions.

## 4. Self-contained example

```yaml
schema: bull-user-test
version: 1
id: ticket_extraction
title: Extract a synthetic ticket
description: Exact field extraction, not interpretation of a real support case
language: en
prompt: |
  Extract the ticket fields from this synthetic record.
  Record: ticket B-104; quantity 3; confirmation not received.
  Return result.id as a string, result.quantity as a number, and
  result.confirmed as a boolean. Do not assume confirmation.
criteria:
  - id: ticket_identifier
    type: terminal_json_equals
    description: Preserve the identifier exactly
    weight: 40
    path: result.id
    expected: B-104
  - id: ticket_quantity
    type: terminal_json_equals
    description: Preserve the declared quantity
    weight: 35
    path: result.quantity
    expected: 3
  - id: ticket_confirmation
    type: terminal_json_equals
    description: Do not invent confirmation
    weight: 25
    path: result.confirmed
    expected: false
    critical: true
manual_review:
  - If prose is supplied, check that it does not contradict the JSON.
```

Passing fixture: `BENCHMARK_RESULT` followed by
`{"result":{"id":"B-104","quantity":3,"confirmed":false}}` → 100% of declared
checks. Replacing `false` with `true` leaves 75% of raw criterion weights passing
but the critical failure caps the result at 59%. Appending prose after the JSON
fails all three terminal JSON criteria → 0%. Manual prose review is still separate.

## 5. Deliverables, review and packaging

Provide each task as a separate source file. Supply a README with pack title,
author, version, language/skill coverage, selected-task guidance, expected runtime
constraints, score meaning, critical failures, manual review and limitations.
Include input provenance and license information; BULL's MIT license does not
automatically license third-party datasets or an author's pack. Never invent a
source citation, permission or license. Keep answer fixtures/reference derivations
separate from prompts. They must not be sent as model context during a run.

Human acceptance checklist:

1. Independently verify references, calculations, units and ambiguous inputs.
2. Review coverage and duplicated tasks; one pack does not certify a profession.
3. Review critical failures, weights and tolerance justifications.
4. Validate every source and score the positive/negative fixtures offline.
5. Run a small smoke comparison, inspect raw answers, then use multiple seeds.
6. Freeze a candidate version before broad model comparisons.
7. Record changes in a new version; never rewrite installed/published versions.

The runnable pack uses `manifest.json`, `cases.json` (or an allowed data generator),
`gold.json`, `pack.lock.json`, README and license. The engine-owned build step
maps YAML to `user_contract_v2`, unscored text to `none`, preserves editable sources
and computes all content/gold/lock hashes. Hashes prove content identity, not the
truth of a reference answer. PK1.4 provides `Tools/build_author_pack.py` and the
Author Workshop menu. Validate sources, build outside the workspace, then import
the resulting ZIP explicitly. The existing registry format is authoritative.

Updates are explicit new versions; editing should take place in a working copy.
Packs may be distributed as ZIP from the author's chosen hosting, including
GitHub, or remain private. Executable checks, isolated custom scorers, model/test
configuration separation and local/remote LLM judging are future work, not
capabilities a generated pack may silently activate.
