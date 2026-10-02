# UserTests

Put reusable personal tasks in this directory. BULL discovers them when you
open **Compare models → My tasks and prompts → Task from UserTests**.

- Copy `simple_prompt.example.txt` to `my_task.txt` for a prompt-only test.
  BULL runs it on every selected model and reports speed, but does not invent a
  quality score. Compare the answers manually.
- Copy `structured_task.example.yaml` to `my_task.yaml` when the answer has
  deterministic facts or a terminal JSON contract that BULL can verify.

Read `Docs/USER_TESTS.md` before writing YAML criteria. Unsupported or invalid
files are isolated and shown as validation errors; they do not execute code.

