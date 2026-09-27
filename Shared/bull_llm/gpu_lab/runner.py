"""Sequential, recoverable GPU experiments. Outputs stay private and local."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from ..storage import atomic_json
from ..http_transport import decode_object
from .contracts import SCHEMA, VERSION, validate_config, fingerprint, plan, request, placement, number
from .transport import Session


@contextmanager
def run_lock(path):
    """OS lock is released after crash; no stale-PID heuristics or lock deletion."""
    with Path(str(path) + '.lock').open('a+b') as stream:
        stream.seek(0); stream.write(b'1'); stream.flush(); stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try: yield
        finally:
            stream.seek(0)
            if os.name == 'nt': msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(stream, fcntl.LOCK_UN)


def inventory_identity(inventory):
    return sorted([dict(uuid=g['uuid'], name=g['name'], memory_mib=g['memory_mib'], driver=g['driver']) for g in inventory], key=lambda g: g['uuid'])


def new_result(cfg, inventory):
    cfg = validate_config(cfg)
    return dict(schema=SCHEMA, version=VERSION, created_utc=datetime.now(timezone.utc).isoformat(),
                config=cfg, config_sha256=fingerprint(cfg), inventory=inventory_identity(inventory),
                workloads_sha256=fingerprint([request(cfg, j) for j in plan(cfg)]),
                jobs=plan(cfg), completed=[], attempts=[], active=None, status='ready',
                ollama_version=None, model_digests={}, events=[])


def check_result(result):
    if result.get('schema') != SCHEMA or result.get('version') != VERSION: raise ValueError('Неизвестная версия GPU результата')
    cfg = validate_config(result['config'])
    if result['config_sha256'] != fingerprint(cfg) or result['jobs'] != plan(cfg): raise ValueError('GPU config/plan изменён')
    if result['workloads_sha256'] != fingerprint([request(cfg, j) for j in plan(cfg)]): raise ValueError('Версия GPU workloads изменилась: нужен новый эксперимент')
    ids = [r['job']['id'] for r in result['completed']]
    if len(set(ids)) != len(ids) or any(r['job'] not in result['jobs'] for r in result['completed']): raise ValueError('Повторный или неизвестный GPU run')
    if any([p.get('phase') for p in r.get('phases', [])] != ['fresh_process', 'repeat_same_prompt'] for r in result['completed']):
        raise ValueError('Checkpoint marks an incomplete pair as complete')
    return cfg


def background_status(sample, selected):
    if not sample.get('process_query_available'): return 'unknown'
    if any(p['uuid'] in selected for p in sample.get('processes', [])): return 'busy'
    if any((number(g.get('utilization')) or 0) > 10 for g in sample.get('gpus', []) if g['uuid'] in selected): return 'busy'
    return 'idle_observed'


def thermal_check(samples, selected):
    for sample in samples:
        if any((number(g.get('temperature_c')) or 0) >= 85 for g in sample.get('gpus', []) if g['uuid'] in selected):
            raise RuntimeError('GPU_TEMPERATURE_AT_LEAST_85C')


def execute(worker, result, path, private=None, progress=lambda s: None, session_type=Session):
    """Resume only complete pairs; interrupted pair is archived then restarted cold."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with run_lock(path):
        if path.exists():
            if path.stat().st_size > 64 * 1024 * 1024: raise ValueError('GPU result exceeds 64 MiB')
            saved = decode_object(path.read_text(encoding='utf-8'))
            if saved.get('config_sha256') != result.get('config_sha256'): raise ValueError('Checkpoint differs from selected experiment')
            result = saved  # Read under the lock, not a possibly stale UI snapshot.
        cfg = check_result(result)
        inventory = inventory_identity(worker.rpc('inventory')['gpus'])
        if inventory != result['inventory']: raise ValueError('GPU inventory/driver changed; create a new experiment')
        if result.get('active'):
            result['attempts'].append(result['active']); result['active'] = None
            result['events'].append(dict(event='abandoned_pair_after_interruption', at=time.time()))
        done = {r['job']['id'] for r in result['completed']}
        result['status'] = 'running'; atomic_json(path, result)
        for ordinal, job in enumerate(result['jobs'], 1):
            if job['id'] in done: continue
            row = dict(job=job, phases=[], started_utc=datetime.now(timezone.utc).isoformat())
            result['active'] = row; atomic_json(path, result)
            progress(f"{ordinal}/{len(result['jobs'])} | {job['model']} | {job['workload']} | {len(job['devices'])} GPU | seed {job['seed']}")
            try:
                before = worker.sample(); thermal_check([before], job['devices'])
                row['background'] = background_status(before, job['devices'])
                row['before'] = before
                if row['background'] == 'busy': raise RuntimeError('GPU_BUSY_CLOSE_OTHER_MODELS_OR_APPS')
                with session_type(worker, job['devices'], private) as session:
                    if result['ollama_version'] not in (None, session.version): raise RuntimeError('OLLAMA_VERSION_CHANGED')
                    result['ollama_version'] = session.version
                    catalog = session.api('/api/tags').get('models', [])
                    model = next((m for m in catalog if m.get('name') == job['model']), None)
                    if not model or not model.get('digest'): raise RuntimeError('LOCAL_MODEL_NOT_FOUND')
                    details = session.api('/api/show', dict(model=job['model']))
                    if details.get('remote_model') or details.get('remote_host'): raise RuntimeError('REMOTE_MODEL_FORBIDDEN')
                    digest = model['digest']
                    if result['model_digests'].get(job['model'], digest) != digest: raise RuntimeError('MODEL_DIGEST_CHANGED')
                    result['model_digests'][job['model']] = digest
                    row['digest'] = digest
                    launch = dict(session.launch['environment']); launch.pop('OLLAMA_HOST', None)
                    row['launch_environment'] = launch
                    row['launch_fingerprint'] = fingerprint(dict(env=launch, version=session.version, digest=digest, inventory=inventory))
                    row['request_fingerprint'] = fingerprint(request(cfg, job))
                    atomic_json(path, result)
                    for phase in ('fresh_process', 'repeat_same_prompt'):
                        progress('  ' + ('Первый запрос / загрузка' if phase == 'fresh_process' else 'Повтор / возможен KV cache hit'))
                        started = time.monotonic()
                        metrics = session.generate(request(cfg, job), cfg['timeout'])
                        worker.sample()  # Post-request residency, including very short generations.
                        samples = worker.samples_since(started)
                        thermal_check(samples, job['devices'])
                        gpu_placement = placement(job['devices'], samples)
                        foreign_compute = any(p['uuid'] in job['devices'] and p['pid'] not in s.get('owned_pids', [])
                                              for s in samples for p in s.get('processes', []))
                        running = session.api('/api/ps').get('models', [])
                        runtime = next((m for m in running if m.get('name', m.get('model')) == job['model']), {})
                        runtime = {k: runtime.get(k) for k in ('digest', 'size', 'size_vram', 'context_length')}
                        vram = number(runtime['size_vram'])
                        accelerator = 'unknown' if vram is None else 'cpu_only' if vram == 0 else 'gpu_offload_observed'
                        context_ok = runtime['context_length'] in (None, cfg['context'])
                        evidence = dict(placement=gpu_placement, runtime=runtime)
                        # Bound checkpoint size. Summary sensor peaks are sampled, not continuous maxima.
                        stride = max(1, (len(samples) + 59) // 60)
                        retained = samples[::stride]
                        if samples and retained[-1] is not samples[-1]: retained.append(samples[-1])
                        phase_row = dict(phase=phase, metrics=metrics, samples=retained, sample_count=len(samples), **evidence,
                                         accelerator=accelerator, context_matches=context_ok,
                                         foreign_compute_detected=foreign_compute,
                                         runtime_fingerprint=fingerprint(evidence),
                                         comparable=gpu_placement['status'] == 'observed_selected' and row['background'] == 'idle_observed' and vram is not None and vram > 0 and context_ok and not foreign_compute)
                        row['phases'].append(phase_row); atomic_json(path, result)
                        if gpu_placement['status'] == 'unexpected_device': raise RuntimeError('UNSELECTED_GPU_OBSERVED')
                result['completed'].append(row); result['active'] = None; atomic_json(path, result)
            except (Exception, KeyboardInterrupt) as exc:
                result['status'] = 'paused'
                # Do not serialize exception paths, endpoints, headers or response bodies.
                text = str(exc)
                code = text if text.isascii() and text.replace('_', '').isalnum() and len(text) <= 90 else type(exc).__name__
                row['error'] = code
                result['events'].append(dict(event='paused', code=code, at=time.time()))
                atomic_json(path, result)
                progress('Пауза: ' + code + '. Готовые пары сохранены; незавершённая начнётся заново.')
                return result
        result['status'] = 'completed'; atomic_json(path, result)
        return result
