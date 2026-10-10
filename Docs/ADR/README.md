# BULL Architecture Decision Records

ADR фиксируют решения, которые должны оставаться понятными независимо от будущего рефакторинга.

| ADR | Статус | Решение |
|---|---|---|
| [0001](0001-product-boundaries.md) | Accepted | Границы Benchmark Lab, Client, Agent Lab, GPU Lab и shared core |
| [0002](0002-legacy-schema-compatibility.md) | Accepted | Read-only legacy compatibility и copy migration |
| [0003](0003-metric-taxonomy.md) | Accepted | Разделение native, assisted, contract, runtime, recovery и других метрик |
| [0004](0004-benchmark-pack-registry.md) | Accepted | Versioned benchmark packs и data-first trust boundary |

Статусы ADR: `Proposed`, `Accepted`, `Superseded`, `Deprecated`.

Изменение принятого ADR выполняется новым ADR со ссылкой на superseded decision. История не переписывается.

