"""Owned Windows Ollama sidecar, locally or through the selected pinned SSH route."""
from __future__ import annotations
import base64
from collections import deque
import json
import os
from pathlib import Path
import queue
import socket
import struct
import subprocess
import threading
import time
import urllib.request

from ..http_transport import NoRedirect, open_response, json_object, decode_object
from .contracts import process_environment, number, load_class

FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def owns_local_listener(pid, port):
    """Verify SSH forwarding socket without admin/CIM, before sending any prompt."""
    import ctypes
    from ctypes import wintypes
    dll = ctypes.WinDLL('iphlpapi')
    fn = dll.GetExtendedTcpTable
    fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
    size = wintypes.DWORD(0); fn(None, ctypes.byref(size), False, 2, 3, 0)
    if not 4 <= size.value <= 16 * 1024 * 1024: raise RuntimeError('LOCAL_TCP_TABLE_UNAVAILABLE')
    buffer = ctypes.create_string_buffer(size.value)
    if fn(buffer, ctypes.byref(size), False, 2, 3, 0): raise RuntimeError('LOCAL_TCP_TABLE_UNAVAILABLE')
    count, = struct.unpack_from('<I', buffer)
    if count > (size.value - 4) // 24: raise RuntimeError('LOCAL_TCP_TABLE_INVALID')
    matched = []
    for i in range(count):
        _, address, raw_port, _, _, owner = struct.unpack_from('<6I', buffer, 4 + i * 24)
        actual = ((raw_port & 255) << 8) | ((raw_port >> 8) & 255)
        if actual == port: matched.append((address, owner))
    return matched == [(0x0100007f, pid)]


class Worker:
    """Lease-owned server: control EOF or >60s without commands closes the GPU job."""
    def __init__(self, core):
        self.core = core
        self.endpoint = None
        self.proc = None
        self.lock = threading.Lock()
        self.replies = queue.Queue(maxsize=16)
        self.samples = deque(maxlen=512)
        self.sample_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.failure = None
        self.active_devices = []

    def __enter__(self):
        if os.name != 'nt': raise ValueError('GPU Lab v1 требует Windows-клиент и Windows-сервер')
        if self.core.ACTIVE_BACKEND != 'ollama': raise ValueError('GPU Lab поддерживает Windows + Ollama. Выберите этот движок в Подключениях.')
        if self.core.load_backend_settings().get('target_mode', 'local') == 'remote':
            self.endpoint = self.core.resolve_remote_endpoint()
            if not self.endpoint.get('known_hosts_file') or not self.endpoint.get('host_key_fingerprint'):
                raise ValueError('GPU Lab требует SSH-подключение с закреплённым ключом сервера. Добавьте его через Подключения.')
        elif os.name != 'nt': raise ValueError('GPU Lab v1 поддерживает Windows-сервер')
        source = Path(__file__).resolve().parents[3] / 'Server/Gpu-Lab-Worker.ps1'
        bootstrap = "[Console]::InputEncoding=[Text.UTF8Encoding]::new($false); [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); & ([scriptblock]::Create([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String([Console]::ReadLine()))))"
        args = ['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', base64.b64encode(bootstrap.encode('utf-16-le')).decode()]
        if self.endpoint: args = self.core._ssh_base_args(self.endpoint, batch=True) + args
        try:
            self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=FLAGS)
            threading.Thread(target=self._reader, daemon=True).start()
            self.proc.stdin.write(base64.b64encode(source.read_text(encoding='utf-8-sig').encode()) + b'\n'); self.proc.stdin.flush()
            hello = self._reply(30)
            if hello.get('protocol') != 1 or hello.get('platform') != 'windows': raise RuntimeError('WORKER_PROTOCOL_MISMATCH')
            self.thread = threading.Thread(target=self._heartbeat, daemon=True); self.thread.start()
            return self
        except BaseException:
            self.close(); raise

    def _reader(self):
        try:
            while True:
                raw = self.proc.stdout.readline(262145)
                if not raw or len(raw) > 262144: break
                data = decode_object(raw.decode('utf-8-sig'))
                self.replies.put(data, timeout=2)
        except Exception: pass
        try: self.replies.put({'ok': False, 'error': 'WORKER_CONNECTION_CLOSED'}, timeout=1)
        except queue.Full: pass

    def _reply(self, timeout):
        try: result = self.replies.get(timeout=timeout)
        except queue.Empty as exc: raise TimeoutError('WORKER_TIMEOUT') from exc
        if not result.get('ok'): raise RuntimeError(result.get('error', 'WORKER_FAILURE'))
        return result

    def rpc(self, action, **kwargs):
        with self.lock:
            if self.failure: raise RuntimeError(self.failure)
            try:
                raw = json.dumps(dict(action=action, **kwargs), ensure_ascii=True).encode() + b'\n'
                if len(raw) > 131072: raise ValueError('WORKER_REQUEST_LIMIT')
                self.proc.stdin.write(raw); self.proc.stdin.flush()
                return self._reply(40).get('data', {})
            except (OSError, TimeoutError) as exc:
                self.failure = 'WORKER_CONNECTION_LOST'; raise RuntimeError(self.failure) from exc

    def sample(self):
        sample = self.rpc('sample')
        sample['client_observed_monotonic'] = time.monotonic()
        with self.sample_lock: self.samples.append(sample)
        return sample

    def samples_since(self, start):
        with self.sample_lock: return [s for s in self.samples if s['client_observed_monotonic'] >= start]

    def _heartbeat(self):
        while not self.stop_event.wait(5):
            try:
                sample = self.sample()
                if self.active_devices and any((number(g.get('temperature_c')) or 0) >= 85 for g in sample.get('gpus', []) if g['uuid'] in self.active_devices):
                    self.rpc('stop')
                    self.failure = 'GPU_TEMPERATURE_AT_LEAST_85C'
                    return
            except Exception:
                self.failure = 'WORKER_TELEMETRY_OR_CONNECTION_LOST'; return

    def close(self):
        self.stop_event.set()
        if self.proc:
            # EOF releases the worker's Job Object; no process-name termination.
            try: self.proc.stdin.close()
            except (OSError, ValueError): pass
            try: self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired: self.proc.kill(); self.proc.wait(timeout=5)
            if self.thread: self.thread.join(timeout=2)
            try: self.proc.stdout.close()
            except (OSError, ValueError): pass
            self.proc = None

    def __exit__(self, *args): self.close()


class Session:
    def __init__(self, worker, devices, private=None):
        self.worker, self.devices, self.private = worker, devices, private or {}
        self.tunnel = None
        self.launch = None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def __enter__(self):
        try:
            self.launch = self.worker.rpc('start', devices=self.devices, executable=self.private.get('executable', ''), models_dir=self.private.get('models_dir', ''))
            self.worker.active_devices = list(self.devices)
            port = self.launch['port']
            if self.launch['environment'] != process_environment(self.devices, port): raise RuntimeError('LAUNCH_ENVIRONMENT_MISMATCH')
            if self.worker.endpoint:
                local = free_port()
                args = self.worker.core._ssh_base_args(self.worker.endpoint, batch=True)
                args = args[:-1] + ['-N', '-o', 'ExitOnForwardFailure=yes', '-L', f'127.0.0.1:{local}:127.0.0.1:{port}', args[-1]]
                self.tunnel = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=FLAGS)
                port = local
            self.base = f'http://127.0.0.1:{port}'
            for _ in range(30):
                if self.tunnel and self.tunnel.poll() is not None: raise RuntimeError('LAB_SSH_FORWARD_FAILED')
                if self.tunnel and not owns_local_listener(self.tunnel.pid, port):
                    time.sleep(.25); continue
                try:
                    self.version = self.api('/api/version', timeout=2)['version']; break
                except (OSError, TimeoutError): time.sleep(.25)
            else: raise RuntimeError('LAB_API_NOT_READY')
            self.worker.rpc('guard')
            return self
        except BaseException:
            self.__exit__(); raise

    def api(self, path, payload=None, timeout=30):
        req = urllib.request.Request(self.base + path, data=None if payload is None else json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with open_response(self.opener, req, timeout) as response: return json_object(response)

    def generate(self, payload, timeout):
        self.worker.rpc('guard')
        start = time.monotonic(); first = None; final = None
        req = urllib.request.Request(self.base + '/api/generate', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with open_response(self.opener, req, timeout) as response:
            for raw in response:
                if not raw.strip(): continue
                chunk = decode_object(raw.decode('utf-8'))
                if chunk.get('error'): raise RuntimeError('OLLAMA_GENERATION_ERROR')
                if first is None and (chunk.get('response') or chunk.get('thinking')): first = time.monotonic() - start
                if chunk.get('done') is True:
                    final = chunk; break
        wall = time.monotonic() - start
        if final is None: raise ConnectionResetError('INCOMPLETE_OLLAMA_STREAM')
        if not (number(final.get('eval_count')) or 0): raise RuntimeError('NO_GENERATED_TOKENS')
        fields = ('total_duration', 'load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration')
        metrics = {k: number(final.get(k)) for k in fields}
        for prefix, count, duration in [('decode', 'eval_count', 'eval_duration'), ('prefill', 'prompt_eval_count', 'prompt_eval_duration')]:
            metrics[prefix + '_tok_s'] = metrics[count] / (metrics[duration] / 1e9) if metrics[count] is not None and metrics[duration] else None
        metrics.update(wall_s=wall, ttft_client_s=first, load_class=load_class(metrics['load_duration']),
                       done_reason=final.get('done_reason', 'unknown'), output_capped=final.get('done_reason') == 'length')
        return metrics

    def __exit__(self, *args):
        self.worker.active_devices = []
        if self.tunnel:
            self.tunnel.terminate()
            try: self.tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired: self.tunnel.kill(); self.tunnel.wait(timeout=5)
            self.tunnel = None
        if self.launch:
            try: self.worker.rpc('stop')
            except Exception:
                self.worker.close()
                if not args or args[0] is None: raise RuntimeError('LAB_CLEANUP_CONNECTION_LOST')
            finally: self.launch = None
