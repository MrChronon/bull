# BULL v0.28.0.1 — Startup presentation hotfix

v0.28.0.1 fixes the visual startup behaviour reported for v0.28.0.0. It does
not change Built-in benchmark prompts, scorers, model-runtime options, recovery
logic, or the separation of native and assisted quality metrics.

## What changed

- Startup verification now appears in a compact independent desktop window,
  rather than being drawn into the terminal.
- The window shows the release image, version, and the three real verification
  stages. It disappears before the terminal connects to a backend or draws the
  main menu.
- The terminal reset path now clears foreground and background ANSI state,
  preventing a red splash palette from leaking into ordinary screens.

## First run

1. Verify and extract `BULL-v0.28.0.1-Bundle.zip`.
2. Run `Install-BULL-v0.28.0.1.cmd`.
3. Start `BULL-v0.28.0.1.cmd`.

The desktop splash is optional presentation only. If Tk/Windows GUI facilities
are unavailable, the mandatory offline verification still runs and BULL starts
in the terminal.
