# BULL v0.28.0.3 — Exact startup checks

BULL v0.28.0.3 is a presentation and usability patch. Built-in benchmark prompts,
scorers, model-runtime options, recovery behaviour, and the separate
native/final quality metrics are unchanged.

## What changed

- The separate startup window now shows the exact active verification check,
  not only the regression-suite filename.
- Check names are emitted by the test harness immediately before execution;
  BULL does not derive a fictional per-test completion count.
- Contract suites such as security, GPU Lab and UX checks identify themselves
  when they begin.
- Status text remains localized while test identifiers stay intact.

## Install

1. Verify and extract `BULL-v0.28.0.3-Bundle.zip`.
2. Run `Install-BULL-v0.28.0.3.cmd`.
3. Start `BULL-v0.28.0.3.cmd`.

The startup window is presentation only. If Tk or Windows GUI facilities are
not available, the mandatory offline verification still runs and BULL opens in
the terminal.
