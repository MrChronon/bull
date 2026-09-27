# BULL v0.24.0.0 — аудит этапа T3

## Scope

T3 introduces a safe data-only benchmark registry and moves the frozen CHAT Core
through it. Runtime transport, prompts, scorers, recovery and execution order are
outside this change.

## Closed findings

- manifest, case, gold and lock contracts are versioned and strictly validated;
- canonical compilation and hashes are deterministic;
- public and private roots enforce matching visibility;
- lifecycle includes experimental, candidate, stable, deprecated and retired;
- arbitrary code, links, traversal and non-allowlisted references are rejected;
- duplicate pack identity and case ID are fail-closed;
- engine compatibility and case envelope/definition versions are checked;
- the CHAT Core pack equals all 12 legacy definitions by canonical hash;
- a private safe task is discovered without editing the central client;
- list, validate and inspect commands do not print prompt bodies;
- validation runs before benchmark inference;
- Windows PowerShell 5.1 startup is parse-tested with an ASCII-only launcher.
- release exclusions apply to private root data only, so `Shared/bull_llm/runtime`
  cannot be removed from an extracted ZIP;
- the real Client installer branch creates shortcuts in an isolated integration test;
- all PowerShell files are ASCII-only or carry a UTF-8 BOM;
- no release path uses the old product prefix and no runtime import uses the removed
  duplicate shared package.
- the full-colour terminal Chafa brand mark is bounded, permits only ANSI SGR colour controls,
  is UTF-8 startup-tested and rendered once per process;
- OpenSSH aliases are resolved without shell execution and accept only bounded
  option-safe names, a direct route and an existing private `IdentityFile`;
- ProxyCommand/ProxyJump cannot be imported silently, and host-key trust is reused
  only after an exact match in OpenSSH `known_hosts`, including hashed entries;
- the alias flow retains the existing pinned per-connection known_hosts boundary
  and has offline regression for injection, trust and fingerprint fallback.

## Residual risks

- runners and scorers remain engine-owned; third-party executable extensions are
  intentionally unsupported in this stage;
- manifest validation is implemented without a third-party JSON Schema runtime,
  so the checked-in schema and validator require parity tests when changed;
- the monolithic client remains the active production path;
- live hardware and WAN behavior remain separate from offline release gates.

## Exit criteria

T3 is complete when registry negative tests, exact CHAT prompt snapshots,
deterministic compilation, normal and forced-cp1251 regressions, privacy audit,
manifest verification and ZIP integrity pass. No inference may begin with an
invalid installed pack.

## Public release candidate addendum · 2026-09-27

The final candidate was re-audited after field-data validation. The release now
counterbalances model, test and seed positions for new runs while preserving the
stored order of legacy checkpoints. Tested profiles are deduplicated by their
importable Client payload and never copy an evidence seed into ordinary chat.

The clean-install gate also runs all 349 offline checks under `python -S`.
This exposed and removed an accidental Pillow dependency in brand-image tests;
normal Windows Client startup now needs no third-party Python package. Markdown
links, PowerShell 5.1/cp1251 startup, privacy exclusions, manifest/staged hashes
and ZIP integrity are release gates.

Publication must use an audited extraction of the release ZIP. The development
workspace contains historical bundles and research evidence and is not a safe
`git add .` source. The owner selected the MIT License for the public repository;
third-party model, engine and pack licenses remain independent.
