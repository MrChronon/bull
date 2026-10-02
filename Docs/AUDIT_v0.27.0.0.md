# Public release audit — BULL v0.27.0.0

## Scope

The audit covers the Simple Experience terminal navigation, user-owned test
loader/scorer, decision-support summaries, report export boundaries, packaging,
documentation, and public-release privacy gates.

## Security properties

- User YAML is parsed by a bounded dependency-free subset; executable tags,
  anchors, aliases, regex, and code are unsupported.
- Maximum file, prompt, test, criterion, and string sizes are enforced.
- Invalid user files fail before inference and do not block valid siblings.
- `.txt` tasks never receive a fabricated quality score.
- Decision profiles consume existing metrics and cannot mutate benchmark scores.
- Raw benchmark JSON is labelled private; offline HTML excludes raw answers and
  prompts; share-safe evidence remains the preferred JSON export.
- Local/remote defaults, SSH host-key pinning, loopback inference APIs, redirect
  blocking, and secret-scrubbed child processes are preserved.

## Methodology boundaries

- Keyword criteria prove only declared string presence or absence, not semantic
  correctness.
- Numeric criteria are trustworthy only when the author independently verifies
  the expected value and tolerance.
- Custom decision weights express preference, not statistical certainty.
- A profile winner applies only to comparable models in the current run.
- Real WAN, GPU placement, and inference quality require hardware/model testing;
  offline regression cannot validate them.

## Release exclusions

`Chats`, `Runtime`, `Benchmarks`, `Exports`, local `Workspace` contents, private
keys, connection records, logs, caches, and generated release artifacts are not
included in the public source or bundle payload.

## Exit gate

- Python compile and complete offline regression pass.
- Forced-cp1251 and startup integration pass.
- English/Russian primary routes do not mix interface languages.
- Public-candidate audit finds no personal paths, endpoints, or secret patterns.
- Manifest hashes and release ZIP verify from a clean extracted directory.
