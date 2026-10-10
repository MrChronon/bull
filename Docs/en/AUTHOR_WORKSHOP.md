# Author Workshop

[Русская версия](../ru/AUTHOR_WORKSHOP.md)

Available in BULL v0.29.0.1 Pack Library.
No model, backend connection or third-party Python package is needed.

## Create, edit, check, build

Open **Home → Test settings → Author Workshop**.

1. **Create an editable starter**. Enter a unique lowercase pack ID, such as
   `my_tasks`. The starter uses your interface language and synthetic data.
2. **Open selected workspace folder**. Edit its UTF-8 files in a text editor.
   You can also select an already prepared source folder by path.
3. **Validate sources and answer fixtures**. Green PASS means the observed score
   and failed criterion IDs match the fixture. Red FAIL shows a disagreement.
   Fix references, rules or fixture expectations before building. If sources
   change after preview, repeat validation before confirming a ZIP build.
4. **Build ZIP**. Review the source/fixture disclosure warning and confirm.
5. Return to the library and **Import my ZIP**, then choose its tests.

Creating a workspace or ZIP does not install, select, run or publish a pack.
The default starter is `private` and `experimental`; it claims no permission
to redistribute user-added data. Declare actual rights before distribution.

## Files and storage

Windows library: `%LOCALAPPDATA%\BULL\BenchmarkPacks`.
Workspaces live in `Workspaces/<id>-<unique_id>/`; exported ZIPs live in
`PackExports/<id>@<version>.zip`. They survive application updates. These are
private user files, never part of the BULL release. Remove unwanted workspaces
or exported ZIPs manually after backing up anything you need.

```text
author.json          pack metadata and explicit task list
Tasks/ticket.yaml    one scored task per file
Tasks/poem.txt       optional unscored task
fixtures.json        expected positive and negative answers
README.md            purpose, coverage, references and limitations
LICENSE.txt          actual distribution terms for this pack/data
```

Only those declared source files are accepted. Move personal notes, secrets,
outputs and unrelated files outside the workspace. A ZIP deliberately preserves
all declared sources under `Source/`, including prompts and fixture answers.
It is not a share-safe benchmark report. Review it before sharing.

## author.json contract

This is an author-source schema, not a replacement for runnable manifest v1.
The builder generates the manifest, compiled cases, gold snapshots and lock.

```json
{
  "schema": "bull-pack-workspace",
  "schema_version": 1,
  "id": "my_tasks",
  "version": "1.0.0",
  "title": "Ticket extraction",
  "description": "Synthetic field checks; not semantic review",
  "status": "experimental",
  "visibility": "private",
  "minimum_engine_version": "0.29.0.1",
  "license": {"id": "LicenseRef-Private-Review", "name": "Private draft"},
  "provenance": {"source": "Synthetic records"},
  "tasks": [
    {"file": "Tasks/ticket.yaml", "category": "field_extraction", "case_version": 1}
  ]
}
```

Unknown fields and duplicate JSON keys fail validation. IDs use lowercase ASCII
letters, digits and underscores, start with a letter, and have 3–64 characters.
Versions have three or four numeric components. Status is `experimental` or
`candidate`, not a self-awarded `stable` certification. Visibility is `private`
or `public`; `public` does not upload anything. Provenance has required `source`
and optional `author`. Never include credentials, endpoints or private paths.
Update the license ID/name and `LICENSE.txt` consistently; BULL's MIT license
does not automatically license your data.

Every task has `file`, `category` and integer `case_version` (1–1000000). The file
must be directly under `Tasks/`. Categories are lowercase ASCII identifiers,
2–64 characters. YAML contains its own ID/title/description/language/prompt and
criteria; do not duplicate these fields in its descriptor. For `.txt`, the
descriptor additionally requires `id`, `title`, `description` and `language`
(`en`, `ru` or `auto`). Text is a prompt only and has no automatic quality score.
Mixed domains and language variants may coexist in one pack; case IDs are unique.

Optional `parameters` supports only:

| Field | Accepted value |
| --- | --- |
| `primary_predict`, `recovery_predict` | integer 1–32768 |
| `think_override` | boolean |
| `benchmark_defaults.ctx` | integer 512–262144 |
| `benchmark_defaults.num_predict` | integer 1–32768; must agree with `primary_predict` if both are set |
| `benchmark_defaults.num_thread` | integer 1–256 |
| `benchmark_defaults.temperature` | number 0–2 |
| `benchmark_defaults.top_p`, `min_p` | number 0–1 |
| `benchmark_defaults.top_k` | integer 0–1000 |
| `benchmark_defaults.repeat_penalty` | number 0–2 |

These use the existing runtime's defaults/override rules, not new hard constraints.
Named run profiles and explicit overrides can replace defaults. `think_override`
is an explicit task policy. The launch plan shows resolved settings; model-profile
sampling remains inherited and omitted from API options. No chat settings change.
Use `ctx`, not `num_ctx`, in this source contract. Unsupported parameters fail.

## YAML criteria and fixture answers

Use the exact task schema, six criterion types, weights summing to 100, tolerances
and critical cap in [LLM author instructions](PACK_AUTHOR_LLM.md). YAML source
schema `version: 1` is distinct from descriptor `case_version`.

`fixtures.json` has schema `bull-author-fixtures`, `schema_version: 1`, and `cases`.
Each scored case appears exactly once with its ID and 2–64 answer objects:

```json
{
  "id": "invented_confirmation",
  "kind": "negative",
  "answer": "BENCHMARK_RESULT\n{\"result\":{\"id\":\"B-104\",\"quantity\":3,\"confirmed\":true}}",
  "expected_score": 0.59,
  "failed_checks": ["ticket_confirmation"]
}
```

An answer object has exactly `id`, `kind`, `answer`, `expected_score` and
`failed_checks`. Score is a finite fraction 0–1, not a percentage. `positive`
expects 1 and no failed checks; `negative` expects less than 1 and distinct
criterion IDs. Every scored case needs at least one positive. Across negatives,
every criterion must fail at least once. One fixture may cover several criteria.
Unscored text cases do not appear in this file; an entirely unscored pack uses
`"cases": []`. Manual review is never turned into a numeric score.

The starter includes a correct answer, invented confirmation (59% cap), and
trailing prose (all JSON checks fail). Also add missing-field, type, boundary and
domain-error fixtures where relevant. Matching fixtures proves rule behavior,
not reference truth, task representativeness or professional safety. A person
must verify assumptions, calculations, units, rights and semantic limitations.

## Updates, bounds and commands

**Copy an authored installed pack to a new version** requires `ID@version` and
a different explicit version. Source hashes and compiled content are checked
before copying; the installed version, active selection and old runs stay intact.
Old native packs without workshop `Source/` cannot be converted automatically:
request editable sources from their author or keep their maintainer tool.
Do not replace native scoring with keyword rules to simulate compatibility.

ZIP output is deterministic and never overwrites an existing file. Choose a new
version/output. A changed prompt or criterion also needs an appropriate new
`case_version`. Version labels do not by themselves prove compatibility.

Bounds: 1,000 tasks; 256 KiB per task/document; 50,000 prompt characters; 1–20
criteria; 8 MiB author/fixture/compiled JSON; 64 MiB archive; 128 MiB expanded;
4,096 entries including copied sources. These may limit a pack before the task
count does. No legacy 100-task truncation occurs. ZIP installation still checks
its own bounds and hashes. No author code, shell, regex, YAML tags or imports run.

CLI alternative, from the application directory:

```powershell
python Tools/build_author_pack.py create my_tasks --language en
python Tools/build_author_pack.py validate "PATH_TO_WORKSPACE"
python Tools/build_author_pack.py build "PATH_TO_WORKSPACE" --output "PATH_TO_OUTPUT.zip"
python Tools/build_author_pack.py copy my_tasks 1.0.0 1.1.0
```

`validate` returns exit 1 on invalid sources or fixture disagreements. `build`
also validates the runnable registry contract and ZIP preflight, and refuses a
ZIP path inside its source directory. `--library-root` before the subcommand
overrides storage for isolated tests. No command publishes or installs anything.
