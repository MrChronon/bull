# BULL v0.28.0.0 — Clear Choice

v0.28 makes model selection and user-owned checks more trustworthy without
changing built-in benchmark prompts, built-in scorers, or the inference and
recovery runtime pipeline.

## What changed

- Decision profiles no longer choose a model by name when utilities are equal:
  the report shows equal candidates instead.
- Native score mean and a conservative lower 95% confidence bound are distinct
  fields. The latter is used only as a cautious decision input, never displayed
  as the measured score.
- Unknown VRAM remains unknown. The **Low memory** profile is unavailable until
  comparable memory measurements exist.
- New YAML tasks use `user_contract_v2`: JSON booleans are not numbers, and a
  `BENCHMARK_RESULT` JSON value must be the final content of the answer.
- Historic `user_contract_v1` artifacts remain readable with their recorded
  behavior; they are not silently rescored.
- `UserTests` now includes three safe, self-contained synthetic templates for
  field extraction, a structured calculation, and business translation.
- The v0.28 startup screen has new versioned red BULL artwork and displays only
  observed startup-verification stages.

## What did not change

Built-in benchmark prompts, scorers, model-native versus client-recovery metric
separation, and inference runtime behavior are unchanged.

## First run

1. Verify and extract `BULL-v0.28.0.0-Bundle.zip`.
2. Run `Install-BULL-v0.28.0.0.cmd`.
3. Start `BULL-v0.28.0.0.cmd`.
4. Use **Compare models** for the standard suite, or copy a `.example.*` file
   in `UserTests` to a new name for a task-specific comparison.

Share-safe evidence and offline HTML exclude prompts and raw answers. Review
model labels before sharing, and never publish `Runtime`, `Benchmarks`, `Chats`,
keys, endpoints, or raw benchmark JSON.
