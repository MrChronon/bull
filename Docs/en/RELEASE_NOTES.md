# BULL v0.28.0.6 — Clearer benchmark decisions

This release improves how BULL presents benchmark evidence. It does not change
built-in benchmark prompts, scorers, recovery behaviour or inference runtime.

## Highlights

- Measured top-three places for Native quality, warm speed, observed VRAM and
  balance.
- Recommendations clearly separated from rankings: the report states the
  quality/task gate and why a profile is unavailable.
- A short, provisional current-test summary after every saved run.
- Live host telemetry for GPU/VRAM and, when available, aggregate CPU/RAM.
- A redesigned self-contained red BULL HTML report with charts, resource views,
  rankings, test descriptions and parameter provenance.

Read [Results](RESULTS.md) before using a report to choose a model.

The public bundle contains no models, chats, benchmark results, runtime state,
private connections, keys, tokens, endpoints, or local logs.
