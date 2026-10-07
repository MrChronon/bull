# Benchmarks and user-owned tests

[Reading live output, top-three places and HTML charts](RESULTS.md)

## What BULL separates

- **Native model quality** scores the model's first answer.
- **Final system quality** scores the result after permitted client assistance.
- **Recovery metrics** describe retries, finalizers, restarts, and transport work.
- **Performance metrics** describe load, generation speed, latency, GPU, and VRAM.

These spaces must not be collapsed into one score. Generation completion,
required task structure, and terminal JSON/schema validity are also separate facts.

## Standard comparison

Use at least three comparable seeds for a decision. BULL reports mean, sample SD,
min/max, worst seed, rank stability when available, and uncertainty-aware Pareto
status. Warm runs are classified from observed load duration, not seed position.
Job-level counterbalancing reduces test/model-order effects for new runs.

The terminal and HTML report provide transparent relative choices:

- Quality;
- Speed, subject to a quality/task gate;
- Balance;
- Low memory;
- custom weights for quality, speed, reliability, and memory.

These choices apply only to the compared models and conditions in that report.
Unknown VRAM is not treated as low usage: the **Low memory** choice remains
unavailable until the report has comparable memory measurements.

## Sampling source and strict comparison

**Benchmark settings** is the default: BULL sends one explicit sampler setup to
every selected model. Use it when the question is which model performs best
under the same runtime settings.

**Ollama profile settings** reads every model's current Modelfile through
`/api/show` and deliberately does not send sampler options in the request.
Differences in `temperature`, `top_p`, penalties, mirostat and other inherited
sampler fields are reported as **profile-owned differences**. They are not a
sampling experiment and do not fail strict fair comparison; context, threads,
output limit, reasoning mode, recovery and prompt still have to match. Missing
Modelfile fields remain `backend_default_unresolved` rather than being guessed.
Use this mode to assess models with their own profiles, not to claim that they
used identical sampler settings.

**Per-model settings** is an explicit sampler experiment. Each edited field is
recorded as experimental and must actually vary between selected models.

## `.txt` user task

Place one UTF-8 prompt in `UserTests/name.txt`. BULL runs the unchanged prompt
across selected models, measures runtime, and stores answers. No automatic quality
score is created because no deterministic contract was supplied.

Use `.txt` for exploration, creative work, consultation, or a new task whose
success criteria are not yet formalized.

`UserTests` contains three self-contained synthetic examples: field extraction,
a structured calculation, and business translation. Their names contain
`.example.`, so BULL never runs them until you copy and rename one.

## `.yaml` user test

A structured test uses the safe `bull-user-test` version 1 format. New files use
the strict `user_contract_v2` scorer; historical `user_contract_v1` results keep
their recorded behavior and are never silently rescored. The parser
accepts no custom tags, anchors, aliases, executable code, or regular expressions.
The file limit is 256 KiB; the prompt limit is 50,000 characters; one to twenty
criteria are allowed; criterion weights must total exactly 100.

Supported criteria:

| Type | Pass condition | Required fields |
| --- | --- | --- |
| `contains_all` | every phrase appears, case-insensitive | `values` |
| `contains_any` | at least one phrase appears | `values` |
| `forbidden_any` | none of the forbidden phrases appears | `values` |
| `word_count` | word count is inside the inclusive range | `min`, `max` |
| `terminal_json_equals` | a JSON-path value equals the expected value | `path`, `expected` |
| `terminal_json_number` | a numeric JSON-path value is within tolerance | `path`, `expected`, exactly one tolerance |

For `terminal_json_number`, specify exactly one of `tolerance_abs` or
`tolerance_pct`. Nested paths such as `result.max_stress_mpa` are supported.

`critical: true` caps the automatic score at 59% when that criterion fails. Use
it only when the failure makes the answer unusable for the stated task.

`manual_review` lists important questions that the deterministic rules cannot
evaluate honestly. It receives no hidden numerical weight and explicitly marks
the result for human review.

For `terminal_json_*`, `BENCHMARK_RESULT` must be followed by the final JSON
value and no trailing prose. Equality is type-strict: JSON `true` is not numeric
`1`. A declared JSON path validates that value only; it does not validate an
entire object schema.

Example:

```yaml
schema: bull-user-test
version: 1
id: my_calculation
title: My calculation
description: One reproducible synthetic task
language: en
prompt: |
  Calculate the value from the supplied data.
  Explain the method and return result.value in terminal JSON.
criteria:
  - id: numeric_result
    type: terminal_json_number
    description: Result is inside a predeclared tolerance
    weight: 100
    path: result.value
    expected: 42
    tolerance_abs: 0.1
    critical: true
manual_review:
  - Check the method and assumptions.
```

When terminal JSON is required, BULL appends only the technical output contract
to the effective prompt. The source file, hashes, and exact effective prompt are
recorded in the checkpoint.

## Authoring rules

1. Test one work task, not an entire profession.
2. Supply every input, unit, symbol, and allowed assumption.
3. Separate content requirements from output format.
4. State what must not be assumed or invented.
5. Predeclare numeric references and tolerances before viewing model answers.
6. Use synthetic or distributable data and no secrets or personal information.
7. Give each criterion one unambiguous question.
8. Let weight reflect real task impact, not ease of automation.
9. One-word literal criteria use Unicode word boundaries: `you` is not found
   inside another word. They remain literal checks, not linguistic evaluation.
9. Do not treat keyword presence as proof of correct reasoning.
10. Put non-deterministic qualities under `manual_review`.

Start with a quick run, inspect false positives and negatives, then use three
seeds. Changing a prompt or scorer creates a new test version; never reinterpret
old results silently.

## Results and sharing

The concise terminal summary and HTML report are derived from the same saved
records. Summary JSON and HTML are intended for controlled sharing. Raw JSON,
checkpoints, private evidence, model answers, prompts, endpoints, and paths may
contain sensitive data and require review.

Built-in benchmark packs are versioned and hash-checked. A data-only pack cannot
execute Python. Promotion from candidate to stable requires validation, golden
snapshots, scorer regression tests, false-positive/negative review, and a versioned
methodology decision.
