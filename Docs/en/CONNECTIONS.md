# Connections

## Choose the simplest route

| Models run on | BULL menu | Required setup |
| --- | --- | --- |
| This computer | Connection settings → Local Ollama | Start Ollama locally |
| Known server | Connection → Saved server | Select the saved entry |
| Server with working OpenSSH alias | Connection → New server from SSH alias | `ssh ALIAS` works |
| New server | Connection → New server manually | Address, user, key, verified fingerprint |

BULL never silently falls back from the selected server to another backend.
Failed connections preserve their settings.

## Local Ollama

Start Ollama and choose **Local Ollama**. BULL uses loopback and does not open an
SSH connection. Install models and the server separately from BULL.

## SSH alias

Create a dedicated key on the client:

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\bull_access" -C "BULL client"
```

Add only `bull_access.pub` to the server user's `authorized_keys`. Keep the
private `bull_access` file on the client. Then add an OpenSSH entry:

```text
Host bull-home
    HostName SERVER_ADDRESS
    User SERVER_USER
    Port 22
    IdentityFile ~/.ssh/bull_access
    IdentitiesOnly yes
```

Test `ssh bull-home` in PowerShell. In BULL choose **New server from SSH alias**
and enter `bull-home`. BULL resolves `HostName`, `User`, `Port`, `IdentityFile`,
and known-host files through `ssh -G` without executing a shell. `ProxyCommand`,
`ProxyJump`, option-like aliases, and missing private keys are rejected.

An exact OpenSSH `known_hosts` match can establish trust. Otherwise, verify the
SHA-256 host fingerprint independently on the server. Never trust a fingerprint
only because the same unverified network connection displayed it.

## Manual SSH

Enter a DNS name or IP address, SSH port, server user, existing private key, and
the independently verified Ed25519 host fingerprint. The wizard does not install
the server, edit a router, copy key bytes, or download models.

Choose whether to remember the connection for future BULL builds or keep it only
inside the current build. Remembered entries live in the user's private BULL
vault; build-local settings live under `Runtime`. Neither belongs in a release.

## Internet access

Prefer a VPN overlay such as WireGuard or Tailscale. For direct Internet SSH:

```text
PUBLIC_IP:EXTERNAL_TCP_PORT → SERVER_LAN_IP:22
```

Forward one TCP port only. Do not enable DMZ or UPnP and do not expose Ollama
`11434` or llama.cpp `8080`. Keep the inference API bound to loopback and access
it through the SSH tunnel. Test from a genuinely external network, such as a
mobile connection, before leaving the server unattended.

Use key-only authentication, a non-administrator account, host-key pinning, and
firewall rules appropriate to the server. Revoke access by removing the public
key from `authorized_keys`; deleting a BULL address-book entry does not revoke it.

## Diagnostics

**Connection settings → Check selected SSH server** tests the connection without
starting inference. Typical failures:

- timeout: address, external port, firewall, NAT, or VPN path;
- connection refused: OpenSSH or the target service is not listening;
- host-key mismatch: stop and verify the server identity;
- private key rejected: check `authorized_keys`, file permissions, user, and key;
- tunnel succeeds but models are absent: start Ollama and run `ollama list` on the server.

Connection errors shown in English never echo a legacy Russian backend message.
The original technical detail is retained in `client_debug.log`.
