# Installing BULL

Current edition: v0.29.0.1 stable, 11 October 2026; manual acceptance is open.
The uninstalled archive has `Setup.exe`, not a root `BULL.exe`.

1. Verify the archive's SHA-256 and extract into a separate directory.
2. Run `Setup.exe` (bull with an install-arrow icon). Choose English or Russian,
   then **BULL Red** or **BULL Matrix**. Both choices apply to the remaining setup
   and are saved for BULL. `Setup.cmd` is a fallback entrypoint.
3. Install standard packs, import a ZIP via HTTPS link or local file, or continue
   without tests. Review the author and tasks before confirming.
   Standard installation selects the safe `bull_chat_core`.
4. Wait for the full internal regression: 668 checks without model inference.
   Failure offers retry or exit. Installation is not complete before verification.
5. Configure an existing connection or skip. Available routes are local Ollama,
   saved server, SSH alias and manual entry. llama.cpp is in advanced engine options.
6. After verification and connection setup/skip, Setup creates `BULL.exe` from
   its manifest-verified payload. Review readiness, then launch or exit.

Theme-coloured shortcuts are created on the Desktop and in the Start Menu. Administrator
rights are not required. If Python 3.10+ is missing, winget installation is
offered with separate confirmation. Setup does not provision servers, models,
OpenSSH Server, firewall rules or NAT.

Use `BULL.exe` or the installed shortcut to start BULL. Launching from setup
uses that same entrypoint and Terminal profile. The fallback console uses
Consolas; no global Terminal settings are modified. Changing the theme updates
owned BULL shortcut icons, not unrelated shortcuts. High contrast is retired.
The portable launchers are locally compiled from `Tools/BullLauncher.cs` and
are unsigned; Windows may show a publisher/reputation warning.

Packs live in `%LOCALAPPDATA%\BULL\BenchmarkPacks` and survive application
updates. HTTPS downloads are bounded to 64 MiB. ZIP paths, files, digests and
extraction size are validated. Archive code is never executed. An identical
installed version is preserved; changed content requires a new version.

Skipping optional steps leaves BULL installed and ready for configuration:

- Home section 3: packs and tasks;
- section 4: LLM connection;
- section 5: language and themes.

Every launch reruns 18 essential integrity checks, then probes the selected
connection and installed library. Green means ready; yellow identifies missing
setup. Settings and saved reports remain available offline.
Home shows integrity and connection only; pack status and read-only browsing
appear in Model testing and Test settings. Additional → Diagnostics lets you
choose basic checks or the full Setup regression.

First and repeat terminal geometry, immediate theme switching and folder release
after exit still need manual acceptance. Automated checks do not certify every
Windows Terminal configuration. See [scope and limits](../FOLLOWUP_2026_10_10.md).

[User guide](USER_GUIDE.md) · [Connections](CONNECTIONS.md)

## Verify the downloaded archive

Put the matching ZIP and checksum file in the same directory, then run PowerShell:

```powershell
$expectedBullHash = ((Get-Content -LiteralPath 'BULL-v0.29.0.1-Bundle.sha256.txt' -Raw).Trim() -split '\s+')[0]
$actualBullHash = (Get-FileHash -Algorithm SHA256 -LiteralPath 'BULL-v0.29.0.1-Bundle.zip').Hash
if ($actualBullHash -ine $expectedBullHash) { throw 'BULL archive checksum mismatch' }
```

Use the version-specific release assets, not GitHub's automatic source archive.
An equal checksum detects corruption/changed bytes; it is not a publisher signature.
Do not run a mismatching archive or disable system protections to conceal the warning.

## Upgrade, backup and removal

Close BULL and privately back up any needed Chats, Benchmarks, Exports, UserTests
and connection metadata. Do not publish these copies or copy an old Runtime/Python
environment over a new installation. Extract the new release into a new folder
and run Setup again. The shared library persists; pack versions are not automatically
updated or rescored. Import/select connection metadata deliberately, with preview;
keep private keys in their existing user-controlled location.

To remove this portable installation, close BULL and terminals using its folder,
then remove that folder and shortcuts pointing to it. The shared library and
user-profile connection metadata remain; inspect/back up them separately before
any cleanup. Do not remove another installation's shortcuts or stop an external
model server. If Windows still locks the folder, report the holding process and
sanitized log; do not force-delete unrelated data.

If the verification libraries are missing, setup offers their installation
from PyPI into a private `Runtime/Python` environment, with confirmation.
It does not alter the system's Python packages. All launchers use the Python
that passed installation verification.
