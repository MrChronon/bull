# BULL v0.28.0.5 — Clear benchmark flow

This patch makes the benchmark path clearer and adds live host-resource context.
Built-in benchmark prompts, scorers, recovery behaviour, inference runtime, and
the separate native and final quality metrics are unchanged.

## What changed

- Comma-separated model selections now tolerate spaces, for example `2, 4, 7`.
- The sampling-source choice opens on a clean screen after preset selection.
- Live benchmark output can show CPU and RAM beside GPU and VRAM, when the
  selected host exposes those measurements.
- Each saved run prints a concise checkpoint: score or contract result, speed,
  and available resource measurements. Final terminal and HTML summaries remain
  the source for model selection.

## Install

1. Verify and extract `BULL-v0.28.0.5-Bundle.zip`.
2. Run `Install-BULL-v0.28.0.5.cmd`.
3. Start `BULL-v0.28.0.5.cmd`.
