"""Synthetic, editable starter content; never an engine catalog fallback."""
from __future__ import annotations

import json


def starter_files(pack_id, language, engine_version):
    ru = language == "ru"
    title = "Извлечение синтетической заявки" if ru else "Synthetic ticket extraction"
    description = "Проверка полей, не смысловой анализ обращения" if ru else "Field checks, not semantic interpretation"
    prompt = ("Извлеки поля из синтетической записи.\n"
              "Запись: заявка B-104; количество 3; подтверждение не получено.\n"
              "Верни result.id как строку, result.quantity как число и\n"
              "result.confirmed как boolean. Не предполагай наличие подтверждения." if ru else
              "Extract fields from this synthetic record.\n"
              "Record: ticket B-104; quantity 3; confirmation not received.\n"
              "Return result.id as a string, result.quantity as a number and\n"
              "result.confirmed as a boolean. Do not assume confirmation.")
    task = f"""schema: bull-user-test
version: 1
id: ticket_extraction
title: {title}
description: {description}
language: {language}
prompt: |
""" + "".join("  " + line + "\n" for line in prompt.splitlines()) + """criteria:
  - id: ticket_identifier
    type: terminal_json_equals
    description: Preserve the identifier exactly
    weight: 40
    path: result.id
    expected: B-104
  - id: ticket_quantity
    type: terminal_json_equals
    description: Preserve the declared quantity
    weight: 35
    path: result.quantity
    expected: 3
  - id: ticket_confirmation
    type: terminal_json_equals
    description: Do not invent confirmation
    weight: 25
    path: result.confirmed
    expected: false
    critical: true
manual_review:
  - Check any prose for contradictions with the JSON.
"""
    source = {
        "schema": "bull-pack-workspace", "schema_version": 1, "id": pack_id, "version": "1.0.0",
        "title": title, "description": description, "status": "experimental", "visibility": "private",
        "minimum_engine_version": str(engine_version).removeprefix('v'),
        "license": {"id": "LicenseRef-Private-Review", "name": "Private draft; review data rights before redistribution"},
        "provenance": {"source": "Synthetic author starter; no real ticket data"},
        "tasks": [{"file": "Tasks/ticket.yaml", "category": "field_extraction", "case_version": 1}],
    }
    good = 'BENCHMARK_RESULT\n{"result":{"id":"B-104","quantity":3,"confirmed":false}}'
    fixtures = {"schema": "bull-author-fixtures", "schema_version": 1, "cases": [{"id": "ticket_extraction", "answers": [
        {"id": "correct_fields", "kind": "positive", "answer": good, "expected_score": 1.0, "failed_checks": []},
        {"id": "invented_confirmation", "kind": "negative", "answer": good.replace("false", "true"), "expected_score": 0.59,
         "failed_checks": ["ticket_confirmation"]},
        {"id": "trailing_prose", "kind": "negative", "answer": good + "\nExtra text.", "expected_score": 0.0,
         "failed_checks": ["ticket_identifier", "ticket_quantity", "ticket_confirmation"]},
    ]}]}
    readme = ("""# Набор для извлечения полей

Синтетическая заявка: B-104, количество 3, подтверждение отсутствует.
Проверяются точные поля JSON; веса 40/35/25. Выдуманное подтверждение
критично и ограничивает балл 59%. Текст после JSON проваливает JSON-критерии.
Пояснения требуют ручной проверки. Это не проверка реальных обращений.

Отредактируйте author.json, Tasks/ticket.yaml и fixtures.json в UTF-8.
Добавьте самостоятельные задания под свои задачи, обоснуйте эталоны и допуски.
Запустите проверку в мастерской, затем соберите ZIP вне этой папки.
Рабочая папка не является установленным набором. Обновление выпускается новой
версией. Не добавляйте секреты: ZIP сохраняет prompts, критерии и ответы fixtures.
Укажите свою лицензию и происхождение данных до распространения.
""" if ru else """# Field extraction pack

Synthetic ticket: B-104, quantity 3, confirmation absent.
Exact JSON fields are checked with weights 40/35/25. Invented confirmation
is critical and caps quality at 59%. Trailing text fails JSON criteria.
Prose needs manual review. This does not assess real support tickets.

Edit author.json, Tasks/ticket.yaml and fixtures.json as UTF-8.
Add independent tasks for your use case; justify references and tolerances.
Validate in Author Workshop, then build a ZIP outside this directory.
The workspace is not installed. Updates require a new version.
Do not add secrets: ZIPs retain prompts, criteria and fixture answers.
Declare your own license and data provenance before redistributing.
""")
    def payload(value):
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    return {"author.json": payload(source), "fixtures.json": payload(fixtures),
            "Tasks/ticket.yaml": task.encode("utf-8"), "README.md": readme.encode("utf-8"),
            "LICENSE.txt": b"Private draft. No redistribution permission is claimed for user-added material.\n"}
