# BULL v0.28.0.7 — Ollama Profile Comparison Fix

Benchmark Lab now compares models using their Ollama Modelfiles without
mistaking inherited sampler differences for a broken strict comparison.
Built-in prompts, scorers, recovery behaviour and inference runtime are
unchanged.

- Profile-owned sampler differences are shown separately in the evidence.
- Context, threads, output limit, reasoning, recovery and prompt remain strict.
- The pre-run plan resolves `/api/show` first, so it shows actual profile values.
- The release passes 400 offline regression checks.

Read [Benchmarks](BENCHMARKS.md) before choosing a sampling source. The public
bundle contains no models, chats, benchmark results, runtime state, private
connections, keys, tokens, endpoints, or local logs.
