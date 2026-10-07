# BULL v0.28.0.7 — Clean Release

v0.28.0.7 consolidates the v0.28 benchmark experience into an audited public
bundle. It keeps the benchmark contracts stable while making results easier to
read during a run, in the terminal summary, and in the offline HTML report.

## What is new

- Separate Russian, English, and bilingual benchmark tracks make language
  quality and speed directly comparable.
- Terminal and HTML reports provide top-3 rankings, quality/speed maps, test
  heatmaps, stability ranges, resource views, and plain-language explanations.
- Live checkpoints show the completed test result, generation speed, and the
  available CPU, RAM, GPU, and VRAM telemetry.
- The HTML report is the recommended post-run view; JSON and CSV remain
  available for reproducible analysis.
- Ollama profile-owned sampler values are resolved before launch and recorded
  separately without weakening strict comparison of runtime settings.

## Integrity and privacy

- The public regression suite passes **401/401** checks.
- The audited ZIP contains **256** manifest-controlled files.
- Public names, paths, launchers, schemas, and documentation use BULL-only
  identifiers; obsolete product branding is not shipped.
- Chats, benchmark results, runtime state, connection profiles, keys, tokens,
  endpoints, personal paths, and local logs are excluded.
- The bundle includes a SHA-256 checksum for independent verification.

Download the v0.28.0.7 release and checksum from the repository's Releases page.
Read [Benchmarks](BENCHMARKS.md), [Results](RESULTS.md), and
[Security](SECURITY.md) before publishing benchmark evidence.
