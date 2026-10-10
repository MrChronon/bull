"""Build a clearly labelled synthetic report for visual QA; never run models."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from Shared.bull_llm.results_report import render_report
    client = ROOT / 'bull_client_v0.29.0.1.py'
    spec = importlib.util.spec_from_file_location('bull_report_preview', client)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    records = []
    # Deliberately reproduce one qualified candidate plus faster alternatives.
    for mi, (model, score, speed, vram) in enumerate((
        ('Atlas-27B-Q6-context-32k:synthetic', .948, 26.8, 10445),
        ('Boreal-Code-80B-Q4-context-128k:synthetic', .825, 29.2, 10640),
        ('Cirrus-35B-Q4-context-128k:synthetic', .712, 53.1, 9550),
    )):
        for ti, test in enumerate(core.CHAT_CORE_TESTS):
            for seed in (42,43,44):
                quality = max(0, min(1, score + (seed-43)*.012 + (ti%3-1)*.02))
                record = {
                    'record_schema_version': 12, 'execution_status': 'ok',
                    'identity': {'model': model, 'backend': 'ollama', 'benchmark': test,
                                 'benchmark_mode': 'native', 'benchmark_version': 1, 'run': seed-41},
                    'config': {'seed': seed, 'ctx': 32768, 'threads': 12, 'primary_predict': 1800,
                               'temperature': .2, 'top_p': .9, 'top_k': 40, 'min_p': 0,
                               'think': False, 'sampling_source': 'benchmark_override'},
                    'primary': {'generation_completed': True, 'task_completed': True,
                                'structural_completion': True, 'schema_exact': True,
                                'eval_rate': speed+(seed-43)*.4, 'load_state': 'warm',
                                'load_seconds': .01, 'answer': ''},
                    'final': {'generation_completed': True, 'task_completed': True,
                              'pipeline_wall_seconds': 550/speed + ti*.3, 'answer': ''},
                    'score': {'native': {'value': quality}, 'final': {'value': quality}},
                    'telemetry': {'gpu': {'vram_peak_mib': vram, 'gpu_util_avg': 55+mi*12},
                                  'system': {'cpu_util_avg': 38+mi*14,
                                             'ram_used_peak_bytes': (32-mi*5)*1024**3,
                                             'ram_total_bytes': 64*1024**3}},
                }
                records.append(record)
    models = core.benchmark_model_summary_rows(records)
    details = core.benchmark_summary_rows(records)
    folder = ROOT / 'Runtime/report-preview'
    folder.mkdir(parents=True, exist_ok=True)
    for language in ('en','ru'):
        page = render_report(models,details,version='PREVIEW / SYNTHETIC DATA',language=language)
        path = folder / f'report-{language}.html'
        path.write_text(page, encoding='utf-8')
        print(path)


if __name__ == '__main__':
    main()
