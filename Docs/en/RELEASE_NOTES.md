# BULL v0.28.0.5 — Clear Benchmark Flow

This patch makes benchmark setup clearer and adds live host-resource context. It
does not change built-in benchmark prompts, built-in scorers, or the inference
and recovery runtime pipeline.

## Highlights

- Comma-separated model selection accepts spaces, such as `2, 4, 7`.
- Sampling-source selection opens on its own clean screen after the preset.
- Live progress shows optional aggregate CPU and RAM beside GPU and VRAM.
- Every saved run prints a short checkpoint with result, speed and available
  resources before the suite completes.

The public bundle contains no models, chats, benchmark results, runtime state,
private connections, keys, tokens, endpoints, or local logs.
