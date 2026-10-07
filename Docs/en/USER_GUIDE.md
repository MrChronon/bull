# BULL v0.28.0.6 user guide

BULL is a Windows-first terminal application for chatting with local language
models and comparing them under repeatable conditions. It supports Ollama and a
compatible llama.cpp HTTP server, locally or through a pinned SSH tunnel.

## Requirements and installation

- Windows 11, Python 3 and PowerShell;
- Ollama or a compatible llama.cpp server;
- at least one model installed on the selected backend.

Download `BULL-v0.28.0.6-Bundle.zip` and its checksum from the GitHub release.
Verify the SHA-256 value, extract into a new directory, and run
`Install-BULL-v0.28.0.6.cmd`. It creates red BULL shortcuts on the Desktop and
in the Start Menu. Choose **Client**, **Server**, or **AllInOne**.

Use `BULL-v0.28.0.6.cmd` for the application. The Benchmark Lab and Agent Lab
launchers open their respective sections directly.

On the first launch, choose English or Russian. This question is shown once.
Change the saved language or color theme later under **More → Language and
appearance**. BULL Red is the default. Matrix BULL is the green alternative;
high contrast remains available. During the startup check, the separate splash
shows the active stage, the exact current check, and the completed/total check
count emitted by the offline regression harness.

The client performs an offline regression check before enabling inference. A
small separate desktop window shows the version, release artwork, the current
check, and its real completed/total progress. It closes before the terminal menu opens and
never changes terminal colours. If Windows GUI facilities are unavailable, the
check still runs normally in the terminal. If it fails, run `Run-Tests.ps1` and
inspect `client_debug.log`.

## Home

The primary menu contains four actions:

1. **Compare models** — choose the best installed model for a task.
2. **Chat with a model** — start a chat or open a saved conversation.
3. **Connection** — use this computer or a remote SSH server.
4. **More** — results, appearance, status, help, expert commands, and experiments.

Press `0` to go back or exit. A `/command` can be entered from Home, but ordinary
model messages belong in Chat.

The complete bull mark and the product name appear on every navigation page.
Colors are never the only status signal: warnings and errors have text labels.

## Connect to models

Open **Connection** and choose one source:

- **Local Ollama** for models installed on this computer;
- **Saved server** for an existing BULL connection;
- **New server from SSH alias** when `ssh ALIAS` already works;
- **New server manually** for an address, SSH port, user, private key, and
  independently verified server fingerprint.

Import, migration, SSH checks, and Internet-access instructions are under the
Tools section of Connection. BULL does not require Ollama to be running merely
to open menus, settings, help, or saved reports. Chat and a new benchmark run
check the selected connection immediately before use.

See [Connections](CONNECTIONS.md) for setup and troubleshooting.

## Compare models

### Standard comparison

Choose **Compare models → Standard comparison**, select models, review the plan,
and start. Standard settings use the same test definitions and comparable run
conditions for every selected model. Change runs, seeds, reasoning, or generation
settings only when the experiment requires it.

### My tasks and prompts

Choose **Compare models → My tasks and prompts**. You can select a file from
`UserTests` or paste a one-off prompt. A `.txt` task measures runtime and keeps
answers for manual review; BULL does not fabricate a quality score. A strict
`.yaml` task may use only supported deterministic criteria.

### Resume interrupted run

Completed runs are written atomically to a checkpoint. **Resume interrupted
run** continues only missing or interrupted work. If the server is offline,
settings and completed runs remain intact; restore the connection and resume
again. Environment mismatches block a normal resume unless the expert explicitly
uses the documented force path.

### View results

After a run, BULL offers:

- a concise terminal summary;
- measured top-three places for Native quality, generation speed, VRAM and
  weighted balance, plus separately gated model choices;
- custom importance weights;
- numeric quality/speed and task-time charts with stable model IDs;
- a self-contained HTML report;
- share-safe summary files and clearly labelled private raw output.

Recommendations are relative to that run. They reuse measured metrics and apply
quality/task gates; they are not a universal leaderboard or a new benchmark score.

During a run, the live line can show approximate token rate plus GPU/VRAM and
aggregate CPU/RAM for the active inference host. After each saved run, BULL prints
a compact checkpoint: native/final score when a scorer exists, TASK, speed and the
available resource measurements. A missing sensor is shown as unavailable, never as
zero.

See [Results](RESULTS.md) for how ranks, recommendations, resources and charts
are read, and [Benchmarks](BENCHMARKS.md) for metric definitions and user-test
authoring.

## Chat

Choose a model, then use FAST for ordinary replies, THINK for supported reasoning,
or ULTIMATE for bounded continuation of demanding work. Chats can be saved,
loaded, branched, exported, and supplied with attachments. Tool execution and
generated code are not an operating-system sandbox. Run untrusted work only in
a disposable VM without secrets or network access.

The dashboard distinguishes a live backend from saved session data. When the
backend is offline it does not invent GPU, VRAM, model, or health readings.

## More

- **Saved results** opens the terminal summary or HTML report.
- **Language and appearance** changes the persistent language and theme.
- **Current session status** shows connection state and saved/runtime metrics.
- **How to use BULL** explains the short route through the application.
- **Expert commands** exposes `/bench` and service commands.
- **Experimental features** contains Agent Benchmark, GPU Lab, and advanced
  engine/server tools.

The ordinary workflow does not require experimental server setup.

## Result files

A completed comparison can produce raw JSON/CSV, an atomic checkpoint, summary
JSON/CSV, tested profiles, private evidence, a share-safe evidence summary, and
an offline HTML report. Raw answers, prompts, local paths, and connection details
may be private. Review files before sharing them.

## Troubleshooting

- **No local Ollama:** start Ollama or choose a saved SSH server under Connection.
- **WinError 10054:** the connection was reset; restore the server/network and resume.
- **WinError 10061:** the endpoint is refusing connections; verify SSH, the remote
  runtime, and tunnel before resuming.
- **Regression failed:** run `Run-Tests.ps1`; do not benchmark until it passes.
- **Broken terminal characters:** use the supplied launcher, which configures UTF-8.
- **English screen contains a legacy-language backend message:** the UI keeps the
  technical detail in `client_debug.log` and displays a localized recovery path.

## Privacy

Public bundles exclude `Chats`, `Runtime`, `Benchmarks`, `Exports`, `Workspace`,
private keys, connection profiles, and local logs. Never expose Ollama `11434`
or llama.cpp `8080` directly to the Internet. Read [Security](SECURITY.md) before
using a remote server or sharing benchmark artifacts.
