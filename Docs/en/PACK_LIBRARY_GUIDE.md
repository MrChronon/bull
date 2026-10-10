# Test pack library

Applies to BULL v0.29.0.1 Pack Library.

## First launch

Setup first asks for language and BULL Red / BULL Matrix, then offers standard
packs, your own local ZIP/explicit HTTPS archive link, or skip. After the full
668-check regression and connection setup/skip it creates `BULL.exe` and offers
Launch/Exit. See the [installation sequence](USER_GUIDE.md).

Later, **Home → Test settings** offers:

1. **Install a base pack** — choose one or several optional ZIPs in `BasePacks`.
2. **Import my ZIP** — enter a local archive path or explicit HTTPS archive link.
3. **Choose installed pack and tests** — use an existing shared installation.
4. **Skip for now** (`0`) — keep chat, connections and saved reports available.

Skipping is remembered across application builds. It does not install tests.
You can return directly through **Home → Test settings**. Trying
to compare without an active pack opens the same install/select choices.
Installing a ZIP never selects a different installed version silently.

Enter one number, comma-separated numbers such as `1,3`, or `all`. A batch
installation adds the approved packs to the library without activating them.
Then select one installed version and all or specific tasks for the next run.
Setup's standard-install action selects `bull_chat_core` when successful;
batch installation in the library itself does not change the active selection.
Identical installed versions are kept; different content cannot overwrite
the same version. If one installation fails, the page lists successes and
failures; successfully installed versions remain available.

## Where packs live

Windows library: `%LOCALAPPDATA%\BULL\BenchmarkPacks`.

```text
BenchmarkPacks/
  Installed/public/<pack_id>@<version>/
  Installed/private/<pack_id>@<version>/
  Workspaces/<pack_id>-<unique_id>/  editable author sources
  PackExports/                     independently built ZIPs
  Trash/<pack_id>@<version>-<unique_id>/
  .staging/                 temporary installation data
  library_state.json       onboarding and explicit selection
```

The exact path is shown in the library menu; the installed list shows each
version's observed file size. It resolves from the current user's environment,
not a path captured on the developer's machine. **Open library folder** opens it.
Read-only browsing is available at **Model testing → P** or **Test settings → 7**:
choose a pack version, then view its tasks without changing the run selection.
The library is separate from the application folder, so unpacking a newer build
does not remove tests. Obtain ZIPs from the pack author, for example from their
GitHub release; BULL does not download or publish packs automatically.

Use **Remove one installed version** to move that exact version to BULL's bin
(`Trash` inside the library, not Windows Recycle Bin).
Nothing is permanently deleted. Files in Trash still use disk space: review and
delete the chosen trash directory manually if you no longer need recovery.
To restore it, move its directory back under the original visibility branch and
rename it to the exact `<pack_id>@<version>`, then select it again.

For a clean start, close BULL, back up needed packs, and rename this specific
`BenchmarkPacks` directory. The next launch creates an empty library only after
an explicit onboarding choice. Never edit installed versions in place. Do not
delete the entire user application-data folder.

## Install and review

Enter a local ZIP path or explicitly request an HTTPS archive download. There is
no network catalog, background download or automatic version update.
Before confirmation BULL validates paths, file types,
sizes, manifest, hashes, engine compatibility and scorer references. The preview
shows identity/version, status, visibility, source, license, skills and declared
languages. Installation requires explicit confirmation. The ZIP is checked again
against the approved manifest and compiled-content hashes before publication.

Only data files are accepted: JSON, YAML, Markdown and TXT. Packs cannot add
Python/PowerShell code or import new scorers. Existing engine-owned code checks
require typing `EXECUTE` when selecting those cases; they are not a sandbox. Use a disposable VM for
untrusted model-generated code.

Current limits: 1,000 cases, 8 MiB per JSON/file, 64 MiB archive, 128 MiB expanded,
4,096 ZIP entries, compression ratio at most 200. Larger packs need a future
explicit budget policy; there is no claim of unlimited pack size today.

## Compare

Open **Model testing → Compare a test pack**. Choose exactly one installed
version, or **Use current selection**. Select `all` or distinct test numbers
separated by commas. `n` and `p` browse case pages. A mixed-domain pack can contain
different skills, but a run never merges two packs.

Case pages show descriptions, scoring references, author budgets and constraints.
The generation wizard then selects models, repeats/seeds and sampling source.
Before inference the plan shows the exact selected case IDs, pack version,
coverage and resolved runtime settings. Test budgets remain separate from saved
chat settings. Inspect criteria and prompts in the pack's data/documentation
when assessing whether its tests fit your work.

A subset is explicitly labeled **SUBSET — not a full-pack benchmark result**
in the terminal and HTML. Its scores describe only those tasks. A pack without
automatic scoring supplies timing/output evidence for human review, not invented
quality percentages. Native model quality and client recovery remain separate.

New pack checkpoints contain a complete private, hash-checked task snapshot.
Changing the menu selection, installing another version or removing the original
pack does not replace these tasks. Resume reads the captured definitions, not
the installed library. Changed snapshot bytes or engine scorer/verifier code
block execution; restore the original checkpoint/engine rather than forcing it.
Older checkpoints without a complete snapshot still need the exact installed
version. Missing data never causes a newest-version substitution.

Private evidence retains the snapshot. Share-safe JSON exposes only version,
manifest/compiled/snapshot hashes and selected/total coverage, not author text,
prompts, criteria or expected answers. HTML explains coverage and content hashes.
Review pack/case IDs and model labels before sharing: names can identify a project.

## Existing features

**My tasks and prompts** remains a separate legacy `UserTests`/prompt workflow.
Loose files are not silently appended to a pack. Their directory remains local
to the build; use Author Workshop packs for portable, versioned tasks.

Advanced named commands require the pack that contains their cases. For example,
language tracks require the Language Comparison pack; CHAT commands require CHAT
Core. `/bench pack list` lists installed versions; inspection/validation of one
pack requires `PACK_ID@VERSION`, never an implicit newest version.
Language tracks select a compatible installed version before model discovery.
Current base Language Comparison is 1.0.1/scorer v2; 1.0.0 remains readable and
is never updated or rescored silently. See the [RU/EN result guide](RESULTS.md).

A broken installed version is listed as invalid and cannot be selected. Other
healthy versions remain usable. Home, chat and saved reports do not require a
pack. Resolve library access errors at the displayed folder; BULL does not create
a replacement library in its working directory. If `library_state.json` is
corrupt, close BULL and rename that specific file after backing it up; installed
packs remain intact, and onboarding/selection starts again.

Authoring instructions: [cloud LLM pack authoring](PACK_AUTHOR_LLM.md).
**Author Workshop** is available from the library menu. It creates editable
sources, checks positive/negative answers without inference, and builds a ZIP
for explicit import. See [Author Workshop](AUTHOR_WORKSHOP.md). Frozen native
base packs keep their separate maintainer tools; they are not automatically
converted to keyword-scored tasks.
