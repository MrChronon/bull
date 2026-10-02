# BULL v0.27.0.0 — Simple Experience

v0.27 makes the terminal application easier to learn and turns benchmark output
into an immediate model-selection aid. Existing expert and experimental
capabilities remain available, but no longer compete with the main workflow.

## Highlights

- Four-action Home screen: Compare models, Chat, Connection, More.
- Two-level benchmark flow with a standard comparison as the primary action.
- Agent Lab, GPU Lab, manual server setup, and exact commands moved to advanced
  or experimental menus.
- Compact BULL mark on every navigational page.
- Concise terminal results without leaving the application.
- Model-choice markers for Quality, Speed, Balance, and Low memory.
- Custom decision weights for quality, speed, task completion, and VRAM.
- Relative two-dimensional Native quality/speed map in terminal and offline HTML.
- Explicit export guidance for HTML, summary JSON, share-safe evidence, and
  privacy-sensitive raw JSON.

## User-owned tests

The new `UserTests` directory supports two deliberately different levels:

- `.txt`: one UTF-8 prompt, runtime comparison, and manual answer review. BULL
  does not invent an automatic quality score.
- `.yaml`: schema `bull-user-test`, version 1, with a safe data-only subset and
  deterministic declared criteria.

Supported YAML checks are `contains_all`, `contains_any`, `forbidden_any`,
`word_count`, `terminal_json_equals`, and `terminal_json_number`. Weights must
sum to 100. A criterion marked `critical: true` caps the automatic score at 59%
when it fails. `manual_review` has no hidden numeric weight.

The loader does not execute Python, shell commands, YAML tags, anchors, aliases,
or regular expressions. Invalid files are isolated before inference. See
`Docs/USER_TESTS.md` and the templates in `UserTests`.

## How recommendations work

Decision profiles reuse already computed Native quality, warm speed, task
completion, and VRAM metrics. They never rescore model answers. Speed-led
profiles require Native quality of at least 60%, within ten percentage points of
the best comparable result, and at least 80% task completion when available.
Recommendations are relative to one run and are not a universal leaderboard.

## Compatibility and scope

- Built-in benchmark prompts and scorers are unchanged.
- Recovery and inference runtime behavior are unchanged.
- Existing Agent, GPU, backend, profile, resume, and command workflows remain.
- Historical artifacts remain readable through the compatibility layer.
- BULL still targets Windows 11 with Python, PowerShell, Ollama, and llama.cpp.

## First run

1. Verify and extract `BULL-v0.27.0.0-Bundle.zip`.
2. Run `Install-BULL-v0.27.0.0.cmd`.
3. Start `BULL-v0.27.0.0.cmd`.
4. Choose English or Русский.
5. Select **Compare models** and use the standard comparison, or put a copied
   template in `UserTests` for a task-specific comparison.

Do not publish `Runtime`, `Benchmarks`, `Chats`, private keys, or raw benchmark
JSON without reviewing it. HTML and share-safe evidence exclude raw prompts and
answers by design.
