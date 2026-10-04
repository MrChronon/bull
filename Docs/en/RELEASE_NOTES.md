# BULL v0.28.0.2 — Clear Choice

This release improves the trustworthiness of choosing among installed local
models. It does not change built-in benchmark prompts, built-in scorers, or the
inference and recovery runtime pipeline.

## Highlights

- Equal decision utilities display equal candidates instead of selecting a name
  arbitrarily.
- Native score mean and a conservative lower 95% confidence bound are clearly
  separate values.
- Missing VRAM is shown as unknown; **Low memory** stays unavailable without
  comparable measurements.
- New YAML tasks use strict `user_contract_v2`; old v1 artifacts remain readable
  without silent rescoring.
- Three synthetic, self-contained examples are included for extraction,
  structured calculation, and business translation.
- Startup verification now uses a separate native desktop window. It shows the
  versioned BULL image, the observed stage, and the exact offline
  regression-suite file, then closes before the terminal menu; it cannot colour
  the terminal background. BULL Red is the default theme and Matrix BULL is the
  green alternative.

The public bundle contains no models, chats, benchmark results, runtime state,
private connections, keys, tokens, endpoints, or local logs.
