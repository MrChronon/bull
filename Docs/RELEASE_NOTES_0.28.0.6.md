# BULL v0.28.0.6 — Clearer benchmark decisions

This release makes a benchmark result easier to inspect. Built-in benchmark prompts, scorers, recovery behaviour and the inference runtime are unchanged.

## What changed

- Terminal results now start with measured top-three places for Native quality,
  warm generation speed, observed VRAM peak and a transparent balance profile.
- A recommendation is no longer confused with a place in a measurement: quality
  and task-contract gates are shown separately, including why a profile has no
  eligible model.
- Each saved run adds a provisional summary for the current test only; it never
  claims an overall winner while the suite is still running.
- Live progress can show aggregate CPU/RAM with GPU/VRAM; unavailable sensors
  remain unavailable rather than becoming zero.
- The self-contained HTML report was redesigned in the BULL red palette. It
  includes numeric quality-throughput and task-time charts, top-three cards,
  resource views, test heatmaps, parameter provenance and test descriptions.

## Install

1. Verify and extract `BULL-v0.28.0.6-Bundle.zip`.
2. Run `Install-BULL-v0.28.0.6.cmd`.
3. Start `BULL-v0.28.0.6.cmd`.
