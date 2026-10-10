# BULL v0.29.0.1 user guide

Documentation synchronized 11 October 2026 for pre-release v0.29.0.1.
The 10 October behavior is unchanged. This pre-release is for user testing,
not a fully accepted stable version. See [release readiness](../RELEASE_READINESS.md)
for automated gates and still-open manual acceptance.

The bilingual GitHub handoff includes [repository metadata](../GITHUB_REPOSITORY.md),
[release text](../../GITHUB_RELEASE_v0.29.0.1.md) and a [publishing guide](RELEASING.md).
Pre-release publication does not close manual acceptance.

BULL is a Windows terminal application for model chat and reproducible
comparisons of quality, speed and resources. It supports Ollama and llama.cpp,
locally or through a pinned SSH tunnel.

Test packs are independent of the engine. A run uses one exact pack version,
with all or selected tasks. Packs survive BULL updates in
`%LOCALAPPDATA%\BULL\BenchmarkPacks`.

## Requirements and installation

Follow-up: the extracted bundle contains Setup, not a root BULL.exe. Setup
materializes the manifest-checked client only after verification and connection
setup/skip. See [correction details](../FOLLOWUP_2026_10_10.md) for the specialized
RU/EN report, scorer v2, resource availability and process-lifecycle changes.

Windows 11, Python 3.10+ and PowerShell are required. Install models and the
Ollama/llama.cpp server separately. Settings and saved reports work offline.

1. Obtain the ZIP and matching SHA-256, verify and extract into a new directory.
   Use the exact-version links in the root README or GitHub Releases; v0.29.0.1
   is a pre-release. GitHub's automatic Source code is not the installation ZIP.
2. Run `Setup.exe` (the bull with an install-arrow icon), choose English or Russian,
   then **BULL Red** or **BULL Matrix**. Setup and BULL retain that choice.
   `Setup.cmd` is a fallback entrypoint.
   All subsequent steps use that language.
3. Install standard packs, import your own ZIP via an HTTPS archive link or local file,
   or continue without tests. Review the archive before installation.
   Standard installation selects the safe `bull_chat_core`; other packs remain available.
4. Wait for the full internal regression: 668 checks without model inference.
   Failure offers retry or exit; the installation is not marked complete.
5. Configure an existing connection: local Ollama, saved server, SSH alias or manual parameters.
   You may skip and configure it later in Home section 4.
6. After verification and connection setup/skip, Setup materializes `BULL.exe`, creates theme-coloured shortcuts and shows connection
   and pack readiness. Choose Launch BULL or Exit installer.

The installer does not provision servers, install models, modify firewall rules
or request administrator rights. If Python is missing, its winget installation
is offered with a separate confirmation.

Use `BULL.exe` or the installed shortcut for normal startup. `BULL-v0.29.0.1.cmd`
uses the same entrypoint. Benchmark Lab and Agent Lab launchers
open their respective sections directly.

Every launch reruns 18 essential internal regression checks for integrity,
imports, schemas, interface assets and atomic storage, without using a cached
pass. A separate splash shows the current check and real progress, then closes
before the main menu. Without Tk, verification still runs in the terminal.
Failure blocks startup: inspect `client_debug.log` and run `Run-Tests.ps1`.

BULL then probes the selected connection and checks the installed library.
Two indicators at the top of Home show integrity and connection. Test-pack
status appears in Test settings and Model testing, with a pack → tasks browser.
Green means verified readiness; yellow identifies missing setup. These states
are not repeated beneath menu items.
Without a connection or packs, settings and saved reports remain available.
BULL never silently switches to another backend.

The terminal logo uses coloured background cells and ordinary spaces, without
special font glyphs. An ASCII silhouette is used when colours are unavailable.
The render now has 48×24 cells, sampled directly from the locked canonical logo.
All 24 rows are emitted and flushed individually before the wordmark. Full height
and identical geometry on first and repeat Windows Terminal launches still need
manual acceptance; restarting is not considered a fix.
Setup, its Launch BULL action and installed shortcuts use one Terminal profile;
ordinary consoles use per-window Consolas settings. Global settings are untouched.
The two themes also update icons of owned BULL Desktop/Start shortcuts. Foreign
shortcuts are never changed. High contrast is retired; old contrast preferences
migrate to BULL Red. The new native launchers are unsigned.

## Home

1. **Model testing** — run, resume and results.
2. **Chat with a model** — new or saved conversation.
3. **Test settings** — installation, task selection, removal and Author Workshop.
4. **Connection settings** — local models, SSH and engine options.
5. **Program settings** — language and color themes.
6. **Additional** — session status, diagnostics, help and experiments.
0. **Exit**.

### Main navigation tree

```text
Home
├─ 1 Model testing
│  ├─ 1 Compare a pack → pack/tasks → models → conditions → plan
│  ├─ 2 UserTests file; 3 my prompt
│  ├─ 4 Resume checkpoint; 5 results → recommended HTML / summary
│  └─ P Browse packs → tasks; L language tracks; ? help
├─ 2 Chat → new / saved
├─ 3 Test settings
│  ├─ 1 Base ZIPs; 2 local ZIP or HTTPS link
│  ├─ 3 Pack/tasks; 4 move version to Trash
│  └─ 5 Library folder; 6 Author Workshop; 7 Browse packs → tasks
├─ 4 Connection settings
│  ├─ 1 Local; 2 saved server; 3 SSH alias; 4 manual
│  ├─ 5 Import JSON; 6 migrate; 7 SSH check
│  └─ 8 Key/alias guide; 9 Internet; 10 forget entry; 11 engine options
├─ 5 Program settings
│  └─ 1 Language; 2 BULL Red; 3 BULL Matrix
├─ 6 Additional
│  ├─ 1 Session status; 2 application and API diagnostics
│  ├─ 3 How to use; 4 command reference
│  └─ 5 Agent Benchmark
└─ 0 Exit
```

Press `0` to go back. Exact `/commands` remain available from Home and Chat
but are not required for ordinary comparison. BULL Red is the default,
BULL Matrix the green alternative. Success stays green, warnings yellow
and errors red regardless of theme.

In **Program settings**, select `3` or enter `BULL Matrix` for a green bull,
green accents and cyan actions. The theme applies immediately, survives restart,
and is retained when changing language. On the next launch, the startup window
also uses Matrix green: the same BULL composition, a matching frame and progress
bar. Vertical columns of digits and symbols animate along the right edge of the
artwork, clear of the bull, version, active check and progress. Menus and model
benchmark runs have no animation. Selecting BULL Red restores red styling and
the red startup artwork.
Settings belong to this application
directory; a configured `BULL_UI_THEME` overrides them at startup.
UTF-8 and colour support are checked before the first menu after startup checks
and when selecting a theme. Terminals without colour support use an ASCII bull.

## Connect to models

Open **Connection settings** and choose one source:

- **Local Ollama** for models installed on this computer;
- **Saved server** for an existing BULL connection;
- **New server from SSH alias** when `ssh ALIAS` already works;
- **New server manually** for an address, SSH port, user, private key, and
  independently verified server fingerprint.

Import, migration, SSH checks, and Internet-access instructions are under the
Connection settings screen. BULL does not require Ollama to be running merely
to open menus, settings, help, or saved reports. Chat and a new benchmark run
check the selected connection immediately before use.

See [Connections](CONNECTIONS.md) for setup and troubleshooting.

## Compare models

### Compare a test pack

Choose **Model testing → Compare a test pack**, select a pack and all or specific
tasks, then choose models, review the plan and start. Standard settings use the same test definitions and comparable run
conditions for every selected model. Change runs, seeds, reasoning, or generation
settings only when the experiment requires it.

### My tasks and prompts

Choose **Model testing → Task from UserTests** or **My prompt**. Select a file from
`UserTests` or paste a one-off prompt. A `.txt` task measures runtime and keeps
answers for manual review; BULL does not fabricate a quality score. A strict
`.yaml` task may use only supported deterministic criteria.

### Resume interrupted run

Completed runs are written atomically to a checkpoint. **Resume interrupted
run** continues only missing or interrupted work. If the server is offline,
settings and completed runs remain intact; restore the connection and resume
again. Environment mismatches block a normal resume unless the expert explicitly
uses the documented force path.

Windows file locks trigger a bounded checkpoint-write retry. If replacement
remains blocked, testing stops, the previous file stays intact and the complete
new payload remains beside it as a recovery copy. Its path is displayed.
Close other BULL instances and programs holding the file, then choose Resume.
Using the copy requires confirmation and creates a new checkpoint; both source
files are preserved. To select it explicitly, use `/bench resume "PATH"`.

CPU, RAM, GPU and VRAM belong to the inference host, including background
processes—not exclusively to the model. Windows CPU/RAM sampling uses native
counters without WMI or administrator rights. SSH sampling stays on the server.
Saved-run summaries show average CPU/GPU utilization and observed memory peaks.
Each of GPU, VRAM, CPU and RAM shows a measurement or `N/A` with its reason,
never a fabricated zero. Missing optional temperature/power readings do not
hide GPU/VRAM. Old reports cannot gain missing measurements retroactively.

The full 668-check offline suite is also available through **Additional →
Diagnostics → Full regression**, as in Setup; it performs no model inference.

### View results

For ordinary packs, BULL offers:

- a concise terminal summary;
- measured top-three places for Native quality, generation speed, VRAM and
  weighted balance, plus separately gated model choices;
- custom importance weights;
- numeric quality/speed and task-time charts with stable model IDs;
- a self-contained HTML report — the recommended next step: quality / contract /
  speed scorecards, two scatter plots (quality ↔ speed and quality ↔ task time),
  observed seed stability, resources, and a per-test heatmap;
- share-safe summary files and clearly labelled private raw output.

Recommendations are relative to that run. They reuse measured metrics and apply
quality/task gates; they are not a universal leaderboard or a new benchmark score.
Language runs use a specialized RU/EN summary instead of a combined language
top-three. Returning from HTML/answers clears and redraws the result menu.

### Russian, English, and bilingual tracks

`language_ru` and `language_en` measure automatic checks and speed separately for Russian
and English prompts. Their paired tasks have identical intent, JSON contract,
context, and output budget; only the prompt language changes.

```text
/bench language_ru MODELS
/bench language_en MODELS
/bench bilingual MODELS
```

`/bench bilingual` runs both variants of every task in one balanced plan. Compare
Native score, task completion, warm tok/s, and wall time within each language
track. Do not combine Russian and English scores into a single quality number.
The interactive route is **Model testing → Language tracks**.
Choose an installed compatible pack version first; tasks are validated before
model discovery. Base pack 1.0.1 uses scorer v2 to penalize foreign-script prose.
Scorer v1 remains available for 1.0.0; installed versions and results are never
automatically updated or rescored.
The scorer also checks the answer prose language; the terminal JSON contract is
not used to infer it.

RU/EN reports separate Native checks, required language, prose purity, Native
time, warm tok/s, coverage and per-seed mean ranges. RU − EN differences use
exact pairs by model/digest, backend, pack/scorer, seed/run and recorded settings.
No pair means no paired difference; there is no combined winner. These six
tasks are not comprehensive semantic evaluation: 100% does not prove general
language competence. See [Results](RESULTS.md) for definitions and limits.

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
Models known not to support THINK use FAST. An explicit HTTP 400 “does not support
thinking” permits one non-THINK retry in chat only, with tools off; unrelated
errors and benchmark policy are not silently changed. Before a conversation,
status shows configuration, not an active session; empty chats are not autosaved.

## Program settings

Home section 5 contains language, theme selection, BULL Red / BULL Matrix
shortcuts. Saved results are in Model testing; engine options are in Connection settings.

## Additional

Home section 6 opens a flat list: current session status, application and API
diagnostics, the guide and command reference, and Agent Benchmark.
Diagnostics offers basic checks or Setup's full internal regression. Before the
first chat, status shows configuration only, not an active chat or context meter.
The API check does not generate model answers. Experimental tools are labelled
separately; ordinary comparison does not require them. `0` returns to Home.
There is no additional Experiments submenu.

## Test pack library

In Test settings choose a base pack from `BasePacks`, import a local ZIP or an
explicit HTTPS archive link, choose
an installed pack, or skip. Skipping is remembered. Return through **Home → Test settings**. Base ZIP installation accepts comma-separated numbers or `all`;
selection for a benchmark still uses one pack version. Windows storage is
`%LOCALAPPDATA%\BULL\BenchmarkPacks`, outside the application directory.
The library shows the exact location, versions, declared skills and languages.
Removal moves an exact version to recoverable Trash; it does not delete keys,
connections or results. ZIPs are data-only, bounded and explicitly reviewed. Import accepts local files or HTTPS links.

For read-only browsing use **Model testing → P** or **Test settings → 7**:
pack versions first, then the selected version's tasks. Browsing does not change
the active selection. Pack status belongs to these sections, not Home.

[Author Workshop](AUTHOR_WORKSHOP.md) creates UTF-8 YAML/TXT sources, validates
positive and negative example answers and builds a new-version ZIP without
installing or publishing it. Give the complete [LLM author instructions](PACK_AUTHOR_LLM.md)
and Workshop guide to a drafting LLM, then review domain references yourself.
Text-only tasks have manual quality review, not invented automatic scores.

New pack checkpoints and private evidence retain complete task snapshots.
Removing/updating a pack does not replace a resumed task. Corrupted snapshots
or changed engine checks block execution; old checkpoints without snapshots
still require the exact installed content. Share-safe JSON includes only
allowlisted pack hashes and coverage, never the snapshot itself.
See the [step-by-step library guide](PACK_LIBRARY_GUIDE.md) for selection,
subsets, exact-version checkpoints and recoverable removal.
See the [pack specification](../PACK_LIBRARY_SPEC.md) and
[LLM author instructions](PACK_AUTHOR_LLM.md).

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

- **Different logo width or clipped height:** `Setup.exe`, its launch button
  and the installed shortcut use the same
  `BULL.exe` entrypoint. Compare the first and subsequent menus for acceptance;
  the full bull, wordmark beneath it and text should match. The bounded-row
  correction is implemented; live terminal visual acceptance remains open.
- **Application folder still locked after exit:** BULL reaps its own sampler/SSH
  children and closes their pipes; it does not stop a separately running model server.
  Not every Windows lock is proven resolved. Close the BULL window and terminals
  opened in that folder; if the issue repeats, provide the local log and owning
  process details without terminating unrelated servers.

## Privacy

Public bundles exclude `Chats`, `Runtime`, `Benchmarks`, `Exports`, `Workspace`,
private keys, connection profiles, and local logs. Never expose Ollama `11434`
or llama.cpp `8080` directly to the Internet. Read [Security](SECURITY.md) before
using a remote server or sharing benchmark artifacts.

If the verification libraries are missing, setup offers their installation
from PyPI into a private `Runtime/Python` environment, with confirmation.
It does not alter the system's Python packages. All launchers use the Python
that passed installation verification.
