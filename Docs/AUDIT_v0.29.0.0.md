# BULL v0.29.0.0 release audit

## Scope

PK1.0–PK1.5: data/engine separation, optional independent packs, shared storage,
single-version selection, author workspaces, complete private run snapshots,
public coverage provenance, bilingual documentation and packaging.

## Verification contracts

- Full offline regression: 518 checks, including malicious ZIP, bounds, consent,
  fixture mismatch, immutable versions, snapshot corruption and removal/update resume.
- Golden contracts: 16 existing definitions and 15 complete scorer results.
- Source and staged privacy audits; no user library, author workspaces, exports,
  keys, connections, chats, benchmark outputs or local logs in the release.
- UTF-8 and forced cp1251 gates, PowerShell 5.1 encoding and parse checks.
- Canonical brand checksum; exact release-version launchers and splash.
- Manifest, staged payload and ZIP hashes independently verified by Build-Release.ps1.
- Unpacked release regression and offline startup integration.

The release manifest records automated gate outcomes. The separate SHA-256 file
is authoritative for the whole archive; no self-referential archive hash is embedded here.

## Boundaries

Synthetic/offline verification is not a live Ollama, SSH/WAN or GPU acceptance
test. No user backend or router is modified by the audit. Pack checksums are
integrity evidence, not signatures or domain validation. Existing engine CODE
checks and chat execution are not OS-sandboxed; disposable environments remain
required for untrusted code. IDs and model labels require human review before sharing.

Linux, isolated author executors, separated model/test configuration and creative
LLM-judge evaluation remain roadmap work. Public publication requires an explicit request.
