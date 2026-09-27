"""Versioned performance-only experiments. No quality score or recovery."""
from __future__ import annotations
import hashlib
import json
import math
import re
import statistics

SCHEMA = 'local-llm-gpu-experiment'
VERSION = 1
UUID = re.compile(r'GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z')
WORKLOADS = {
    'decode': ('Генерация текста', 'Write a detailed numbered guide to organizing a public library. Explain each step.'),
    'code': ('Генерация кода (без исполнения)', 'Write a Python LRU cache with type hints, docstrings and ten unit tests. Output source code only.'),
    'prefill': ('Длинный вход', '\n'.join(f'Record {i}: warehouse {i % 13}, stock {i % 97}, region {i % 7}.' for i in range(160)) + '\nSummarize the inventory structure and explain how to validate it.'),
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n >= 0 else None
    except (TypeError, ValueError): return None


def validate_config(value):
    cfg = dict(schema=SCHEMA, version=VERSION, models=[], devices=[], workloads=['decode'],
               repeats=3, context=4096, tokens=512, timeout=600, custom_prompt='')
    if not isinstance(value, dict) or set(value) - set(cfg): raise ValueError('Неизвестные поля GPU config')
    cfg.update(value)
    if cfg['schema'] != SCHEMA or cfg['version'] != VERSION: raise ValueError('Неизвестная версия GPU config')
    for name, lo, hi in [('repeats', 1, 10), ('context', 4096, 32768), ('tokens', 32, 2048), ('timeout', 30, 1800)]:
        if type(cfg[name]) is not int or not lo <= cfg[name] <= hi: raise ValueError(f'{name}: допустимо {lo}..{hi}')
    models = cfg['models']
    if not isinstance(models, list) or not 1 <= len(models) <= 8 or any(not isinstance(m, str) or not re.fullmatch(r'[\w][\w./:@+-]{0,199}', m, re.ASCII) or 'cloud' in m.casefold() for m in models):
        raise ValueError('Выберите 1..8 установленных локальных моделей без cloud')
    if len(set(models)) != len(models): raise ValueError('Повтор модели')
    devices = cfg['devices']
    if not isinstance(devices, list) or not 1 <= len(devices) <= 8: raise ValueError('Выберите 1..8 GPU-конфигураций')
    seen = set()
    for row in devices:
        if not isinstance(row, list) or not 1 <= len(row) <= 8 or any(not isinstance(u, str) or not UUID.fullmatch(u) for u in row) or len(set(row)) != len(row):
            raise ValueError('Нужны уникальные полные NVIDIA GPU UUID')
        key = tuple(sorted(row))
        if key in seen: raise ValueError('Повтор GPU-конфигурации')
        seen.add(key)
    if not isinstance(cfg['custom_prompt'], str) or len(cfg['custom_prompt']) > 32000: raise ValueError('Промпт: не более 32000 символов')
    ws = cfg['workloads']
    if not isinstance(ws, list) or not 1 <= len(ws) <= 4 or any(w not in (*WORKLOADS, 'custom') for w in ws) or len(set(ws)) != len(ws):
        raise ValueError('Неизвестный или повторный сценарий')
    if 'custom' in ws and not cfg['custom_prompt'].strip(): raise ValueError('Пустой пользовательский промпт')
    if len(models) * len(devices) * len(ws) * cfg['repeats'] > 120: raise ValueError('Не более 120 пар за эксперимент; разделите матрицу')
    return cfg


def process_environment(devices, port):
    if not devices or len(set(devices)) != len(devices) or any(not UUID.fullmatch(u) for u in devices): raise ValueError('Invalid GPU UUID')
    if type(port) is not int or not 1024 <= port <= 65535: raise ValueError('Invalid private port')
    return dict(CUDA_VISIBLE_DEVICES=','.join(devices), OLLAMA_HOST=f'127.0.0.1:{port}',
                OLLAMA_SCHED_SPREAD='1' if len(devices) > 1 else '0', OLLAMA_NO_CLOUD='1',
                OLLAMA_VULKAN='0', GGML_VK_VISIBLE_DEVICES='-1', ROCR_VISIBLE_DEVICES='-1', HIP_VISIBLE_DEVICES='-1',
                OLLAMA_FLASH_ATTENTION='0', OLLAMA_KV_CACHE_TYPE='f16', OLLAMA_NUM_PARALLEL='1',
                OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_KEEP_ALIVE='5m', OLLAMA_NOPRUNE='1',
                OLLAMA_DEBUG_LOG_REQUESTS='0', OLLAMA_DEBUG='0', OLLAMA_LOAD_TIMEOUT='10m')


def plan(cfg):
    """Latin rotation of GPU order, plus model/workload rotation between repeats."""
    jobs = []
    units = [(m, w) for m in cfg['models'] for w in cfg['workloads']]
    for repeat in range(cfg['repeats']):
        rotated = units[repeat % len(units):] + units[:repeat % len(units)]
        for i, (model, workload) in enumerate(rotated):
            ds = cfg['devices']; shift = (repeat + i) % len(ds)
            for devices in ds[shift:] + ds[:shift]:
                row = dict(model=model, workload=workload, devices=list(devices), repeat=repeat, seed=42 + repeat)
                row['id'] = fingerprint(row)[:20]; jobs.append(row)
    return jobs


def request(cfg, job):
    prompt = cfg['custom_prompt'] if job['workload'] == 'custom' else WORKLOADS[job['workload']][1]
    return dict(model=job['model'], prompt=prompt, raw=True, stream=True, keep_alive='5m',
                options=dict(num_ctx=cfg['context'], num_predict=cfg['tokens'], temperature=0,
                             top_p=1, top_k=40, min_p=0, repeat_penalty=1.0, seed=job['seed']))


def load_class(duration_ns):
    value = number(duration_ns)
    return 'unknown' if value is None else ('warm' if value <= 100_000_000 else 'load_observed')


def stats(values):
    rows = [n for v in values if (n := number(v)) is not None]
    return dict(n=len(rows), mean=statistics.mean(rows) if rows else None,
                sd=statistics.stdev(rows) if len(rows) > 1 else None,
                min=min(rows) if rows else None, max=max(rows) if rows else None)


def placement(selected, samples):
    """Process residency evidence, never infer ownership from total GPU activity."""
    observed = set()
    for sample in samples:
        owned = set(sample.get('owned_pids') or [])
        observed.update(p['uuid'] for p in sample.get('processes', []) if p.get('pid') in owned)
    wanted = set(selected)
    status = ('unexpected_device' if observed - wanted else 'observed_selected' if observed == wanted
              else 'partial' if observed else 'unverified')
    return dict(status=status, observed_uuids=sorted(observed), evidence='nvidia-smi owned process residency; not proof of compute balance')
