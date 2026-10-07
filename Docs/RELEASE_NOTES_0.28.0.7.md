# BULL v0.28.0.7 — Ollama Profile Comparison Fix

This patch fixes the **Ollama profile settings** option in Benchmark Lab.
Built-in benchmark prompts, scorers, recovery behaviour, and the inference
runtime are unchanged.

## What changed

- Strict fair comparison now permits sampler differences inherited from each
  selected model's Ollama Modelfile. They are retained in the evidence as
  `profile-owned differences`; context, threads, output limit, reasoning,
  recovery and prompt still must match.
- Missing Modelfile sampler values remain explicitly marked as
  `backend_default_unresolved`. BULL does not invent a default value.
- The comparison plan now resolves the current `/api/show` profile before it
  is shown, so it displays real profile values instead of misleading `None`
  placeholders.
- Per-model sampling experiments now declare every sampler field editable in
  the wizard, including `repeat_penalty`.

## Validation

The release passes 400 offline regression checks, Python compilation, forced
cp1251 validation, public-data audit, manifest verification, and ZIP integrity.

## Install

1. Verify and extract `BULL-v0.28.0.7-Bundle.zip`.
2. Run `Install-BULL-v0.28.0.7.cmd`.
3. Start `BULL-v0.28.0.7.cmd`.
