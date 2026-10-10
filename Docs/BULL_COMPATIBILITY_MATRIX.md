# BULL Compatibility Matrix

**Статус:** Accepted for T0  
**Дата:** 2026-09-26  
**Historical producer:** pre-BULL releases and supported historical readers

## 1. Политика

- `Read` означает безопасный read-only разбор и отображение.
- `Migrate copy` означает создание нового BULL artifact без изменения source.
- `Resume` является более строгой возможностью и не следует автоматически из `Read`.
- `No auto-migrate` запрещает фоновое изменение при открытии.
- Raw/private artifacts по умолчанию остаются private после migration.

## 2. Benchmark artifacts

| Artifact | Legacy version | Read | Migrate copy | Resume | Решение |
|---|---:|---|---|---|---|
| Benchmark config | 3 | Да | Да | Н/Д | Сохранить неизвестные поля или блокировать migration |
| Benchmark spec | 9 | Да | Да | Н/Д | Сохранить test/runtime identity и hashes |
| Benchmark record | 12 | Да | Да | Н/Д | Legacy score остаётся неизменным; новая taxonomy добавляется отдельно |
| Benchmark summary | 11 | Да | Да | Н/Д | Не выводить отсутствующие legacy metrics как нули |
| Benchmark checkpoint | 9 | Да | Только после validation | Условно | Resume только при подтверждённой engine/runtime compatibility |
| Tested profile | 1 | Да | Да | Н/Д | Импорт остаётся явным; профиль не применяется автоматически |
| Prompt index | 2 | Да | Да | Н/Д | Immutable prompt versions и SHA-256 сохраняются |
| User benchmark | 1 | Да | Да | Н/Д | Пользовательский content остаётся private по умолчанию |

## 3. Agent artifacts

| Artifact | Schema | Read | Migrate copy | Continue | Решение |
|---|---|---|---|---|---|
| Agent configuration | `bull-agent-config` v1 | Да | Да, private | Нет | Config валидируется повторно; secrets не копируются |
| Agent run | `bull-agent-run` v1 | Да | Да | Нет | Старый run остаётся завершённым evidence; retry создаёт новый run с parent ID |

## 4. GPU artifacts

| Artifact | Schema | Read | Migrate copy | Resume | Решение |
|---|---|---|---|---|---|
| GPU experiment | `bull-gpu-experiment` v1 | Да | Да | Условно | Resume требует совпадения config/workload hashes, inventory, driver, Ollama и model digest |
| GPU result private | v1 envelope | Да | Да, private | Н/Д | GPU UUID и custom prompt не становятся share-safe |
| GPU summary CSV | derived | Да | Перегенерировать | Н/Д | Не использовать как canonical source |
| GPU report HTML | derived | Открыть | Перегенерировать | Н/Д | Не извлекать canonical data из HTML |

## 5. Other state

| State | Read/import | Автоматический перенос | Public release | Решение |
|---|---|---|---|---|
| `backend_settings.json` | Через validated preview | Нет | Запрещён пользовательский файл | Не копировать поверх новой factory config |
| `Runtime/connections.json` | Явный import | Нет | Запрещён | Ключевые данные и endpoints остаются private |
| Windows connection vault | Явный выбор | Нет | Вне repository | Не копировать key bytes |
| Chat sessions | Явное открытие/import | Нет | Запрещены | Не являются benchmark evidence |
| Custom prompts | Явный import | Нет | Запрещены по умолчанию | Сохранить version и SHA-256 |
| Raw benchmark JSON | Да | Только private copy | Не share-safe | Может содержать prompts, answers и локальные metadata |
| Summary JSON/CSV | Да | Перегенерировать из canonical record | После audit | Не использовать для resume |
| Offline HTML | Открыть | Перегенерировать | После audit | Metrics-only, no prompts/raw answers |
| `analysis_result.schema.json` | Валидация текущей формы | Нет | Допускается как internal schema | Legacy schema не имеет ID/version; сначала требуется formal versioning |

## 6. Legacy-to-BULL mapping

Новый artifact, созданный migration tool, обязан содержать:

```json
{
  "migration": {
    "source_schema": "legacy schema identifier",
    "source_schema_version": 1,
    "source_basename": "result.json",
    "source_sha256": "...",
    "migration_id": "historical-to-bull",
    "migration_version": 1,
    "migrated_at": "ISO-8601 timestamp"
  }
}
```

Абсолютный source path не переносится в portable metadata.

## 7. Checkpoint compatibility gate

Resume допускается только при успешной проверке:

- schema и producer compatibility;
- plan identity;
- pack/test/prompt hashes;
- scorer и execution-policy fingerprints;
- backend kind;
- model catalog и required models;
- model digest policy;
- completed record integrity;
- active run state;
- отсутствие второго владельца checkpoint.

Если проверка не доказала совместимость, BULL предлагает:

1. открыть checkpoint read-only;
2. завершить его исходной версией;
3. начать новый BULL run;
4. никогда не использовать silent force.

## 8. Support horizon

Legacy readers, перечисленные в этой матрице, входят в переходную поддержку до BULL v1.0. Удаление после v1 возможно только через отдельный ADR, deprecation period и major-version policy.

