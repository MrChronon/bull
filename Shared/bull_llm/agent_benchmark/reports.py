"""Independent dimensions, no universal agent score or automatic winner."""
from __future__ import annotations

import csv
import html
from pathlib import Path

from .contracts import label
from ..storage import atomic_text

METRICS = [
    ("success", "Проверенный успех"), ("autonomous_success", "Без вмешательства"),
    ("duration_seconds", "Всего, с"), ("useful_completion_seconds", "До успеха, с"),
    ("first_useful_action_seconds", "До первого успешного tool, с"),
    ("human_interventions", "Вмешательства"), ("peak_context", "Пик входа, Ollama tokens"),
    ("peak_context_estimated", "Пик контекста, оценка"), ("compactions", "Compaction"),
    ("tool_calls", "Вызовы tools"), ("tool_failures", "Ошибки tools"),
    ("retries", "Ручные повторы запроса"), ("malformed_tool_calls", "Неверный формат tool"),
    ("prompt_tokens_processed", "Обработано prompt tokens"), ("generated_tokens", "Сгенерировано tokens"),
    ("prompt_tps", "Prompt tokens / eval seconds"), ("generation_tps", "Generation tok/s"),
    ("mean_ttft_seconds", "Средний TTFT, с"),
]


def number(value):
    if value is None:
        return "нет данных"
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float):
        return f"{value:.2f}"
    return label(value)


def comparison_warnings(runs):
    warnings = []
    for field in ("id", "version", "initial_state_sha256", "prompt_sha256", "verifier_version"):
        if len({str(x.get("task", {}).get(field)) for x in runs}) > 1:
            warnings.append("Различаются задача / исходные файлы / проверка: прямое сравнение некорректно.")
            break
    for field in ("instructions_sha256", "context_strategy", "compaction_keep_turns", "max_steps", "timeout_seconds"):
        if len({str(x["config"].get(field)) for x in runs}) > 1:
            warnings.append("Различаются правила или ограничения агента; учитывайте это как отдельный фактор.")
            break
    if len({str(x.get("model", {}).get("ollama_version")) for x in runs}) > 1:
        warnings.append("Различаются версии Ollama.")
    if len({str(x.get("system")) for x in runs}) > 1:
        warnings.append("Различаются клиентские среды.")
    if len({str(x.get("backend_system")) for x in runs}) > 1:
        warnings.append("Различаются снимки оборудования backend или их доступность.")
    if any(not any(r.get("effective_backend_context") is not None for r in x.get("requests", [])) for x in runs):
        warnings.append("У части runs backend не подтвердил фактический num_ctx.")
    if any(x.get("status") == "running" for x in runs):
        warnings.append("Есть незавершённая запись: процесс мог быть прерван. Успех не подтверждён.")
    warnings.append("Порядок и фоновые нагрузки не контролировались; один запуск не доказывает преимущество.")
    warnings.append("Пик RAM/VRAM — максимум выборки, не гарантированный абсолютный пик. Нет данных не означает 0.")
    return warnings


def table_rows(runs):
    rows = [("Модель", [x["config"]["model"] for x in runs]),
            ("Статус", [x["status"] for x in runs]),
            ("Backend / Agent context", [f"{x['config']['backend_context']} / {x['config']['agent_context']}" for x in runs]),
            ("Temperature / seed", [f"{x['config']['sampling']['temperature']} / {x['config']['sampling']['seed']}" for x in runs])]
    rows.extend((title, [number(x["metrics"].get(key)) for x in runs]) for key, title in METRICS)
    for scope in sorted({s for x in runs for s in x["metrics"].get("resources", {})}):
        for kind in ("ram", "vram"):
            vals = []
            for run in runs:
                memory = run["metrics"].get("resources", {}).get(scope, {}).get(kind, {})
                value = memory.get("peak_bytes")
                vals.append(number(value / 1024**3 if value is not None else None))
            rows.append((f"Peak {kind.upper()} {scope}, GiB", vals))
    return rows


def outcome_lines(run):
    """Display-only interpretation; raw metrics, verifier and error records are unchanged."""
    metrics = run.get('metrics', {})
    verification = run.get('verification', {})
    failed_checks = sum(x.get('category') == 'build_test_failure' for x in run.get('errors', []))
    other_events = len(run.get('errors', [])) - failed_checks
    state = {'success': 'Задача выполнена', 'running': 'Результат ещё не подтверждён',
             'backend_error': 'Прервана связь с backend', 'interrupted': 'Запуск остановлен',
             'timeout': 'Истёк лимит времени'}.get(run.get('status'), label(run.get('status')))
    lines = [state + f" · проверок: {verification.get('passed', '?')}/{verification.get('total', '?')}",
             f"Время: {number(metrics.get('duration_seconds'))} с · tools: {number(metrics.get('tool_calls'))} · "
             f"вмешательств: {number(metrics.get('human_interventions'))}",
             f"Неудачных проверок кода: {failed_checks} (не сбои приложения; промежуточные попытки)",
             f"Других диагностических событий: {other_events}"]
    if metrics.get('repeated_tool_calls'):
        lines.append('Одинаковые вызовы tools могут быть проверками после правки; это не число сетевых повторов.')
    resources = metrics.get('resources', {})
    scope = 'backend' if 'backend' in resources else 'client_and_backend'
    title = 'этого ПК (клиент + сервер)' if scope == 'client_and_backend' and scope in resources else 'сервера'
    for kind in ('ram', 'vram'):
        memory = resources.get(scope, {}).get(kind, {}).get('peak_bytes')
        lines.append(f"{kind.upper()} {title}: " + (number(memory / 1024**3) + ' GiB (максимум выборки)' if memory is not None else 'нет данных'))
    return lines


def terminal_summary(run, emit=print):
    emit('\nAGENT BENCHMARK — итог')
    for line in outcome_lines(run):
        emit('  ' + line)
    emit('  Подробности и сравнение доступны отдельно. Один запуск не измеряет устойчивость.')


def terminal_comparison(runs, emit=print):
    for start in range(0, len(runs), 3):
        group = runs[start:start + 3]
        emit("\nAGENT BENCHMARK / независимые показатели")
        emit("Показатель".ljust(38) + " | " + " | ".join(f"Run {start+i+1}".ljust(24) for i in range(len(group))))
        emit("-" * (40 + len(group) * 27))
        for title, vals in table_rows(group):
            emit(label(title).ljust(38) + " | " + " | ".join(label(v)[:24].ljust(24) for v in vals))
        for index, run in enumerate(group, start + 1):
            emit(f"Run {index}: {label(run['run_id'])} | {label(run['config']['model'])}")
    for warning in comparison_warnings(runs):
        emit("  " + warning)


def export_csv(path, runs):
    def cell(value):
        text = label(value)
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
    with atomic_text(path, encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric"] + [cell(x["run_id"]) for x in runs])
        for title, values in table_rows(runs):
            writer.writerow([title] + [cell(x) for x in values])


def report_html(runs):
    escape = lambda value: html.escape(label(value), quote=True)
    rows = "".join("<tr><th>" + escape(title) + "</th>" + "".join("<td>" + escape(x) + "</td>" for x in values) + "</tr>"
                   for title, values in table_rows(runs))
    charts = []
    for run in runs:
        points = run.get("contexts", [])
        maximum = max([x["tokens"] for x in points] + [1])
        duration = max([x["elapsed_seconds"] for x in points] + [1])
        series = []
        for source, color in (("estimate", "#55ddaa"), ("ollama_prompt_eval_count", "#f8c96b")):
            coords = " ".join(f"{40 + 700*x['elapsed_seconds']/duration:.1f},{220-180*x['tokens']/maximum:.1f}"
                              for x in points if x["source"] == source)
            series.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>')
        markers = "".join(f'<circle cx="{40+700*x["elapsed_seconds"]/duration:.1f}" cy="235" r="4" fill="#fa9"><title>{escape(x["type"])}</title></circle>'
                          for x in run.get("events", []) if x["type"] in ("compaction", "error", "human_intervention", "tool_completed", "task_completed"))
        charts.append(f'<h2>{escape(run["run_id"])}</h2><svg viewBox="0 0 780 270" role="img" aria-label="Context timeline"><text x="10" y="20" fill="white">{maximum} tokens</text>{"".join(series)}{markers}<text x="40" y="260" fill="white">0 — {duration:.1f} seconds</text></svg>')
    return ('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
            '<title>Agent Benchmark</title><style>body{background:#101b20;color:#eef7f2;font:16px system-ui;margin:30px} '
            'h1,h2{color:#77eabb}table{border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #47615a;text-align:left} '
            'svg{max-width:900px;display:block}p{max-width:1000px}</style><h1>Agent Benchmark — сравнение</h1>'
            '<p>Независимые показатели результата, автономности и ресурсов. Универсальный рейтинг не вычисляется.</p><table>'
            + '<tr><th>Показатель</th>' + ''.join('<th>' + escape(x['run_id']) + '</th>' for x in runs) + '</tr>' + rows + '</table>'
            + ''.join('<p>' + escape(x) + '</p>' for x in comparison_warnings(runs))
            + '<p>Контекст: зелёный — оценка; жёлтый — фактический вход запроса по Ollama. Маркеры — tools, compaction, ошибки и вмешательства.</p>'
            + ''.join('<h2>Как читать результат</h2>' + ''.join('<p>'+escape(x)+'</p>' for x in outcome_lines(run)) for run in runs)
            + ''.join(charts) + '</html>')


def save_report(path, runs):
    with atomic_text(path) as stream:
        stream.write(report_html(runs))
