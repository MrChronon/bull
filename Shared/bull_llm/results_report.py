"""Offline, data-only result views. No scorer, transport or inference dependency.

All quality values are supplied by existing summaries. Resource rollups and
rankings are descriptive views, never new benchmark scores. Private record
payloads are reduced to an explicit numeric/enum allowlist before rendering.
"""
from __future__ import annotations

import base64
from collections import Counter
import hashlib
from html import escape
import json
import math
from pathlib import Path
import re
import textwrap

from .decision_support import build_decision_support, _number


COLORS = ('#FF3C52', '#51C8FF', '#FFC857', '#BC9CFF', '#42D9AD', '#FF91C0', '#93B7FF')
PARAMETERS = ('ctx', 'threads', 'primary_predict', 'temperature', 'top_p', 'top_k',
              'min_p', 'repeat_penalty', 'think')
SOURCE_NAMES = ('benchmark_override', 'model_profile', 'per_model',
                'benchmark_default', 'run_override', 'model_profile_parameter',
                'per_model_override', 'backend_default_unresolved', 'global_default',
                'model_capability_override', 'benchmark_constraint', 'named_profile')


def clean(value):
    # Model labels are untrusted data, never terminal escape sequences.
    value = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(value))
    return ''.join(c for c in value if c >= ' ' and c != '\x7f')[:512]


def h(value):
    return escape(clean(value), quote=True)


def choose(language, en, ru):
    return ru if language == 'ru' else en


def fmt(value, suffix='', digits=1):
    number = _number(value)
    return '—' if number is None else f'{number:.{digits}f}{suffix}'


def pct(value):
    value = _number(value)
    return '—' if value is None else fmt(value * 100, '%')


def values_mean(values):
    values = [number for value in values if (number := _number(value)) is not None]
    return sum(values) / len(values) if values else None


def values_max(values):
    return max((number for value in values if (number := _number(value)) is not None), default=None)


def at(row, path):
    for key in path.split('.'):
        if not isinstance(row, dict):
            return None
        row = row.get(key)
    return row


def execution_ok(row):
    return row.get('execution_status', 'ok') == 'ok' and not row.get('error')


def report_observations(records):
    """Only roll up measured numbers and approved settings; never take raw text."""
    records = list(records)
    ok = [row for row in records if execution_ok(row)]
    result = {'observed_runs': len(records), 'successful_runs': len(ok),
              'failed_runs': len(records) - len(ok)}
    for output, source, reducer in (
        ('pipeline_wall_avg', 'final.pipeline_wall_seconds', values_mean),
        ('gpu_util_avg', 'telemetry.gpu.gpu_util_avg', values_mean),
        ('cpu_util_avg', 'telemetry.system.cpu_util_avg', values_mean),
        ('ram_peak_bytes', 'telemetry.system.ram_used_peak_bytes', values_max),
        ('ram_total_bytes', 'telemetry.system.ram_total_bytes', values_max),
    ):
        result[output] = reducer(at(row, source) for row in ok)
    result['ram_peak_gib'] = result.pop('ram_peak_bytes')
    if result['ram_peak_gib'] is not None:
        result['ram_peak_gib'] /= 1024 ** 3
    for key, path in (('cpu_sensor_runs', 'telemetry.system.cpu_util_avg'),
                      ('ram_sensor_runs', 'telemetry.system.ram_used_peak_bytes'),
                      ('gpu_sensor_runs', 'telemetry.gpu.gpu_util_avg')):
        result[key] = sum(_number(at(row, path)) is not None for row in ok)
    result['load_counts'] = dict(Counter(at(row, 'primary.load_state')
                                        if at(row, 'primary.load_state') in ('cold', 'warm')
                                        else 'unknown' for row in ok))
    result['seeds_observed'] = sorted({_number(at(row, 'config.seed')) for row in records
                                       if _number(at(row, 'config.seed')) is not None})
    slots = Counter(json.dumps([at(row, 'identity.benchmark'), at(row, 'config.seed'),
                                at(row, 'identity.benchmark_version'),
                                at(row, 'identity.benchmark_prompt_sha256'),
                                at(row, 'identity.benchmark_mode')], sort_keys=True) for row in records)
    result['comparison_signature'] = hashlib.sha256(json.dumps(sorted(slots.items())).encode()).hexdigest()
    result['comparison_complete'] = len(ok) == len(records) and not any(row.get('sweep') for row in records)
    settings = {}
    for key in PARAMETERS:
        seen = []
        for row in ok:
            value = at(row, f'config.{key}')
            if (key == 'think' and isinstance(value, bool)) or (not isinstance(value, bool) and _number(value) is not None):
                if value not in seen:
                    seen.append(value)
        settings[key] = sorted(seen)
    result['report_settings'] = settings
    provenance = {}
    for key in PARAMETERS:
        public_key = {'ctx': 'num_ctx', 'threads': 'num_thread', 'primary_predict': 'num_predict'}.get(key, key)
        entries = []
        for row in ok:
            entry = at(row, f'config.parameter_sources.{public_key}')
            if not isinstance(entry, dict):
                continue
            source = entry.get('source') if entry.get('source') in SOURCE_NAMES else 'unknown'
            value = entry.get('value')
            value = value if key=='think' and isinstance(value,bool) else _number(value)
            safe = {'value': value, 'source': source, 'sent': entry.get('sent_in_request') if isinstance(entry.get('sent_in_request'),bool) else None}
            if safe not in entries:
                entries.append(safe)
        provenance[key] = entries
    result['report_parameter_sources'] = provenance
    result['sampling_sources'] = sorted({at(row, 'config.sampling_source') for row in ok
                                        if at(row, 'config.sampling_source') in SOURCE_NAMES})
    result['client_transport_failures'] = sum(_number(at(row, 'client_recovery.transport_failures')) or 0 for row in records)
    return result


def reason_text(reasons, language):
    labels = {
        'quality_unknown': ('no automatic quality score', 'нет автоматической оценки качества'),
        'quality_below_gate': ('quality below recommendation threshold', 'качество ниже порога рекомендации'),
        'task_below_gate': ('task completion below 80%', 'выполнение контракта ниже 80%'),
        'metrics_missing': ('missing comparable metrics', 'нет сопоставимых метрик'),
        'unequal_coverage': ('unequal, failed or mixed coverage', 'разное покрытие, ошибки или смешанные настройки'),
    }
    return '; '.join(choose(language, *labels.get(reason, ('unavailable', 'недоступно'))) for reason in reasons)


def top_places(rows):
    return [row for row in rows if row.get('rank') is not None and row['rank'] <= 3]


def wrap_lines(lines, width):
    return [part for line in lines for part in (textwrap.wrap(clean(line), width=max(35, width),
             subsequent_indent='  ', break_long_words=True, break_on_hyphens=False) or [''])]


def terminal_map(decision, language='en', width=72):
    points = [p for p in decision['points'] if p['quality'] is not None and p['speed'] is not None
              and p['speed_basis'] == decision['speed_basis']]
    if len(points) < 2:
        return []
    chart_width = max(24, min(54, width - 12))
    height = 9
    maximum = max((p['speed'] for p in points), default=1) or 1
    grid = [[' ' for _ in range(chart_width)] for _ in range(height)]
    for index, point in enumerate(decision['points'], 1):
        if point not in points:
            continue
        x = round(max(0, point['speed']) / maximum * (chart_width - 1))
        y = height - 1 - round(max(0, min(1, point['quality'])) * (height - 1))
        mark = str(index) if index < 10 else '*'
        grid[y][x] = mark if grid[y][x] == ' ' else '*'
    title = choose(language, 'Native quality (%) vs generation speed (tok/s)', 'Качество Native (%) и скорость генерации (ток/с)')
    lines = [title, '100% ┌' + '─' * chart_width + '┐']
    lines += [(' 50% ' if i == 4 else '     ') + '│' + ''.join(row) + '│' for i, row in enumerate(grid)]
    lines += ['  0% └' + '─' * chart_width + '┘', f'      0{" " * max(1, chart_width-17)}{maximum:.1f} tok/s →',
              choose(language, '* = overlapping points; model IDs below.', '* = наложение точек; номера моделей ниже.')]
    return lines


def terminal_decisions(decision, language='en', width=88):
    t = lambda en, ru: choose(language, en, ru)
    ids = {p['model']: f'M{i}' for i, p in enumerate(decision['points'], 1)}
    lines = [t('TOP 3 PLACES · measured results, not universal winners',
               'ТОП-3 МЕСТА · измерения, а не универсальные победители')]
    if not decision['comparable']:
        lines += [t('! Coverage differs or has failures: descriptive only; no recommendation.',
                    '! Разное покрытие или ошибки: только наблюдения, без рекомендации.')]
    for key, label, metric in (
        ('quality', t('Native quality', 'Качество Native'), lambda p: pct(p['quality'])),
        ('speed', t('Generation speed', 'Скорость генерации'), lambda p: fmt(p['speed'], ' tok/s')),
        ('latency', t('Task time (lower is better)', 'Время задачи (меньше — лучше)'), lambda p: fmt(p['latency'], ' s')),
        ('memory', t('VRAM peak (lower is better)', 'Пик VRAM (меньше — лучше)'), lambda p: fmt(p['vram_mib']/1024, ' GiB')),
    ):
        places = top_places(decision['rankings'][key])
        lines += [label + ': ' + (' | '.join(f"#{p['rank']} {ids[p['model']]} {metric(p)}" for p in places) or '—')]
    lines += [t('Speed basis: ', 'Основа скорости: ') + t('warm runs only', 'только warm-запуски')
              if decision['speed_basis'] == 'warm' else t('Speed: all load states; warm data unavailable.', 'Скорость: все состояния загрузки; warm-данных нет.')]
    for profile in decision['profiles']:
        if profile['id'] not in ('balance', 'custom'):
            continue
        ranked = top_places(profile['ranking'])
        lines += [t('Balanced priorities', 'Баланс приоритетов') + ': ' +
                  (' | '.join(f"#{p['rank']} {ids[p['model']]}" + ('' if p['eligible'] else ' !') for p in ranked) or '—')]
        winner = profile.get('winner')
        lines += [t('Recommendation: ', 'Рекомендация: ') + (ids[winner] if winner else
                  ', '.join(ids[m] for m in profile.get('tied_models', [])) or t('unavailable', 'недоступна')) +
                  f" · {profile['eligible_count']}/{profile['total_count']} " + t('eligible', 'допущено')]
    lines += [t('! Recommendation gate: conservative quality ≥ ', '! Порог рекомендации: консервативное качество ≥ ') +
              pct(decision['gate_threshold']) + t('; task contract ≥ 80%.', '; контракт ≥ 80%.')]
    lines += terminal_map(decision, language, width)
    for point in decision['points']:
        lines += [f"{ids[point['model']]}  {point['model']}"]
        if point['gate_reasons']:
            lines += ['    ! ' + reason_text(point['gate_reasons'], language)]
    lines += [t('Ties share a place. Close scores may be indistinguishable; see uncertainty in HTML.',
                'Равные значения делят место. Близкие результаты могут быть неразличимы; разброс — в HTML.')]
    return wrap_lines(lines, width)


def rolling_test_lines(records, current, language='en', width=88):
    """One small O(n) view of the current test; do not rescore or rank unequal waves."""
    identity = current.get('identity') or {}
    matches = [r for r in records if all(at(r, f'identity.{key}') == identity.get(key)
               for key in ('model', 'backend', 'benchmark'))]
    valid = [r for r in matches if execution_ok(r)]
    quality = values_mean(at(r, 'score.native.value') for r in valid)
    scored = sum(_number(at(r, 'score.native.value')) is not None for r in valid)
    speed = values_mean(at(r, 'primary.eval_rate') for r in valid)
    t = lambda en, ru: choose(language, en, ru)
    line = t('So far on this test (provisional): ', 'Накоплено по этому тесту (предварительно): ')
    count = len(valid)
    runs_label = t('run' if count == 1 else 'runs', 'запуск' if count == 1 else 'запуска')
    line += f"{count} {runs_label}" + f" · Native {pct(quality)} (n={scored}) · {fmt(speed, ' tok/s')}"
    line += t(' · failures ', ' · ошибок ') + str(len(matches) - len(valid))
    return wrap_lines([line], width)


def terminal_model_metrics(rows, language='en', width=88):
    t = lambda en,ru: choose(language,en,ru)
    lines = ['', t('MODEL METRICS · same IDs as the top 3', 'МЕТРИКИ МОДЕЛЕЙ · номера как в топ-3')]
    for index,row in enumerate(rows,1):
        final = row.get('chat_assisted_score') if row.get('chat_assisted_score') is not None else row.get('overall_assisted_score')
        lines += [f"M{index}: Final {pct(final)} · GEN {pct(row.get('native_generation_completion_rate'))} · TASK {pct(row.get('native_task_completion_rate'))} · REC.USED {pct(row.get('overall_recovery_rate'))}",
                  f"    CPU {fmt(row.get('cpu_util_avg'),'%')} · GPU {fmt(row.get('gpu_util_avg'),'%')} · RAM {fmt(row.get('ram_peak_gib'),' GiB')} · VRAM {fmt((_number(row.get('vram_peak_mib'))/1024) if _number(row.get('vram_peak_mib')) is not None else None,' GiB')}"]
        lines += ['    '+t('Lowest test: ', 'Самый низкий тест: ')+str(row.get('worst_test') or '—')+' '+pct(row.get('worst_test_score'))+
                  ' · '+t('critical ', 'замечаний ')+str(int(row.get('critical_failure_count') or 0))+
                  ' · '+t('execution errors ', 'ошибок выполнения ')+str(int(row.get('failed_runs') or 0))]
    lines += [t('CPU/GPU: run means; RAM/VRAM: observed peaks on the whole host. — = unknown.', 'CPU/GPU: средние по запускам; RAM/VRAM: пики всего узла. — = неизвестно.'),
              t('GEN = generation ended; TASK = required format; neither guarantees correctness.', 'GEN = выдача завершена; TASK = обязательный формат; это не гарантия правильности.'),
              t('Use HTML for charts and explanations, or detailed terminal metrics for all tests.', 'Графики и объяснения — в HTML; все тесты — в подробных метриках терминала.')]
    return wrap_lines(lines,width)


def live_progress_line(label, stage, elapsed, tokens, budget, resources, width=100):
    """Width-bounded heartbeat; token budget is not a claimed completion percent."""
    width = max(30, int(width))
    sensors = clean(resources).replace(' | ', ' ')
    if width < 115:
        sensors = re.sub(r'/[\d.]+G', 'G', sensors)
        sensors = re.sub(r'\s*\d+°C', '', sensors)
    phase = clean(stage)[:10]
    rate = tokens / max(.001,elapsed)
    line = f'{phase} {elapsed:.0f}s ≈{rate:.1f} tok/s'
    detail = f' · budget ≈{tokens}/{budget} tok'
    if len(line+detail+' | '+sensors) <= width:
        line += detail
    if sensors:
        line += ' | ' + sensors
    if len(line) > width:
        line = f'{phase[:5]} {elapsed:.0f}s '+sensors.replace('GPU ','G').replace('VRAM ','V').replace('CPU ','C').replace('RAM ','R')
    spare = width-len(line)-3
    if spare>=16:
        line = clean(label)[:spare]+' | '+line
    return line[:width]


TEST_DESCRIPTIONS = {
    'russian_editing': ('Russian editing', 'Редактирование русского текста', 'Clear Russian without changing meaning.', 'Ясный русский текст без изменения смысла.'),
    'dialogue_state': ('Dialogue state', 'Состояние диалога', 'Retain confirmed requirements across turns.', 'Сохранить подтверждённые требования в диалоге.'),
    'groundedness': ('Evidence boundaries', 'Границы доказательств', 'Answer only from provided evidence.', 'Отвечать только по предоставленным данным.'),
    'groundedness_adversarial': ('Untrusted instructions', 'Недоверенные инструкции', 'Do not follow instructions hidden inside a source.', 'Не исполнять инструкции, спрятанные внутри источника.'),
    'instruction': ('Instruction following', 'Следование инструкции', 'Follow explicit content and output-format constraints.', 'Выполнить ограничения содержания и формата.'),
    'ru_context_corrections': ('Context corrections', 'Исправления контекста', 'Prefer the latest user-confirmed facts to obsolete or invented claims.', 'Отличить последние факты пользователя от устаревших и выдуманных утверждений.'),
    'ru_causality_precision': ('Causal caution', 'Причинная осторожность', 'Separate an observed change from a proven causal effect.', 'Не выдавать наблюдаемое изменение за доказанную причинную связь.'),
    'ru_semantic_negation': ('Meaning and negation', 'Смысл и отрицания', 'Preserve negation and limits of evidence while rewriting.', 'Сохранить отрицания и ограничения выводов при переформулировке.'),
    'ru_business_tone': ('Business tone', 'Деловой тон', 'Write a calm, firm message while keeping all required facts.', 'Написать спокойное и твёрдое сообщение, сохранив обязательные факты.'),
    'ru_debureaucratize': ('Plain business language', 'Простой деловой язык', 'Remove bureaucratic phrasing without inventing goals or advice.', 'Убрать канцелярит без выдуманных целей и советов.'),
    'logic_constraints': ('Logical constraints', 'Логические ограничения', 'Satisfy multiple formal conditions at the same time.', 'Одновременно выполнить несколько формальных условий.'),
    'simpson': ('Aggregation and causality', 'Агрегация и причинность', 'Interpret subgroup and aggregate results without causal overclaiming.', 'Понять различия групповых и общих показателей без усиления выводов.'),
}


def test_copy(name, language):
    entry = TEST_DESCRIPTIONS.get(name)
    if entry:
        return choose(language, entry[0], entry[1]), choose(language, entry[2], entry[3])
    return clean(name), choose(language, 'Selected test. Its recorded scoring contract defines the result; a missing score requires manual review.',
                              'Выбранный тест. Результат определяется его записанным контрактом; при отсутствии балла нужна ручная оценка.')


def _bar(value, maximum=1, color='#FF3C52'):
    number = _number(value)
    if number is None:
        return '<div class="metric-track unknown"></div>'
    width = min(100, max(0, number / maximum * 100)) if maximum > 0 else 0
    return f'<div class="metric-track"><i class="metric-bar" style="width:{width:.2f}%;background:{color}"></i></div>'


def _scatter(decision, ids, colors, language, field='speed'):
    t = lambda en, ru: choose(language, en, ru)
    points = [p for p in decision['points'] if p['quality'] is not None and p.get(field) is not None
              and (field != 'speed' or p['speed_basis'] == decision['speed_basis'])]
    if not points:
        return '<p class="empty">' + t('Not enough paired measurements.', 'Недостаточно парных измерений.') + '</p>'
    xmax = max((p[field] for p in points), default=1)
    xmax = math.ceil(max(xmax, 1) / 10) * 10
    unit = 'tok/s' if field == 'speed' else 's'
    label = t('Generation speed → faster', 'Скорость генерации → быстрее') if field == 'speed' else t('Task time → slower', 'Время задачи → медленнее')
    out = ['<svg class="scatter" viewBox="0 0 720 380" role="img" aria-label="' + h(label) + '">',
           '<title>' + h(t('Native quality and ', 'Качество Native и ') + label) + '</title>']
    for step in range(6):
        x = 66 + step * 122
        y = 310 - step * 54
        out += [f'<path class="gridline" d="M66 {y}H676 M{x} 40V310"/>',
                f'<text x="54" y="{y+4}" text-anchor="end">{step*20}%</text>',
                f'<text x="{x}" y="335" text-anchor="middle">{xmax*step/5:g}</text>']
    out += ['<text x="66" y="22">Native %</text>', f'<text x="366" y="370" text-anchor="middle">{h(label)} ({unit})</text>']
    used = Counter()
    for p in points:
        x = 66 + max(0, p[field]) / xmax * 610
        y = 310 - min(1, max(0, p['quality'])) * 270
        cell = (round(x / 22), round(y / 22))
        offset = used[cell]
        used[cell] += 1
        dx = min(30, offset * 13)
        dy = -min(30, offset * 13)
        out += [f'<g class="scatter-point"><title>{h(p["model"])}: Native {pct(p["quality"])}; {fmt(p[field], " " + unit)}</title>',
                f'<path d="M{x:.1f} {y:.1f}l{dx} {dy}" stroke="{colors[p["model"]]}"/>',
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{colors[p["model"]]}" stroke="#fff"/>',
                f'<text x="{x+dx+9:.1f}" y="{y+dy-11:.1f}" class="point-label">{ids[p["model"]]}</text></g>']
    return ''.join(out) + '</svg>'


def _comparison_overview(rows, points, badge, colors, language):
    """Compact visual scorecards using existing, non-combined measurements."""
    t = lambda en, ru: choose(language, en, ru)
    speeds = [_number(point.get('speed')) for point in points]
    speed_max = max([value for value in speeds if value is not None] + [1])
    out = [
        '<section id="compare"><div class="eyebrow">02 / ' + t('AT A GLANCE', 'СРАЗУ О ГЛАВНОМ') + '</div>',
        '<h2>' + t('Quality, contract and speed', 'Качество, контракт и скорость') + '</h2>',
        '<p class="lead">' + t(
            'One card per model. Quality and task contract use their direct percentages; speed is only scaled visually within this run and keeps its measured tok/s value.',
            'Одна карточка на модель. Качество и выполнение контракта показаны в процентах; скорость масштабирована только для наглядности внутри этого прогона и сохраняет измеренное значение ток/с.'
        ) + '</p><div class="comparison-grid">'
    ]
    for row, point in zip(rows, points):
        quality = point.get('quality')
        task = point.get('reliability')
        speed = _number(point.get('speed'))
        latency = _number(point.get('latency'))
        low = _number(row.get('chat_native_min'))
        mean = _number(row.get('chat_native_mean'))
        high = _number(row.get('chat_native_max'))
        if low is None:
            low = quality
        if mean is None:
            mean = quality
        if high is None:
            high = quality
        stability = '<div class="stability-track unknown"></div><small>—</small>'
        if None not in (low, mean, high) and low <= mean <= high:
            stability = (
                '<div class="stability-track"><i class="stability-range" style="left:{:.2f}%;width:{:.2f}%;background:{}"></i>'
                '<i class="stability-dot" style="left:{:.2f}%"></i></div><small>{} – {} · mean {}</small>'
            ).format(low * 100, (high - low) * 100, colors[point['model']], mean * 100, pct(low), pct(high), pct(mean))
        out += [
            '<article class="comparison-card"><h3>' + badge(point['model']) + ' ' + h(point['model']) + '</h3>',
            '<div class="bar-label"><span>' + t('Native quality', 'Качество Native') + '</span><strong>' + pct(quality) + '</strong></div>' + _bar(quality, color=colors[point['model']]),
            '<div class="bar-label"><span>' + t('Task contract', 'Контракт задачи') + '</span><strong>' + pct(task) + '</strong></div>' + _bar(task, color='#42D9AD'),
            '<div class="bar-label"><span>' + t('Generation speed', 'Скорость генерации') + '</span><strong>' + fmt(speed, ' tok/s') + '</strong></div>' + _bar(speed, speed_max, '#51C8FF'),
            '<p class="micro">' + t('Average task time: ', 'Среднее время задачи: ') + fmt(latency, ' s') + '</p>',
            '<h4>' + t('Seed stability', 'Стабильность по seed') + '</h4>' + stability,
            '</article>'
        ]
    return ''.join(out) + '</div><p class="micro">' + t(
        'The stability band is the observed lowest-to-highest Native score across seeds; the white mark is the mean. It is not a pass/fail scale.',
        'Полоса стабильности — наблюдаемый диапазон Native-балла по seed; белая отметка — среднее. Это не шкала успеха/ошибки.'
    ) + '</p></section>'


def render_report(model_rows, detail_rows, *, version='', language='en', generated='', evidence_summary=None, run_scope=None, bilingual=None):
    """Render an autonomous HTML document from existing summaries only."""
    language = 'ru' if language == 'ru' else 'en'
    t = lambda en, ru: choose(language, en, ru)
    rows, details = list(model_rows), list(detail_rows)
    decision = build_decision_support(rows)
    points = decision['points']
    ids = {p['model']: f'M{i}' for i, p in enumerate(points, 1)}
    colors = {p['model']: COLORS[i % len(COLORS)] for i, p in enumerate(points)}
    badge = lambda model: f'<b class="model-id" style="--model:{colors[model]}">{ids[model]}</b>'
    title = t('Choose with evidence.', 'Выбирайте по результатам.')
    body = []
    logo_path = Path(__file__).resolve().parents[2] / 'Assets/Brand/bull-mark-red.png'
    logo = ''
    if logo_path.is_file() and logo_path.stat().st_size < 2_000_000:
        logo = '<img alt="BULL" class="brand-mark" src="data:image/png;base64,' + base64.b64encode(logo_path.read_bytes()).decode('ascii') + '">'
    counts = sum(int(r.get('observed_runs') or 0) for r in rows)
    failed = sum(int(r.get('failed_runs') or 0) for r in rows)
    body += [f'<header>{logo}<div class="eyebrow">BULL / RESULTS LAB · {h(version)}</div><h1>{title}</h1>',
             '<p>' + t('Quality. Speed. Resources. Find the trade-off that fits your work.', 'Качество. Скорость. Ресурсы. Найдите сочетание, которое подходит вашим задачам.') + '</p>',
             '<div class="kpis">' + ''.join(f'<div><strong>{value}</strong><span>{label}</span></div>' for value, label in
                 ((len(rows), t('models', 'моделей')), (len({r.get('benchmark') for r in details}), t('tests', 'тестов')),
                  (counts, t('recorded runs', 'сохранённых запусков')), (failed, t('execution errors', 'ошибок выполнения')))) + '</div></header>']
    if run_scope:
        body += ['<aside class="notice"><strong>' + h(run_scope.get('identity', '')) + '</strong> · ' +
                 h(run_scope.get('title', '')) + '<br>' +
                 h(run_scope.get('selected_cases', '')) + '/' + h(run_scope.get('total_cases', '')) + ' · ' +
                 t('Explicit test selection', 'Явный выбор тестов') + '<br>' +
                 (t('SUBSET — not a full-pack benchmark result.', 'ЧАСТЬ НАБОРА — не оценка полного набора.')
                  if run_scope.get('coverage') == 'subset' else t('Full pack coverage', 'Полное покрытие набора')) + '</aside>']
        body += ['<details><summary>' + t('Pack provenance', 'Происхождение набора') + '</summary><p>' +
                 t('Manifest SHA-256: ', 'Manifest SHA-256: ') + h(run_scope.get('manifest_sha256', '')) +
                 '<br>Compiled SHA-256: ' + h(run_scope.get('compiled_sha256', '')) + '</p><p>' +
                 t('These checksums identify content, not author authenticity or reference correctness.',
                   'Хеши определяют содержимое, но не подтверждают автора или правильность эталонов.') + '</p></details>']
    nav = [('rankings', t('Top 3', 'Топ-3')), ('compare', t('At a glance', 'Главное')),
           ('charts', t('Quality & speed', 'Качество и скорость')),
           ('resources', t('Resources', 'Ресурсы')), ('tests', t('Tests', 'Тесты')),
           ('settings', t('Settings', 'Параметры')), ('details', t('Full data', 'Все данные'))]
    if bilingual:nav=[('bilingual',t('RU/EN comparison','Сравнение RU/EN'))]
    body += ['<nav aria-label="Report">' + ''.join(f'<a href="#{key}">{label}</a>' for key, label in nav) + '</nav>']
    if bilingual:
        body += [_bilingual_section(bilingual,language),'<details><summary>'+t(
            'Supplemental aggregate metrics — not a bilingual ranking',
            'Дополнительные общие метрики — не билингвальный рейтинг')+'</summary>']
    if not decision['comparable']:
        body += ['<aside class="notice">' + t('Unequal test/seed coverage, errors or a parameter sweep: ranks describe recorded results only. Recommendations are withheld.',
                  'Разное покрытие тестов/seeds, ошибки или перебор настроек: места описывают только записанные результаты. Рекомендации не выдаются.') + '</aside>']
    body += ['<section id="rankings"><div class="eyebrow">01 / ' + t('THE SHORTLIST', 'КОРОТКИЙ СПИСОК') + '</div><h2>' + t('Top 3 places', 'Топ-3 места') + '</h2><p class="lead">' +
             t('Measured places include every model with data. They are not the same as a gated recommendation. Equal values share a place.',
               'Измеренные места включают все модели с данными. Это не то же самое, что рекомендация с порогом допуска. Равные значения делят место.') + '</p><div class="rank-grid">']
    rank_specs = [('quality', t('Native quality', 'Качество Native'), lambda p: pct(p['quality']), t('Higher is better', 'Выше — лучше')),
                  ('speed', t('Generation speed', 'Скорость генерации'), lambda p: fmt(p['speed'], ' tok/s'), t('Warm only' if decision['speed_basis']=='warm' else 'All load states', 'Только warm' if decision['speed_basis']=='warm' else 'Все состояния загрузки')),
                  ('memory', t('VRAM peak', 'Пик VRAM'), lambda p: fmt(p['vram_mib']/1024, ' GiB'), t('Lower is better; unknown excluded', 'Меньше — лучше; неизвестные исключены')),
                  ('balance', t('Balance of priorities', 'Баланс приоритетов'), lambda p: 'Native '+pct(p['quality']), t('Weighted ordering; not a quality score', 'Взвешенный порядок; не балл качества'))]
    ranked_profiles = {p['id']: p for p in decision['profiles']}
    for key, label, metric, note in rank_specs:
        body += [f'<article class="rank-card"><h3>{label}</h3><p class="micro">{note}</p><ol>']
        ranked = ranked_profiles['balance']['ranking'] if key=='balance' else decision['rankings'][key]
        for p in top_places(ranked):
            excluded = ('<small class="warning">'+h(reason_text(p['exclusions'],language))+'</small>') if key=='balance' and not p['eligible'] else ''
            body += [f'<li><span class="place">#{p["rank"]}</span><div>{badge(p["model"])} <span class="model-name">{h(p["model"])}</span><strong class="rank-value">{metric(p)}</strong>{excluded}</div></li>']
        if not top_places(ranked):
            body += ['<li class="empty">' + t('No comparable measurements.', 'Нет сопоставимых измерений.') + '</li>']
        body += ['</ol></article>']
    body += ['</div><h3>' + t('Which model fits your priorities?', 'Какая модель лучше для задачи') + '</h3><p>' +
             t('A recommendation uses conservative quality (lower 95% CI when available), task completion and normalized metrics. This is a choice aid, not a new quality score.',
               'Рекомендация использует консервативное качество (нижнюю границу 95% интервала, если она есть), выполнение контракта и нормированные метрики. Это подсказка выбора, а не новый балл качества.') + '</p>',
             '<p class="notice">' + t('Speed / Balance / Low memory gate: quality ≥ ', 'Порог для Скорости / Баланса / Памяти: качество ≥ ') + pct(decision['gate_threshold']) +
             t(' (at least 60%, within 10 pp of the best conservative value); task completion ≥ 80% when known. Unknown required metrics exclude a candidate.',
               ' (не ниже 60% и не далее 10 п.п. от лучшего консервативного значения); контракт ≥ 80%, когда известен. Без обязательных метрик модель не допускается.') + '</p><div class="decision-grid">']
    profile_labels = {'quality': t('Quality', 'Качество'), 'speed': t('Speed with quality gate', 'Скорость с порогом качества'),
                      'balance': t('Balance', 'Баланс'), 'low_memory': t('Low memory', 'Мало памяти')}
    weight_labels = {'quality': t('quality', 'качество'), 'speed': t('speed', 'скорость'),
                     'reliability': t('contract', 'контракт'), 'memory': t('memory', 'память')}
    for profile in decision['profiles']:
        eligible = profile['eligible_count']
        names = [profile['winner']] if profile['winner'] else profile.get('tied_models', [])
        winner = '<br>'.join(badge(n) + ' ' + h(n) for n in names) or t('Not enough evidence', 'Недостаточно данных')
        body += [f'<article class="decision-card"><h3>{profile_labels[profile["id"]]}</h3><p class="recommendation">{winner}</p>',
                 '<p class="micro">' + f'{eligible}/{len(points)} ' + t('eligible', 'допущено') + '</p>']
        if eligible == 1:
            body += ['<p class="warning">' + t('Only one qualified candidate. This does not mean it is the fastest or uses the least memory.', 'Только один кандидат прошёл порог. Это не означает, что он самый быстрый или требует меньше всего памяти.') + '</p>']
        body += ['<details><summary>' + t('Places & reasons', 'Места и причины') + '</summary><ol>']
        for p in profile['ranking']:
            note = t('eligible', 'допущена') if p['eligible'] else reason_text(p['exclusions'], language)
            body += [f'<li>#{p.get("rank") or "—"} {badge(p["model"])} {h(p["model"])}<small>{h(note)}</small></li>']
        body += ['</ol><p class="micro">' + ' · '.join(f'{weight_labels[k]} {v*100:.0f}%' for k,v in profile['weights'].items() if v) + '</p></details></article>']
    body += ['</div></section>']

    body += [_comparison_overview(rows, points, badge, colors, language)]

    body += ['<section id="charts"><div class="eyebrow">03 / ' + t('THE TRADE-OFF', 'СОЧЕТАНИЕ МЕТРИК') + '</div><h2>' + t('Quality and speed', 'Качество и скорость') + '</h2>',
             '<p class="lead">' + t('True numeric axes, not relative quadrants. The top-right combines higher measured quality and generation throughput. Point labels identify models below.',
             'Числовые оси, а не относительные квадранты. Вверху справа — выше измеренное качество и скорость генерации. Номера точек расшифрованы ниже.') + '</p>',
             _scatter(decision, ids, colors, language), '<div class="legend">']
    for p in points:
        body += [f'<span>{badge(p["model"])} {h(p["model"])}</span>']
    body += ['</div><h3>' + t('Quality and task time', 'Качество и время задачи') + '</h3><p class="micro">' +
             t('Pipeline wall time includes generation and allowed recovery. Lower is better; output lengths differ, so tok/s is not task latency.',
               'Полное время включает генерацию и разрешённый recovery. Меньше — лучше. Длина ответов различается, поэтому ток/с не равны времени задачи.') + '</p>',
             _scatter(decision, ids, colors, language, 'latency'),
             '<h3>' + t('Quality scales', 'Шкалы качества') + '</h3><div class="quality-grid">']
    for row, p in zip(rows, points):
        native = p['quality']
        final = row.get('chat_assisted_score') if row.get('chat_assisted_score') is not None else row.get('overall_assisted_score')
        body += [f'<article class="model-card"><h3>{badge(p["model"])} {h(p["model"])}</h3>',
                 '<div class="bar-label"><span>Native model quality</span><strong>' + pct(native) + '</strong></div>' + _bar(native),
                 '<div class="bar-label"><span>Final system quality</span><strong>' + pct(final) + '</strong></div>' + _bar(final, color='#51C8FF'),
                 '<p>' + t('Task contract ', 'Контракт задачи ') + pct(p['reliability']) + ' · ' + t('Recovery used ', 'Recovery использован ') + pct(row.get('overall_recovery_rate')) + '</p>',
                 '<p class="micro">' + t('Seed SD ', 'SD по seeds ') + fmt((_number(row.get('chat_native_sd')) * 100) if _number(row.get('chat_native_sd')) is not None else None, ' pp') +
                 ' · 95% CI ' + pct(row.get('chat_native_ci95_low')) + '–' + pct(row.get('chat_native_ci95_high')) + '</p></article>']
    body += ['</div><p class="micro">' + t('Native = first answer before recovery. Final = the system result after allowed recovery. Observed ranks are not proof of statistical superiority.',
               'Native — первый ответ до recovery. Final — итог системы после разрешённого recovery. Наблюдаемые места не доказывают статистическое превосходство.') + '</p></section>']

    body += [_uncertainty_plots(details, language)]

    body += ['<section id="resources"><div class="eyebrow">04 / ' + t('THE COST', 'РЕСУРСЫ') + '</div><h2>' + t('Resources used', 'Затраты ресурсов') + '</h2><p class="lead">' +
             t('Host-level sensors, not per-model allocation. CPU/GPU are means of recorded run averages; RAM/VRAM are observed peaks. Background activity is included. Missing sensors stay unknown.',
               'Датчики всего узла, а не выделение ресурсов одной модели. CPU/GPU — средние по измеренным запускам; RAM/VRAM — наблюдаемые пики. Фоновые процессы включены. Нет датчика — нет значения.') + '</p><div class="resource-grid">']
    for key, label, unit in (('cpu_util_avg', 'CPU', '%'), ('gpu_util_avg', 'GPU', '%'), ('ram_peak_gib', 'RAM', ' GiB'), ('vram_peak_mib', 'VRAM', ' GiB')):
        vals = [(row, p, _number(row.get(key))) for row, p in zip(rows, points)]
        vals = [(row, p, value/1024 if key=='vram_peak_mib' and value is not None else value) for row,p,value in vals]
        maximum = 100 if unit == '%' else max([value for _,_,value in vals if value is not None] + [1])
        body += [f'<article class="resource-card"><h3>{label} ' + t('mean' if unit=='%' else 'peak', 'среднее' if unit=='%' else 'пик') + '</h3>']
        for row, p, value in vals:
            body += [f'<div class="bar-label">{badge(p["model"])}<strong>{fmt(value, unit)}</strong></div>' + _bar(value, maximum, colors[p['model']])]
        body += ['</article>']
    body += ['</div><p class="micro">' + t('Each model’s sensor coverage (measured / successful runs): ', 'Покрытие датчиков (измерено / успешных запусков): ') +
             '; '.join(f'{ids[p["model"]]} CPU {r.get("cpu_sensor_runs",0)}/{r.get("successful_runs",0)}, GPU {r.get("gpu_sensor_runs",0)}/{r.get("successful_runs",0)}, RAM {r.get("ram_sensor_runs",0)}/{r.get("successful_runs",0)}' for r,p in zip(rows,points)) + '</p></section>']

    body += ['<section id="tests"><div class="eyebrow">05 / ' + t('WHERE MODELS DIFFER', 'РАЗЛИЧИЯ ПО ЗАДАЧАМ') + '</div><h2>' + t('Results by test', 'Результаты по тестам') + '</h2><p class="lead">' +
             t('Cell = existing Native mean for that test. A dash means no automatic score. Color is a visual scale, not a pass/fail boundary. Multiple configurations stay separate in Full data.',
               'Ячейка — готовый средний Native-балл теста. Прочерк — нет автоматического балла. Цвет — шкала, а не порог успеха. Разные конфигурации сохранены отдельно в полных данных.') + '</p><div class="table-wrap"><table class="heatmap"><thead><tr><th>' + t('Test / purpose', 'Тест / назначение') + '</th>' + ''.join('<th>'+badge(p['model'])+'</th>' for p in points) + '</tr></thead><tbody>']
    for test in sorted({str(row.get('benchmark') or '?') for row in details}):
        name, description = test_copy(test, language)
        body += [f'<tr><th>{h(name)}<small>{h(description)}</small><code>{h(test)}</code></th>']
        for p in points:
            matches = [r for r in details if str(r.get('benchmark')) == test and str(r.get('model')) == p['model_id'] and str(r.get('backend') or '') == (p['backend'] or '')]
            scores = [_number(r.get('native_model_score', r.get('native_score_avg'))) for r in matches]
            if len(scores) == 1 and scores[0] is not None:
                score = scores[0]
                body += [f'<td><span class="heat" style="--heat:{max(0,min(100,score*100)):.1f}%">{pct(score)}</span><small>n={int(matches[0].get("runs_scorable") or matches[0].get("native_score_valid_runs") or 0)}</small></td>']
            else:
                body += ['<td>' + (t('multiple', 'несколько') if len(matches)>1 else '—') + '</td>']
        body += ['</tr>']
    body += ['</tbody></table></div><p class="micro">' + t('Automatic checks do not replace expert review. Plain-text user prompts without a scorer have no quality rank.',
                'Автоматические проверки не заменяют эксперта. Пользовательский текст без scorer не получает место по качеству.') + '</p></section>']
    body += [_category_table(rows, points, badge, language), _language_tracks_table(rows, points, badge, language)]

    body += ['<section id="settings"><div class="eyebrow">06 / ' + t('REPRODUCE', 'ВОСПРОИЗВЕДЕНИЕ') + '</div><h2>' + t('Recorded model settings', 'Записанные параметры моделей') + '</h2><p class="lead">' +
             t('Values are from the run, not guessed from a model name. Multiple values mean settings varied. Unknown inherited defaults remain unknown.',
               'Значения взяты из прогона, а не угаданы по имени модели. Несколько значений означают изменение настроек. Неизвестные унаследованные значения не подставляются.') + '</p><div class="quality-grid">']
    for row, p in zip(rows, points):
        body += [f'<article class="model-card"><h3>{badge(p["model"])} {h(p["model"])}</h3><dl>']
        sources = [s for s in row.get('sampling_sources', []) if s in SOURCE_NAMES]
        source_labels = {'benchmark_override': t('BULL preset', 'Пресет BULL'), 'model_profile': t('Ollama profile', 'Профиль Ollama'), 'per_model': t('Per-model overrides', 'Отдельно для модели')}
        entries = [(t('Sampling source', 'Источник генерации'), ', '.join(source_labels.get(s,s) for s in sources) or '—'),
                   (t('Seeds', 'Seeds'), ', '.join(fmt(v, digits=0) for v in row.get('seeds_observed',[])) or '—')]
        param_labels = {'ctx': t('Context capacity (tokens)', 'Окно контекста (токены)'), 'threads': t('CPU threads', 'Потоки CPU'),
                        'primary_predict': t('Output token limit', 'Лимит токенов ответа'), 'temperature': t('Temperature (randomness)', 'Temperature (случайность)'),
                        'top_p': 'top_p', 'top_k': 'top_k', 'min_p': 'min_p', 'repeat_penalty': t('Repeat penalty', 'Штраф за повторы'), 'think': t('Reasoning enabled', 'Рассуждения включены')}
        for key in PARAMETERS:
            raw = (row.get('report_settings') or {}).get(key, [])
            safe = [str(v).lower() if isinstance(v, bool) and key=='think' else f'{float(v):.15g}'
                    for v in raw if (isinstance(v,bool) and key=='think') or _number(v) is not None]
            entries.append((param_labels[key], ', '.join(safe[:12]) + (' …' if len(safe)>12 else '') if safe else '—'))
        for label, value in entries:
            body += [f'<dt>{label}</dt><dd>{h(value)}</dd>']
        body += ['</dl><details><summary>' + t('Parameter provenance', 'Происхождение параметров') + '</summary><p class="micro">' +
                 t('Sent = explicitly passed to the API. Inherited values are not proof of backend defaults.', 'Передан = явно отправлен в API. Унаследованные значения не доказывают неизвестные значения backend.') + '</p><dl>']
        for key in PARAMETERS:
            for entry in (row.get('report_parameter_sources') or {}).get(key, []):
                source = entry.get('source') if entry.get('source') in SOURCE_NAMES else 'unknown'
                value = str(entry['value']).lower() if key=='think' and isinstance(entry.get('value'),bool) else fmt(entry.get('value'))
                sent = t('sent', 'передан') if entry.get('sent') is True else t('inherited', 'унаследован') if entry.get('sent') is False else '—'
                body += ['<dt>'+param_labels[key]+'</dt><dd>'+h(value+' · '+source+' · '+sent)+'</dd>']
        body += ['</dl></details><p class="micro">' + t('Load state counts: ', 'Состояния загрузки: ') + ' · '.join(f'{key} {int((row.get("load_counts") or {}).get(key,0))}' for key in ('warm','cold','unknown')) + '</p></article>']
    body += ['</div></section>']

    body += ['<section id="details"><h2>' + t('Full data', 'Все данные') + '</h2><details open><summary>' + t('Summary table', 'Сводная таблица') + '</summary><div class="table-wrap"><table><thead><tr>' +
             ''.join('<th>'+s+'</th>' for s in (t('Model', 'Модель'), 'Native', 'Final', 'TASK', 'tok/s', t('Time, s', 'Время, с'), 'VRAM GiB', t('Coverage', 'Покрытие'))) + '</tr></thead><tbody>']
    for row,p in zip(rows,points):
        coverage = t('Selected tests', 'Выбранные тесты') if not row.get('chat_available_tests') else f"CHAT {row.get('chat_available_tests')}/{row.get('chat_required_tests')}"
        body += ['<tr><th>'+badge(p['model'])+' '+h(p['model'])+'</th>' + ''.join('<td>'+value+'</td>' for value in
                 (pct(p['quality']), pct(row.get('chat_assisted_score') if row.get('chat_assisted_score') is not None else row.get('overall_assisted_score')),
                  pct(p['reliability']), fmt(p['speed']), fmt(p['latency']), fmt(p['vram_mib']/1024 if p['vram_mib'] is not None else None), h(coverage))) + '</tr>']
    body += ['</tbody></table></div></details><details><summary>' + t('Per-test metrics & uncertainty', 'Метрики и разброс по тестам') + '</summary><p>95% confidence intervals · Latency distributions</p><div class="table-wrap"><table><thead><tr>' +
             ''.join('<th>'+s+'</th>' for s in (t('Test', 'Тест'), t('Model', 'Модель'), 'Native', 'Final', '95% CI', 'SD', 'tok/s', 'Time min / mean / max, s', 'TASK', t('Worst seed', 'Худший seed'))) + '</tr></thead><tbody>']
    for row in details:
        native = row.get('native_model_score', row.get('native_score_avg'))
        cells = (h(row.get('benchmark','?')), h(row.get('model','?')), pct(native), pct(row.get('assisted_final_score',row.get('final_score_avg'))),
                 pct(row.get('native_score_ci95_low'))+'–'+pct(row.get('native_score_ci95_high')), fmt(_number(row.get('native_score_sd'))*100 if _number(row.get('native_score_sd')) is not None else None, ' pp'),
                 fmt(row.get('primary_eval_warm_avg')), ' / '.join(fmt(row.get('pipeline_wall_'+s)) for s in ('min','avg','max')),
                 pct(row.get('native_task_completion_rate')), fmt(row.get('native_score_worst_seed'), digits=0))
        body += ['<tr>' + ''.join('<td>'+v+'</td>' for v in cells) + '</tr>']
    body += ['</tbody></table></div></details>', _context_curves(details, language), _failure_details(rows, points, badge, language), '</section>',
             '<section class="notice"><h2>' + t('How to read this report', 'Как читать отчёт') + '</h2><ul>']
    for en, ru in (
        ('Native quality measures the first answer; Final system quality measures the allowed assisted pipeline. Never combine them into one quality score.', 'Native оценивает первый ответ, Final — систему после разрешённой помощи. Их нельзя смешивать в один балл.'),
        ('TASK means mandatory structure/schema was satisfied. It does not guarantee a correct or useful answer. A technical execution error is separate.', 'TASK означает соблюдение обязательной структуры/схемы. Это не гарантия правильного или полезного ответа. Техническая ошибка учитывается отдельно.'),
        ('Warm depends on measured load duration, not seed order. Generation throughput and full task time answer different questions.', 'Warm определяется измеренной загрузкой, а не номером seed. Скорость генерации и полное время задачи отвечают на разные вопросы.'),
        ('SD describes variability. A 95% interval needs repeated comparable observations. Overlapping intervals do not justify a certain winner.', 'SD показывает разброс. Для 95% интервала нужны повторные сопоставимые наблюдения. Пересекающиеся интервалы не дают оснований для уверенного победителя.'),
        ('HTML contains metrics only, no prompts or raw answers. Model and test labels may still be sensitive; review before sharing.', 'HTML содержит метрики, но не промпты и ответы. Имена моделей и тестов могут быть чувствительными — просмотрите их перед отправкой.'),
    ):
        body += ['<li>'+t(en,ru)+'</li>']
    body += ['</ul></section>'+('</details>' if bilingual else '')+'<footer>BULL — Benchmarking &amp; Usage of Local Language Models · '+h(generated)+'<br>'+t('Offline report · no JavaScript, CDN or external requests', 'Автономный отчёт · без JavaScript, CDN и внешних запросов')+'</footer>']
    return '<!doctype html>\n<html lang="'+language+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BULL · Results</title><style>'+STYLE+'</style></head><body><main>'+''.join(body)+'</main></body></html>'


def _bilingual_section(rows,language):
    t=lambda en,ru:choose(language,en,ru)
    out=['<section id="bilingual"><div class="eyebrow">BULL / LANGUAGE COMPARISON</div><h2>'+t(
        'RU and EN: separate evidence','RU и EN: отдельные результаты')+'</h2><p class="lead">'+t(
        'No combined language winner. Scores reflect this pack’s deterministic checks, not general language competence. JSON compliance is not a semantic evaluation.',
        'Общего победителя по языкам нет. Баллы отражают автоматические критерии этого набора, а не общую языковую компетентность. Правильный JSON не доказывает качество смысла.')+'</p>']
    if any(row.get('legacy_language_scorer') for row in rows):
        out+=['<aside class="notice">'+t(
            'Historical scorer v1: foreign-script insertions could pass. Stored results are shown unchanged; use pack 1.0.1 for the corrected checks.',
            'Исторический оценщик v1 мог пропускать вставки на другом языке. Сохранённые баллы не изменены; исправленная проверка доступна в наборе 1.0.1.')+'</aside>']
    headings=(t('Track','Трек'),t('Runs / errors','Запуски / ошибки'),t('Native checks','Критерии Native'),
              t('Correct language','Нужный язык'),t('No switching','Без переключений'),
              t('Native time, s','Время Native, с'),'warm tok/s',t('Seed range','Диапазон seed'))
    for row in rows:
        out+=['<article class="model-card"><h3>'+h(row['model'])+'</h3><div class="table-wrap"><table><thead><tr>'+''.join('<th>'+h(s)+'</th>' for s in headings)+'</tr></thead><tbody>']
        for track in ('ru','en'):
            values=row['tracks'][track]
            cells=(track.upper(),str(values['valid'])+'/'+str(values['observed'])+' · '+str(values['errors']),
                   pct(values['score'])+' (n='+str(values['scored'])+')',
                   pct(values['language_ok'])+' (n='+str(values['language_checked'])+')',pct(values['purity_ok']),
                   fmt(values['native_seconds']),fmt(values['warm_tok_s'])+' (n='+str(values['warm_samples'])+')',
                   pct(values['seed_min'])+'–'+pct(values['seed_max'])+' (n='+str(values['seeds'])+')')
            out+=['<tr>'+''.join('<td>'+h(cell)+'</td>' for cell in cells)+'</tr>']
        out+=['</tbody></table></div><p><strong>'+t('Matched RU/EN pairs: ','Сопоставленные пары RU/EN: ')+str(row['matched_pairs'])+'</strong> · '+t('ambiguous: ','неоднозначных: ')+str(row['ambiguous_pairs'])+'</p><p>'+t(
            'Paired Native difference RU − EN: ','Парная разница Native RU − EN: ')+fmt(
                row['score_delta']*100 if row['score_delta'] is not None else None,' pp')+' (n='+str(row['score_pairs'])+') · '+t(
            'Native time difference RU − EN: ','Разница времени Native RU − EN: ')+fmt(row['native_seconds_delta'],' s')+'</p><p>'+t(
            'All checks pass: both / RU only / EN only / neither: ',
            'Все критерии выполнены: оба / только RU / только EN / ни один: ')+
            ' / '.join(str(row[key]) for key in ('both_pass','ru_only_pass','en_only_pass','neither_pass'))+'</p></article>']
    out+=['<p class="micro">'+t(
        'Pairs match model digest, pack/scorer version, seed/run and effective configuration. Ambiguous attempts and unmatched rows are excluded from paired differences. Time and quality are model-native only; recovery is separate below. tok/s is tokenizer-dependent. Seed ranges are descriptive, not confidence intervals.',
        'Пары сопоставлены по модели/digest, версии набора/оценщика, seed/run и параметрам. Неоднозначные попытки и строки без пары исключены из парных разностей. Время и качество здесь только model-native; recovery показан отдельно ниже. tok/s зависит от токенизатора. Диапазон seed описательный, не доверительный интервал.')+'</p></section>']
    return ''.join(out)


def _uncertainty_plots(details, language):
    t = lambda en, ru: choose(language, en, ru)
    out = ['<section><details><summary>' + t('Uncertainty and latency distributions', 'Неопределённость и разброс времени') + '</summary><p>' +
           t('Native: dot = mean, band = 95% confidence interval. Time: dot = mean, band = observed minimum–maximum, not a confidence interval. Missing intervals stay empty.',
             'Native: точка — среднее, полоса — 95% доверительный интервал. Время: точка — среднее, полоса — наблюдаемый минимум–максимум, а не доверительный интервал. Нет интервала — нет полосы.') + '</p>']
    latency_max = max([_number(r.get('pipeline_wall_max')) or 0 for r in details] + [1])
    for kind, heading, maximum in (('quality', t('Native · 0–100%', 'Native · 0–100%'), 1),
                                   ('time', t('Task time · seconds', 'Время задачи · секунды'), latency_max)):
        out += ['<h3>'+heading+'</h3>']
        for r in details:
            if kind=='quality':
                keys = ('native_score_ci95_low', 'native_score_avg', 'native_score_ci95_high')
            else:
                keys = ('pipeline_wall_min', 'pipeline_wall_avg', 'pipeline_wall_max')
            low,mean,high = (_number(r.get(k)) for k in keys)
            chart = '<div class="ci-track unknown"></div>'
            if low is not None and high is not None and mean is not None and low<=mean<=high:
                left,dot,right = (max(0,min(100,v/maximum*100)) for v in (low,mean,high))
                chart = f'<div class="ci-track"><i class="ci-range" style="left:{left:.2f}%;width:{right-left:.2f}%"></i><i class="ci-dot" style="left:{dot:.2f}%"></i></div>'
            number = pct if kind=='quality' else lambda v: fmt(v,' s')
            out += ['<div class="ci-row"><span>'+h(r.get('model','?'))+'<small>'+h(r.get('benchmark','?'))+'</small></span>'+chart+'<strong>'+number(mean)+'<small>'+number(low)+'–'+number(high)+'</small></strong></div>']
    return ''.join(out) + '</details></section>'


def _category_table(rows, points, badge, language):
    t = lambda en, ru: choose(language,en,ru)
    categories = sorted({c for r in rows for c in (r.get('chat_category_scores_native') or {})})
    if not categories:
        return ''
    names = {'russian_language_style': ('Russian language & style', 'Русский язык и стиль'),
             'dialogue_context': ('Dialogue & context', 'Диалог и контекст'), 'groundedness': ('Evidence grounding', 'Опора на факты'),
             'instruction_semantic_precision': ('Instructions & meaning', 'Инструкции и смысл'), 'general_reasoning': ('Reasoning', 'Логика')}
    out = ['<section><details><summary>'+t('Quality by category', 'Качество по категориям')+'</summary><div class="table-wrap"><table><thead><tr><th>'+t('Category','Категория')+'</th>'+''.join('<th>'+badge(p['model'])+'</th>' for p in points)+'</tr></thead><tbody>']
    for category in categories:
        out += ['<tr><th>'+h(t(*names.get(category,(category,category))))+'</th>']
        for r in rows:
            value = _number((r.get('chat_category_scores_native') or {}).get(category))
            out += ['<td>'+pct(value)+'</td>']
        out += ['</tr>']
    return ''.join(out)+'</tbody></table></div></details></section>'


def _language_tracks_table(rows, points, badge, language):
    """Render paired RU/EN measurements without manufacturing a combined score."""
    if not any((row.get('language_tracks') or {}) for row in rows):
        return ''
    t=lambda en,ru: choose(language,en,ru)
    out=['<section><div class="eyebrow">LANGUAGE / TRACKS</div><h2>'+t('Russian and English prompt tracks','Треки русских и английских prompts')+'</h2><p class="lead">'+t(
        'Each value is measured separately. BULL does not merge Russian and English results into one quality score.',
        'Каждое значение измерено отдельно. BULL не объединяет русский и английский результаты в один балл качества.')+
        '</p><div class="table-wrap"><table><thead><tr><th>'+t('Model','Модель')+'</th><th>RU</th><th>EN</th><th>'+t('RU − EN quality','Качество RU − EN')+'</th></tr></thead><tbody>']
    for row,p in zip(rows,points):
        tracks=row.get('language_tracks') or {}
        def cell(track):
            values=tracks.get(track)
            if not values:
                return '—'
            q=pct(values.get('native_score'))
            speed=fmt(values.get('warm_tok_s'),' tok/s')
            task=pct(values.get('task_completion'))
            return q+'<small>'+t('TASK ','TASK ')+task+' · '+speed+'</small>'
        ru=(tracks.get('ru') or {}).get('native_score'); en=(tracks.get('en') or {}).get('native_score')
        delta='—' if ru is None or en is None else f'{(float(ru)-float(en))*100:+.1f} pp'
        out += ['<tr><th>'+badge(p['model'])+' '+h(p['model'])+'</th><td>'+cell('ru')+'</td><td>'+cell('en')+'</td><td>'+delta+'</td></tr>']
    return ''.join(out)+'</tbody></table></div><p class="micro">'+t(
        'A difference describes this run only. Compare task completion and throughput alongside score before drawing a conclusion.',
        'Разница описывает только этот прогон. Перед выводом сопоставьте score с выполнением контракта и скоростью.')+'</p></section>'


def _failure_details(rows, points, badge, language):
    t = lambda en,ru: choose(language,en,ru)
    out = ['<details><summary>'+t('Critical findings & execution errors', 'Критические замечания и ошибки выполнения')+'</summary><p>'+t(
        'Critical findings flag answer-contract issues for review; they are not application crashes. Transport errors are counted separately.',
        'Критические замечания — сигналы о нарушении контракта ответа, а не падения приложения. Ошибки соединения учитываются отдельно.')+'</p>']
    for row,p in zip(rows,points):
        out += ['<h3>'+badge(p['model'])+' '+h(p['model'])+'</h3><p>'+t('Execution errors: ','Ошибок выполнения: ')+str(int(row.get('failed_runs') or 0))+' · '+
                t('Transport interruptions: ','Разрывов соединения: ')+str(int(row.get('client_transport_failures') or 0))+' · '+
                t('Critical findings: ','Критических замечаний: ')+str(int(row.get('critical_failure_count') or 0))+'</p><ul>']
        for finding in row.get('critical_failures') or []:
            out += ['<li>'+h(finding.get('test','?'))+' · seed '+fmt(finding.get('seed'),digits=0)+'</li>']
        out += ['</ul>']
    return ''.join(out)+'</details>'


def _context_curves(details, language):
    groups = {}
    for row in details:
        ctx = _number(row.get('context_length'))
        score = _number(row.get('native_model_score', row.get('native_score_avg')))
        if ctx is not None and ctx > 0 and score is not None:
            groups.setdefault((str(row.get('model')), str(row.get('backend')), str(row.get('benchmark'))), []).append((ctx,score))
    charts = []
    for key, values in groups.items():
        # Do not pick an arbitrary score from duplicate/mixed configurations.
        if len({v[0] for v in values}) != len(values) or len(values) < 2:
            continue
        values.sort()
        low, high = math.log2(values[0][0]), math.log2(values[-1][0])
        coords = ' '.join(f'{20+(math.log2(ctx)-low)/(high-low)*460:.1f},{120-max(0,min(1,q))*100:.1f}' for ctx,q in values)
        charts.append('<h3>'+h(key[0]+' · '+key[2])+'</h3><svg viewBox="0 0 500 140" role="img" aria-label="Context curve"><polyline fill="none" stroke="#FF3C52" stroke-width="3" points="'+coords+'"/></svg><p>'+h(' · '.join(f'{ctx:g} ctx: {pct(q)}' for ctx,q in values))+'</p>')
    return '<details><summary>Context curves</summary>'+(''.join(charts) or '<p>'+choose(language,
        'A curve requires two comparable context lengths for the same model and test; no trend is inferred here.',
        'Для кривой нужны два сопоставимых размера контекста одной модели и теста; здесь тенденция не выводится.')+'</p>')+'</details>'


STYLE = '''
:root{color-scheme:dark;--bg:#0C1016;--panel:#151B24;--ink:#F4F7FB;--muted:#B0BDCD;--line:#344152;--red:#FF3C52}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:78px}body{margin:0;background:radial-gradient(ellipse at 8% 0,#481724 0,transparent 35%),var(--bg);color:var(--ink);font:16px/1.55 'Segoe UI',Arial,sans-serif}main{max-width:1360px;margin:auto;padding:28px 24px 60px}header{position:relative;background:linear-gradient(120deg,#291723,#141C28);border:1px solid #6F2C3B;border-radius:22px;padding:40px;min-height:270px;overflow:hidden}header h1{max-width:850px;font-size:clamp(32px,4.4vw,60px);line-height:1.08;margin:18px 0}header>p{color:#D6DEEA;max-width:700px}.brand-mark{float:right;width:145px;height:145px;object-fit:contain;margin:0 0 12px 20px}.eyebrow{font-size:12px;font-weight:800;letter-spacing:.13em;color:#FF8190}h2{font-size:30px;line-height:1.2;margin:8px 0 16px}h3{font-size:18px;line-height:1.35;margin:0 0 12px;overflow-wrap:anywhere}p{margin:10px 0 16px}a{color:inherit}nav{display:flex;flex-wrap:wrap;gap:8px;position:sticky;top:0;z-index:5;background:#0C1016F5;padding:14px 0}nav a{padding:8px 15px;border:1px solid var(--line);border-radius:999px;text-decoration:none;font-size:14px}nav a:hover,nav a:focus-visible{background:#5F2030;border-color:var(--red)}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;clear:both;margin-top:26px}.kpis div{border-top:2px solid var(--red);padding-top:8px}.kpis strong{display:block;font-size:30px}.kpis span{font-size:14px;color:var(--muted)}section{padding:28px;margin-top:24px;background:var(--panel);border:1px solid var(--line);border-radius:18px}section:target{border-color:var(--red)}.lead,.micro,small{color:var(--muted)}.micro,small{font-size:13px}small{display:block}section>h3{margin-top:28px}.rank-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:22px 0 30px}.rank-card,.decision-card,.model-card,.resource-card{min-width:0;background:#101620;border:1px solid var(--line);border-radius:14px;padding:18px}.rank-card{border-top:3px solid var(--red)}ol{padding:0;list-style:none;margin:12px 0 0}.rank-card li{display:flex;align-items:flex-start;gap:12px;border-top:1px solid var(--line);padding:15px 0}.rank-card li>div{min-width:0}.place{font-size:20px;font-weight:800;color:#FF8190}.rank-value{display:block;font-size:25px;margin-top:4px;font-variant-numeric:tabular-nums}.model-name{font-size:13px;overflow-wrap:anywhere}.model-id{display:inline-block;white-space:nowrap;font-size:12px;line-height:1.6;padding:1px 7px;border-radius:5px;background:#19212D;color:var(--model);border-left:3px solid var(--model)}.decision-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.recommendation{font-size:15px;font-weight:700;overflow-wrap:anywhere}.warning{color:#FFC857;font-size:13px}.notice{background:#302330;border:1px solid #7F5160;border-left:4px solid #FF6174;padding:18px;border-radius:10px}.notice li{margin-bottom:10px}.quality-grid,.resource-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:18px}.resource-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.bar-label{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:13px;margin:10px 0 5px}.metric-track{height:10px;background:#2B3544;border-radius:5px;overflow:hidden;margin-bottom:13px}.metric-bar{display:block;height:100%;border-radius:5px}.unknown{background:repeating-linear-gradient(45deg,#27303D,#27303D 5px,#131A23 5px,#131A23 10px)}.scatter{display:block;width:100%;max-height:480px;margin:10px auto}.scatter text{fill:#C2CEDD;font:13px 'Segoe UI',Arial,sans-serif}.scatter .point-label{fill:#fff;font-weight:800;paint-order:stroke;stroke:#101620;stroke-width:3px}.gridline{fill:none;stroke:#354253;stroke-width:1}.legend{display:flex;flex-wrap:wrap;gap:8px 20px}.legend span{font-size:13px;overflow-wrap:anywhere;max-width:100%}details{margin-top:16px;border-top:1px solid var(--line);padding-top:14px}summary{cursor:pointer;font-weight:700;color:#FFABB5;padding:6px 0}summary:focus-visible{outline:2px solid var(--red)}details li{font-size:13px;overflow-wrap:anywhere;margin:12px 0}dl{display:grid;grid-template-columns:1fr 1fr;font-size:13px;gap:7px 16px}dt{color:var(--muted)}dd{margin:0;text-align:right;overflow-wrap:anywhere}.table-wrap{overflow:auto;margin:18px 0;max-width:100%}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}th:first-child,td:first-child{text-align:left;white-space:normal;min-width:180px;max-width:330px;overflow-wrap:anywhere}thead{background:#232C3B}thead th{color:#D9E1ED;font-size:12px}tbody th{font-weight:600}.heatmap th:first-child{min-width:240px}.heatmap code{font-size:11px;color:#8293AA;overflow-wrap:anywhere}.heat{display:block;min-width:85px;background:linear-gradient(90deg,#752738 var(--heat),#202B39 var(--heat));border:1px solid #72505E;border-radius:6px;padding:8px;font-weight:800;color:#fff}.empty{color:var(--muted)}footer{padding:28px 0;color:var(--muted);font-size:13px}.model-card svg{width:100%}
@media(max-width:1000px){.decision-grid,.resource-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.rank-grid{grid-template-columns:1fr}.rank-card ol{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}
@media(max-width:620px){main{padding:12px}header{padding:22px}.brand-mark{width:76px;height:76px}section{padding:18px}.kpis{grid-template-columns:1fr 1fr}.rank-card ol,.decision-grid,.quality-grid,.resource-grid{grid-template-columns:1fr}nav{position:static;gap:6px}nav a{padding:6px 10px;font-size:13px}h2{font-size:25px}.scatter text{font-size:15px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{body{background:#fff;color:#111}main{padding:0}nav{display:none}section,header{break-inside:avoid;box-shadow:none}*{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
.rank-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.comparison-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.comparison-card{min-width:0;background:#101620;border:1px solid var(--line);border-top:3px solid #51C8FF;border-radius:14px;padding:18px}.comparison-card h4{font-size:13px;margin:18px 0 7px;color:var(--muted)}.stability-track{height:14px;background:#2B3544;position:relative;border-radius:7px;margin:4px 0 5px}.stability-range{position:absolute;height:8px;top:3px;border-radius:5px}.stability-dot{position:absolute;height:14px;top:0;width:3px;transform:translateX(-50%);background:#fff}.ci-row{display:grid;grid-template-columns:minmax(160px,1fr) minmax(180px,2fr) 120px;gap:16px;align-items:center;margin:14px 0;font-size:13px}.ci-row>span{overflow-wrap:anywhere}.ci-track{height:14px;background:#2B3544;position:relative;border-radius:6px}.ci-range{position:absolute;height:8px;top:3px;background:#FF6174;border-radius:5px}.ci-dot{position:absolute;height:14px;top:0;width:3px;transform:translateX(-50%);background:#fff}
@media(max-width:1000px){.rank-grid,.comparison-grid{grid-template-columns:1fr 1fr}.rank-card ol{display:block}}
@media(max-width:620px){.rank-grid,.comparison-grid{grid-template-columns:1fr}.ci-row{grid-template-columns:1fr}}
'''
