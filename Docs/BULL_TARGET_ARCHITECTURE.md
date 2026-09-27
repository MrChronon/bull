# BULL Target Architecture

**Статус:** Accepted target for incremental migration  
**Дата:** 2026-09-26  
**Важно:** структура целевая; T0 не перемещает существующие файлы.

## 1. Архитектурная цель

Отделить benchmark definition, execution, scoring, telemetry и reporting от UI и transport, сохранив Client, Agent Lab, GPU Lab и compatibility с Local LLM.

## 2. Целевой layout

```text
BULL/
  Apps/
    bull_desktop/
    bull_benchmark_lab/
    bull_client/
    bull_agent_lab/
    bull_gpu_lab/

  Packages/
    bull_llm/
      core/
        contracts/
        fingerprints/
        profiles/
        provenance/
        validation/
      runtime/
        ollama/
        llama_cpp/
        ssh/
        streaming/
        recovery/
      evaluation/
        registry/
        planning/
        runners/
        scoring/
        statistics/
        checkpoints/
      agents/
        contracts/
        tools/
        isolation/
        verifiers/
      telemetry/
        system/
        nvidia/
        timing/
      reports/
        terminal/
        html/
        csv_json/
      security/
        redaction/
        paths/
        release_audit/

  BenchmarkPacks/
    bull_chat_core/
    bull_ru_dialogue/
    bull_local_system/
    bull_resilience/
    bull_agent/
    bull_long_context/
    bull_security/
    bull_robustness/

  Adapters/
    lm_eval/
    inspect_ai/

  Compatibility/
    local_llm_v1/
    schema_migrations/

  Schemas/
  Docs/
  Tests/
    unit/
    contracts/
    golden/
    scorer/
    fault_injection/
    security/
    packaging/
```

## 3. Dependency direction

```text
Apps
 ├─> application services
 ├─> presentation adapters
 └─> public contracts

Evaluation ─> Core contracts
Evaluation ─> Runtime interfaces
Evaluation ─> Telemetry interfaces
Evaluation ─> ArtifactStore interface

Runtime ─> Core contracts
Reports ─> result/summary contracts
Benchmark packs ─> registry contracts
Compatibility ─> legacy readers + new contracts
```

Запрещённые зависимости:

- `core -> Apps`;
- `runtime -> UI`;
- `scorer -> transport`;
- `reports -> inference`;
- `benchmark pack -> private Runtime state`;
- `Client -> scorer implementation`;
- `GPU Lab -> рабочий Ollama process ownership`.

## 4. Публичные интерфейсы

### BackendAdapter

```text
health()
list_models()
describe_model(model_id)
generate(request, event_sink)
cancel(request_id)
runtime_fingerprint()
```

### BenchmarkPack

```text
manifest()
list_cases()
load_case(case_id, version)
validate()
```

### Runner

```text
build_plan(config)
run_case(case, model, runtime, telemetry)
resume(checkpoint)
```

Runner types:

- single-turn;
- multi-turn;
- agent;
- performance;
- fault-injection;
- human-pairwise.

### Scorer

```text
score(case, native_response, execution_context)
```

Scorer возвращает dimensions, evidence, critical failures, applicability и scorer identity. Он не выполняет recovery и не вызывает backend.

### Verifier

Точная проверка JSON, вычисления, tool calls, файлов и конечного sandbox state. Недоверенный generated code не исполняется в основном процессе.

### TelemetryProvider

```text
capabilities()
start_scope()
sample()
finish_scope()
```

### ArtifactStore

Гарантирует unique temp file, bounded serialization, `fsync`, atomic replace, SHA-256, path validation и private/share-safe classification.

### ReportRenderer

Получает immutable summary и создаёт представление. Report renderer не пересчитывает score или statistics.

## 5. Основные data flows

### Benchmark

```text
UI config
  -> validated RunPlan
  -> Registry loads exact Pack/Case
  -> Runtime generates native response
  -> Scorer/Verifier evaluates native response
  -> optional explicit recovery
  -> assisted evaluation
  -> Telemetry finalization
  -> immutable Record
  -> Checkpoint/ArtifactStore
  -> Summary
  -> terminal/HTML/CSV/JSON reports
```

### Tested profile

```text
Benchmark result
  -> explicit profile export
  -> versioned tested profile
  -> user preview in Client
  -> explicit import
```

Benchmark никогда не изменяет активный Client profile без preview и подтверждения.

### Legacy artifact

```text
Legacy file
  -> read-only reader
  -> validation + source SHA-256
  -> compatibility view
  -> optional explicit copy migration
```

## 6. Current-to-target map

| Current v0.21 component | Target ownership |
|---|---|
| `Apps/llm_client_*` | `Apps/bull_client` |
| `Apps/benchmark_lab_*` | `Apps/bull_benchmark_lab` |
| `Apps/agent_benchmark_*` | `Apps/bull_agent_lab` |
| `Shared/local_llm_shared/backends.py` | `bull_llm.runtime` interfaces/adapters |
| `http_transport.py` | `bull_llm.runtime.streaming/http` |
| `profiles.py` | `bull_llm.core.profiles` |
| `schemas.py` | `bull_llm.core.contracts` |
| `storage.py` | `ArtifactStore` implementation |
| `telemetry.py` | `bull_llm.telemetry` |
| `terminal_ui.py`, `presentation.py` | App/presentation adapters |
| `agent_benchmark/*` | `bull_llm.agents` + Agent application |
| `gpu_lab/*` | GPU application + telemetry/runtime services |
| monolithic built-in benchmark definitions | `BenchmarkPacks/bull_chat_core` |
| legacy schema readers | `Compatibility/local_llm_v1` |

## 7. Naming map

| Existing | Transition | Target |
|---|---|---|
| Local LLM | BULL — Local LLM Benchmark Lab | BULL |
| `local_llm_shared` | compatibility facade | `bull_llm` |
| `Local-LLM-*.cmd` | alias with notice | `BULL-*.cmd` |
| `local-llm-*` schemas | immutable legacy IDs | `bull-llm-*` for new schemas |
| `Local-LLM-*-Bundle` | retained old bundles | `BULL-vX.Y.Z-Bundle` |
| `local_llm` repository | retained through T1 preparation | qualified BULL repository after owner gate |

## 8. Extraction order

1. Add contracts around current behavior.
2. Add contract/golden tests.
3. Extract storage and fingerprints.
4. Extract backend adapters.
5. Extract evaluation orchestration.
6. Move Chat Core to registry without content changes.
7. Switch reports to unified summary.
8. Add new packs only after parity.
9. Remove legacy internal route only when unused and tested.

## 9. Trust boundaries

- public benchmark packs are data-first;
- executable plugins require separate installation and explicit trust;
- Agent verifier runs out-of-process in a later isolated-executor stage;
- remote inference stays behind pinned SSH or equivalent secure tunnel;
- public reports are generated from share-safe summaries;
- raw records, prompts, answers, connections and model paths remain private;
- no external URLs or scripts in offline HTML.

## 10. T0 non-actions

Этот документ не разрешает:

- перемещать текущие Python modules;
- переименовывать launchers;
- менять schema IDs;
- изменять benchmark content;
- создавать migration artifacts;
- публиковать новый release.

Реализация начинается только после product-owner gate между T0 и T1.

