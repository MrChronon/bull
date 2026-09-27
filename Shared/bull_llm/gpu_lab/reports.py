"""Offline metrics only: not a model-quality or GPU marketing leaderboard."""
from collections import defaultdict
import csv
import html
from pathlib import Path

from ..storage import atomic_text
from ..presentation import terminal_text as safe_terminal_text
from .contracts import stats, number
from .messages import explain


def label(result, devices):
    names = {g['uuid']: g['name'] for g in result['inventory']}
    return ' + '.join(names.get(u, 'Unknown GPU') for u in devices)


def summary(result):
    groups = defaultdict(list)
    for row in result['completed']:
        for phase in row['phases']:
            key = (row['job']['model'], row['job']['workload'], tuple(row['job']['devices']), phase['phase'], phase['metrics']['load_class'])
            groups[key].append(phase)
    output = []
    for (model, workload, devices, phase, load), rows in groups.items():
        usable = [r for r in rows if r['comparable']]
        sensors = {}
        for uuid in devices:
            readings = [g for r in rows for s in r['samples'] for g in s.get('gpus', []) if g['uuid'] == uuid]
            sensors[label(result, [uuid])] = {k: stats([g.get(k) for g in readings])['max'] for k in ('memory_mib', 'temperature_c', 'power_w', 'utilization')}
        output.append(dict(model=model, workload=workload, gpu=label(result, devices), phase=phase, load=load,
                           n=len(rows), verified=len(usable), decode=stats([r['metrics']['decode_tok_s'] for r in usable]),
                           wall=stats([r['metrics']['wall_s'] for r in usable]),
                           ttft=stats([r['metrics']['ttft_client_s'] for r in usable]),
                           prefill=stats([r['metrics']['prefill_tok_s'] for r in usable]),
                           observed_decode=stats([r['metrics']['decode_tok_s'] for r in rows]), sensors=sensors))
    return output


def fmt(value): return '—' if value is None else f'{value:.2f}'


def terminal(result, emit=print):
    emit(f"GPU LAB · {result['status']} · готово {len(result['completed'])}/{len(result['jobs'])} пар запросов")
    if (result.get('active') or {}).get('error'):
        emit(safe_terminal_text('Пауза: ' + explain(result['active']['error'])))
    for row in summary(result):
        emit(safe_terminal_text(f"{row['model']} | {row['workload']} | {row['gpu']} | {row['phase']} / {row['load']}"))
        emit(f"  Подтверждено {row['verified']}/{row['n']} | decode {fmt(row['decode']['mean'])} tok/s | SD {fmt(row['decode']['sd'])} | min/max {fmt(row['decode']['min'])}/{fmt(row['decode']['max'])}")
        if not row['verified']: emit(f"  Только диагностика: наблюдалось {fmt(row['observed_decode']['mean'])} tok/s; выбор GPU или отсутствие фоновой нагрузки не подтверждены.")
        emit(f"  TTFT клиента {fmt(row['ttft']['mean'])} s | полный запрос {fmt(row['wall']['mean'])} s | prefill {fmt(row['prefill']['mean'])} tok/s")
        for name, sensor in row['sensors'].items():
            emit(safe_terminal_text(f"  {name}: VRAM {fmt(sensor['memory_mib'])} MiB · {fmt(sensor['temperature_c'])} °C · {fmt(sensor['power_w'])} W (пики всей карты)"))
    emit('Это измерения текущего эксперимента, не оценка качества. TTFT включает сеть; residency не доказывает равномерную работу двух GPU.')


def export(result, directory):
    root = Path(directory); rows = summary(result)
    with atomic_text(root / 'summary.csv', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['model','workload','gpu','phase','load','n','verified','decode_mean','decode_sd','decode_min','decode_max','wall_mean_s','ttft_client_mean_s'])
        for r in rows:
            values = [r[k] for k in ('model','workload','gpu','phase','load','n','verified')] + [r['decode'][k] for k in ('mean','sd','min','max')] + [r['wall']['mean'], r['ttft']['mean']]
            writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
    cards = []
    # Normalize bars only within the same model/workload/phase/load, never across models.
    scales = defaultdict(list)
    for r in rows: scales[(r['model'],r['workload'],r['phase'],r['load'])].append(r['decode']['mean'] or 0)
    for r in rows:
        maximum = max(scales[(r['model'],r['workload'],r['phase'],r['load'])]) or 1
        width = 100 * (r['decode']['mean'] or 0) / maximum
        heading = html.escape(f"{r['model']} · {r['workload']} · {r['phase']} / {r['load']}")
        cards.append(f'<article><small>{heading}</small><h2>{html.escape(r["gpu"])}</h2><div class="track"><div class="bar" style="width:{width:.2f}%"></div></div><p>{fmt(r["decode"]["mean"])} tok/s · SD {fmt(r["decode"]["sd"])} · min/max {fmt(r["decode"]["min"])}/{fmt(r["decode"]["max"])}</p><p>Подтверждено {r["verified"]}/{r["n"]} · TTFT {fmt(r["ttft"]["mean"])} s · запрос {fmt(r["wall"]["mean"])} s</p></article>')
    with atomic_text(root / 'report.html') as stream:
        status = html.escape(str(result['status']))
        progress = f'<p>Состояние: <strong>{status}</strong> · готово {len(result["completed"])}/{len(result["jobs"])} пар запросов.</p>'
        stream.write('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>GPU Lab</title><style>body{background:#101d24;color:#f1f6f8;font:17px system-ui;margin:0 auto;padding:32px;max-width:1100px}h1{color:#73f5b8}article{background:#1c303c;padding:24px;margin:16px 0;border:1px solid #3e697d;border-radius:14px}small{color:#bdd6e0}.track{height:14px;background:#35515e;border-radius:7px;overflow:hidden}.bar{height:100%;background:#69e7c0}p{line-height:1.6}</style><h1>GPU Lab · экспериментальные измерения</h1>' + progress + '<p>Сравнивайте одинаковые модели, сценарии и фазы. Нет оценок качества или общего победителя. Полосы нормированы внутри сопоставимой группы. Неподтверждённые запуски исключены из скорости сравнения. SD недоступен при одном измерении.</p>' + ''.join(cards) + '<p>Fresh process — новый процесс, не гарантированно холодный дисковый кеш. Repeat same prompt допускает повторное использование KV-кеша. Warm определяется по load_duration ≤ 100 ms. GPU residency подтверждает размещение процесса, но не баланс вычислений. Raw JSON приватный; этот отчёт не содержит промптов, ответов, адресов и GPU UUID. Имена моделей и карт остаются видимыми.</p></html>')
    return root / 'report.html'
