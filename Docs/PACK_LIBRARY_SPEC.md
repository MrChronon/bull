# BULL Pack Library — PK1 specification

Requirements accepted: 2026-10-09. Implemented in v0.29.0.1 Pack Library.
Current installation/navigation wording synchronized: 2026-10-11.
PK1 is not a
scorer rewrite, runtime redesign, Linux port or online marketplace.

## 1. Product boundary

The engine owns model connections, runner/scorer/verifier implementations,
scheduling, telemetry, checkpoint/resume and reports. Packs own task data,
declared criteria, documentation, provenance and task/model defaults. Installing
a new compatible pack must not require modifying the engine source.

Base tests travel with BULL as separate ZIP packages. They are optional, not
hardcoded fallback tasks and not an automatic mandatory installation. Freeze
existing definitions and score fixtures before extracting them. Extraction
must preserve effective prompts, scorer references, budgets and results.

## 2. First run and navigation

Setup selects language, then BULL Red / BULL Matrix before dependency checks.
Its optional test-installation step offers:

1. **Install base tests** — show title, version, languages, skills and storage path.
2. **Install my ZIP** — provide a local file or explicit HTTPS archive link;
   validate, preview, confirm installation. There is no automatic network catalog.
3. **Skip for now** — continue installation without tests.

Next come the mandatory full 668-check offline regression, existing connection
setup/skip, completion, then launch/exit. BULL.exe is materialized only after
regression succeeds and connection setup is completed or skipped. Choosing or
skipping packs alone does not complete Setup. Chat, settings and saved reports
remain available without installed packs after launching the installed application.

Complete onboarding after any of these explicit choices; do not repeat it on
every startup or upgrade. If Compare is requested with no runnable packs, show
the same installation choices with a Back action. A corrupt pack must not block
Home, chat or reading saved reports, and must never run through a fallback pack.

Home has Model testing / Chat / Test settings / Connection settings / Program settings
and the flat Additional section. Its header shows integrity and connection only;
pack status and read-only pack → task browsing belong to the two testing sections.
The testing route opens a direct pack picker; library management is in Test settings. Library actions include install ZIP,
inspect, open storage location, create editable copy and remove selected version.
No server provisioning or network catalog is added to the primary flow.

## 3. Shared storage

Windows default: `%LOCALAPPDATA%/BULL/BenchmarkPacks`.

```text
BenchmarkPacks/
  Installed/
    public/<pack-id>@<version>/
    private/<pack-id>@<version>/
  Workspaces/                  # editable source copies, never auto-discovered
  Trash/                       # explicitly removed versions, recoverable
  .staging/                    # private in-progress installations, not runnable
```

`public` is the manifest's intended distribution classification, not upload
permission: neither branch is automatically published or sent anywhere. Library
data never goes into the application release ZIP. Upgrades reuse this location,
not a path inside the old application folder. Linux storage will be specified in
P1; PK1 must not invent an untested cross-platform contract.

Show the resolved directory in installation preview and library help. Explain
where to obtain packs (included base ZIP or a trusted author's release), how to
open the directory, how much the selected version occupies, and how to remove
it. Removing BULL does not silently remove packs. A clean install requires an
explicit library reset; warn that deleting the library also deletes workspaces
and retained versions. Trash cleanup needs a separate explicit choice.

Do not silently select a fallback folder if LOCALAPPDATA is unavailable. Do not
follow symbolic links or reparse points while installing or removing content.
Tests use injected temporary roots, never the real user library.

## 4. ZIP installation and trust

One ZIP contains exactly one pack, at its root or under one enclosing directory.
Use the existing versioned manifest/case/gold/lock contracts. Allow only data and
text documentation: JSON, YAML/YML, Markdown and TXT in the first installer.
No executable files, symlinks, junctions, encrypted entries, alternate data
streams, absolute paths, `..`, duplicate paths or Windows case-name collisions.

Preflight paths, file types, CRC/size integrity and budgets before publication.
Extract using bounded streams into a fresh staging directory; never use unchecked
`extractall`. Validate manifest, engine compatibility, refs, content/gold/lock
hashes and lifecycle. Publish by an atomic same-filesystem rename. A failed
installation leaves no discoverable partial pack. Concurrent installers use an
exclusive library lock; do not automatically remove another process's lock.

Existing `<id>@<version>` is never overwritten, even by a ZIP with the same bytes.
An upgrade creates a separate explicit version. A checksum detects corruption
but does not authenticate an author or prove that expected answers are correct.
No pack is permitted to download resources or execute a setup command.

No arbitrary *product* cap on task count is intended. Resource safeguards remain
necessary. The current registry v1 has a 1,000-case / 8 MiB JSON ceiling; PK1.2
must revise or make the ceiling explicit/configurable before claiming larger
pack support. Never truncate a pack silently. Initial ZIP safeguards are
64 MiB archive, 128 MiB expanded total, 8 MiB per file, 4,096 entries and 200:1
maximum compression ratio; these are documented resource controls, not a claim
of unlimited input. Large-pack support needs bounded loading and paginated UI.

## 5. Selecting tests and explaining coverage

A run binds exactly one pack ID, explicit version and compiled hash. Select all
cases or a non-empty subset of unique case IDs. There is no merging of installed
packs. Mixed domains are allowed in one pack; groups, languages and skills remain
visible. Repeated case IDs inside a pack are ambiguous and must be rejected.

Before inference show title, author/provenance, lifecycle, version, compatibility,
languages, skills, exact selected count/list, why these cases are included,
scoring scope, manual review, model choices, seeds, budgets and parameter source.
Warn when only part of the pack is selected. A partial score is not the official
full-pack score and must be labelled as partial coverage in terminal and HTML.
Treat titles, descriptions and author text as untrusted: escape terminal control
sequences and HTML, and never automatically execute or open documentation links.

Unselected packs do not influence the run or its scores. Invalid library entries
can be listed with their error but cannot be selected. No inference occurs until
the selected pack and the entire selected configuration pass validation.

## 6. Test and model parameters

Authors may declare task budgets and model defaults through validated fields.
Only values understood by the installed engine are applicable. Reject unknown
parameters, wrong types and unsafe/out-of-range values; never silently discard
them. Connection credentials, endpoints, filesystem paths, commands and imports
are not pack settings. Metadata cannot certify actual GPU placement.

PK1.2 defines the supported fields using the existing runtime contract. Preview
must distinguish required task constraints, suggested model defaults, selected
parameter source, explicit user override and measured/unknown effective value.
Conflicting required constraints must be resolved before launch, not overwritten
in a hidden precedence rule. In Ollama-profile mode inherited sampling parameters
remain omitted from the API request; report profile-owned differences separately.
Adding author defaults must not reintroduce the fixed sampler bug.

Benchmark choices never mutate saved chat profiles. Freeze the effective plan
and provenance per run. A later **Config Boundary** stage separates model
profiles from test settings; PK1 must not pretend this broader split is done.

## 7. Authoring and editing

An author can work manually or ask a cloud LLM using the paired instructions:
`en/PACK_AUTHOR_LLM.md` / `ru/PACK_AUTHOR_LLM.md`. The LLM drafts task data and
criteria, not engine code. A human validates domain assumptions, reference values,
licenses and representativeness before using or distributing a pack.

Use the existing `.txt` and safe `bull-user-test` YAML formats for editable task
sources. Formal YAML criteria compile to engine-owned `user_contract_v2`;
unscored text uses `none`. Preserve original sources and README in the ZIP. PK1.4
provides an engine-owned source-to-ZIP builder which calculates hashes and lock and
checks positive/negative answer fixtures without model inference. The editable
`bull-pack-workspace@1` contract, exact `bull-author-fixtures@1` expectations,
safe defaults and manual editing workflow are specified in
`en/AUTHOR_WORKSHOP.md` / `ru/AUTHOR_WORKSHOP.md`.

Edit prompts, input data, criteria, weights and expected values in a workspace,
not in an installed version. Rebuild and install a new version. Published
definitions, raw results and checkpoints never change in place. Distribution
is independent of BULL; GitHub is optional. A private pack need not be published.

## 8. Scoring and evidence

Automatic quality describes only declared machine checks; manual semantic review
is separate. No scorer, no quality number. Phrase matching does not prove correct
reasoning, style or engineering safety. Creativity and open tasks may use manual
rubrics without a fabricated numeric quality ranking. No local/remote LLM judge
is enabled in PK1. Future judge work must account for consent, costs, hardware
capacity, rubric validity, bias and reproducibility.

Record pack identity, manifest/compiled/case hashes, engine/scorer/verifier
versions, selected cases, parameter provenance and a complete immutable task
snapshot in private run evidence/checkpoints. Share-safe artifacts retain only
allowlisted metadata and aggregated coverage, never user prompts, expected
answers, private filesystem paths or private author identifiers.

Updating or removing a pack does not rewrite old reports or replace a resumed
task. If necessary snapshot data is missing, resume must explain the problem and
stop; it cannot substitute the newest pack version. Offline rescore still creates
a separate artifact with its own provenance.

## 9. Verification and delivery

PK1.0 requirements → PK1.1 installer → PK1.2 extraction → PK1.3 UI/run selection →
PK1.4 authoring tools → PK1.5 evidence/release. All are incremental changes.

Acceptance includes malicious ZIP fixtures, no partial installation, explicit
versions, unchanged base prompt/scorer snapshots, startup/chat/reports without
packs, exact subset coverage, preview agreement with sent options, checkpoint
stability after update/removal, bilingual copy and a clean release ZIP. Existing
tests, cp1251 startup, manifest and public privacy gates remain mandatory.
