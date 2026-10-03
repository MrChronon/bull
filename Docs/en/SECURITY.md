# Security and privacy

## Trust boundaries

BULL is a local application, not a hosted service. It trusts the user-selected
Python/PowerShell environment, inference engine, installed models, and files the
user deliberately supplies. Model output, imported connection files, benchmark
packs, generated code, and third-party model files are untrusted inputs.

## Safe defaults

- a clean build starts in local mode and contains no private server;
- remote inference uses a pinned SSH tunnel and a loopback-only inference API;
- private key bytes are never copied into a connection profile;
- HTTP redirects are blocked before forwarding authorization headers;
- external plain HTTP is rejected by default;
- connection failure never silently changes the selected backend;
- benchmark artifacts are written atomically and resume preserves completed runs.

## Secrets and private state

Never commit or publish:

- `Runtime`, `Chats`, `Benchmarks`, `Exports`, or `Workspace`;
- `client_debug.log` or generated diagnostic logs;
- private SSH keys, passwords, tokens, API keys, or `.env` files;
- personal endpoints, usernames, router exports, or connection JSON containing
  real infrastructure;
- raw prompts, responses, attachments, or evidence without review.

The public release gate scans manifests, names, extensions, content, archives,
paths, connection defaults, and generated ZIP files. It does not replace a human
review of data the user chooses to publish later.

## SSH identity

Verify the server fingerprint through an independent channel. BULL pins a
per-connection host key. A mismatch is a stop condition, not a warning to ignore.
Use a dedicated key and non-administrator account. A remembered address-book
entry stores the key path, not key bytes. Removing the entry does not revoke the
key on the server.

## Internet exposure

Prefer VPN. If direct SSH is required, forward one external TCP port to Windows
OpenSSH and leave Ollama/llama.cpp on loopback. Do not use router DMZ or UPnP.
Apply operating-system updates, key-only authentication, firewall restrictions,
and log monitoring before unattended remote access.

## Model output and tools

Language-model output is data, not authority. Generated-code execution and chat
tools run with the current user's operating-system rights and are not a secure
sandbox. Use a disposable VM without credentials or network access for untrusted
code. Review every destructive or external action.

User YAML tests and public benchmark packs are data-only. Unsupported constructs
are rejected; they do not become executable Python. Legacy CODE-style evaluation
still requires an isolated environment.

## Reports

The standalone HTML report loads no external resources, but its contents may
still reveal model names, prompts, answers, local paths, or experiment details.
Share-safe output reduces exposure; it does not certify a file as anonymous.

## Incident response

If a key, token, or endpoint is exposed:

1. revoke or rotate it at the authoritative service;
2. remove the public key from `authorized_keys` when SSH access is affected;
3. review server and router logs;
4. delete the secret from working copies and repository history as appropriate;
5. rebuild from a clean checkout and run the public release gate;
6. disclose the affected release and remediation without publishing the secret.

Report security issues privately when public disclosure would increase risk.

