"""GPU Lab contracts: offline, no real inference or selected SSH endpoint."""
import copy
import contextlib
import io
import os
import subprocess
import types
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Shared.bull_llm.gpu_lab import contracts as c

A = 'GPU-11111111-1111-1111-1111-111111111111'
B = 'GPU-22222222-2222-2222-2222-222222222222'


class GPUContracts(unittest.TestCase):
    def config(self):
        return c.validate_config(dict(models=['fixture:latest'], devices=[[A], [B], [A, B]],
                                      workloads=['decode'], repeats=3, context=4096, tokens=128))

    def test_uuid_not_unstable_index(self):
        value = self.config(); value['devices'] = [['0']]
        with self.assertRaises(ValueError): c.validate_config(value)

    def test_reject_duplicates_and_cloud(self):
        for key, value in [('devices', [[A, A]]), ('models', ['remote:cloud']), ('repeats', True),
                           ('repeats', 99), ('context', 1), ('tokens', 0), ('workloads', ['shell'])]:
            config = self.config(); config[key] = value
            with self.assertRaises(ValueError): c.validate_config(config)

    def test_explicit_process_environment(self):
        env = c.process_environment([A, B], 23456)
        self.assertEqual(env['CUDA_VISIBLE_DEVICES'], A + ',' + B)
        self.assertEqual(env['OLLAMA_SCHED_SPREAD'], '1')
        self.assertEqual(env['OLLAMA_HOST'], '127.0.0.1:23456')
        self.assertEqual(env['OLLAMA_NO_CLOUD'], '1')
        self.assertEqual(env['GGML_VK_VISIBLE_DEVICES'], '-1')
        self.assertEqual(env['OLLAMA_FLASH_ATTENTION'], '0')

    def test_counterbalanced_order(self):
        jobs = c.plan(self.config())
        self.assertEqual(len(jobs), 9)
        self.assertEqual([r['devices'][0] for r in jobs[:3]], [A, B, A])
        self.assertEqual(jobs[3]['devices'], [B])
        self.assertEqual(len({r['id'] for r in jobs}), 9)

    def test_unknown_sensors_not_zero(self):
        self.assertIsNone(c.number('[N/A]'))
        self.assertIsNone(c.number('nan'))
        self.assertEqual(c.number('0'), 0)

    def test_placement_requires_owned_pid_and_all_cards(self):
        samples = [dict(owned_pids=[12], processes=[dict(pid=12, uuid=A), dict(pid=99, uuid=B)])]
        self.assertEqual(c.placement([A, B], samples)['status'], 'partial')
        self.assertEqual(c.placement([A], samples)['status'], 'observed_selected')
        self.assertEqual(c.placement([B], samples)['status'], 'unexpected_device')
        self.assertEqual(c.placement([A], [])['status'], 'unverified')

    def test_warm_uses_duration_not_position(self):
        self.assertEqual(c.load_class(500_000_000), 'load_observed')
        self.assertEqual(c.load_class(2_000_000), 'warm')
        self.assertEqual(c.load_class(None), 'unknown')

    def test_statistics(self):
        self.assertIsNone(c.stats([10])['sd'])
        self.assertEqual(c.stats([10, 20, 30]), dict(n=3, mean=20, sd=10, min=10, max=30))

    def test_request_options_are_bounded_and_same_across_devices(self):
        cfg = self.config(); a, b = c.plan(cfg)[:2]
        self.assertEqual(c.request(cfg, a), c.request(cfg, b))
        self.assertTrue(c.request(cfg, a)['raw'])
        self.assertNotIn('recovery', c.request(cfg, a))

    def test_oversize_custom_prompt(self):
        config = self.config(); config['custom_prompt'] = 'x' * 32001
        with self.assertRaises(ValueError): c.validate_config(config)

    def test_worker_ownership_safety_contract(self):
        src = (Path(__file__).resolve().parents[1] / 'Server/Gpu-Lab-Worker.ps1').read_text(encoding='utf-8-sig')
        self.assertIn('KILL_ON_JOB_CLOSE', src)
        self.assertIn('AssignProcessToJobObject', src)
        self.assertIn('60000', src)
        self.assertNotIn('Stop-Process -Name', src)
        self.assertNotIn('SetEnvironmentVariable', src)

    def test_html_excludes_private_prompt_and_uuid(self):
        from Shared.bull_llm.gpu_lab.runner import new_result
        from Shared.bull_llm.gpu_lab.reports import export
        cfg=self.config(); cfg['custom_prompt']='private secret fixture'
        result=new_result(cfg,[dict(uuid=A,name='Fixture <Card>',memory_mib='10',driver='999')])
        with tempfile.TemporaryDirectory() as tmp:
            text=export(result,tmp).read_text(encoding='utf-8')
            self.assertNotIn(cfg['custom_prompt'],text); self.assertNotIn(A,text)
            self.assertNotIn('<script',text); self.assertNotIn('https://',text)

    def test_changed_workloads_fail_resume(self):
        from Shared.bull_llm.gpu_lab.runner import new_result, check_result
        result=new_result(self.config(),[]); result['workloads_sha256']='bad'
        with self.assertRaises(ValueError): check_result(result)

    def test_corrupt_completed_pair_cannot_skip_a_request(self):
        from Shared.bull_llm.gpu_lab.runner import new_result, check_result
        result=new_result(self.config(),[])
        result['completed']=[dict(job=result['jobs'][0],phases=[dict(phase='fresh_process')])]
        with self.assertRaises(ValueError): check_result(result)

    @unittest.skipUnless(os.name=='nt','Windows forwarding ownership')
    def test_forwarding_socket_must_be_loopback_and_owned(self):
        import socket
        from Shared.bull_llm.gpu_lab.transport import owns_local_listener
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); sock.listen()
            self.assertTrue(owns_local_listener(os.getpid(),sock.getsockname()[1]))
            self.assertFalse(owns_local_listener(0,sock.getsockname()[1]))
        with socket.socket() as sock:
            sock.bind(('0.0.0.0',0)); sock.listen()
            self.assertFalse(owns_local_listener(os.getpid(),sock.getsockname()[1]))

    def test_idle_unknown_and_foreign_process(self):
        from Shared.bull_llm.gpu_lab.runner import background_status
        self.assertEqual(background_status({},[A]),'unknown')
        self.assertEqual(background_status(dict(process_query_available=True,processes=[dict(uuid=A,pid=99)]),[A]),'busy')

    def test_pause_resume_preserves_complete_pairs(self):
        from Shared.bull_llm.gpu_lab.runner import new_result, execute
        inventory=[dict(uuid=A,name='Fixture A',memory_mib='12288',driver='999')]
        class FakeWorker:
            active=False
            def rpc(self,action): return dict(gpus=inventory)
            def sample(self):
                return dict(process_query_available=True,gpus=[],owned_pids=[1],processes=[dict(uuid=A,pid=1)] if self.active else [])
            def samples_since(self,start): return [self.sample()]
        class FakeSession:
            count=0; fail=True; version='fixture'; launch=dict(environment=c.process_environment([A],20000))
            def __init__(self,worker,*args): self.worker=worker
            def __enter__(self): self.worker.active=True; return self
            def __exit__(self,*args): self.worker.active=False
            def api(self,path,*args):
                return dict(models=[dict(name='fixture:latest',digest='fixture',size=100,size_vram=50,context_length=4096)])
            def generate(self,*args):
                FakeSession.count+=1
                if FakeSession.fail and FakeSession.count==3: raise ConnectionResetError('FIXTURE_DISCONNECT')
                return dict(decode_tok_s=10,prefill_tok_s=20,wall_s=1,ttft_client_s=.1,load_class='warm')
        cfg=self.config(); cfg.update(devices=[[A]],repeats=2)
        result=new_result(cfg,inventory); worker=FakeWorker()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'result.json'
            result=execute(worker,result,path,session_type=FakeSession)
            self.assertEqual(result['status'],'paused'); self.assertEqual(len(result['completed']),1)
            original=copy.deepcopy(result['completed'][0]); FakeSession.fail=False
            result=execute(worker,result,path,session_type=FakeSession)
            self.assertEqual(result['status'],'completed'); self.assertEqual(len(result['completed']),2)
            self.assertEqual(result['completed'][0],original); self.assertEqual(len(result['attempts']),1)
            self.assertEqual(FakeSession.count,5)

    def test_navigation_gpu_does_not_require_running_primary_ollama(self):
        from Apps._bootstrap import load_compat_core
        from Shared.bull_llm.terminal_ui import experimental_menu
        core=load_compat_core()
        with patch.object(core,'clear_console'), patch.object(core,'read_user_input',return_value='2'), contextlib.redirect_stdout(io.StringIO()):
            guard=unittest.mock.Mock(side_effect=AssertionError('Do not probe global Ollama'))
            self.assertEqual(experimental_menu(core),'/gpu')
            guard.assert_not_called()

    @unittest.skipUnless(os.name=='nt','Windows Job Object integration')
    def test_windows_worker_real_process_tree_and_api(self):
        from Shared.bull_llm.gpu_lab.transport import Worker, Session
        from Shared.bull_llm.gpu_lab.runner import new_result, execute
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            cp=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(root/'Tests/Build-Gpu-Lab-Fixture.ps1'),'-Destination',tmp],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(cp.returncode,0,cp.stderr.decode(errors='replace'))
            core=types.SimpleNamespace(ACTIVE_BACKEND='ollama',load_backend_settings=lambda:dict(target_mode='local'))
            cfg=self.config(); cfg.update(devices=[[A,B]],repeats=1)
            original=os.environ.get('CUDA_VISIBLE_DEVICES')
            with patch.dict(os.environ,{'PATH':tmp+os.pathsep+os.environ['PATH']}), Worker(core) as worker:
                inventory=worker.rpc('inventory')['gpus']; self.assertEqual(len(inventory),2)
                private=dict(executable=str(Path(tmp)/'ollama_fixture.exe'))
                result=new_result(cfg,inventory)
                result=execute(worker,result,Path(tmp)/'result.json',private)
                self.assertEqual(result['status'],'completed',result)
                self.assertEqual(len(result['completed'][0]['phases']),2)
                phase=result['completed'][0]['phases'][0]
                self.assertTrue(phase['comparable'],phase)
                self.assertEqual(phase['metrics']['decode_tok_s'],80)
                after=worker.sample()
                self.assertEqual(after['processes'],[], 'Job must stop server AND fixture child processes')
                # Abrupt supervisor death must also close its non-inherited Job handle.
                session=Session(worker,[A,B],private).__enter__()
                session.generate(c.request(cfg,result['jobs'][0]),30)
                owned=worker.sample()['owned_pids']; self.assertGreaterEqual(len(owned),2)
                import ctypes
                from ctypes import wintypes
                dll=ctypes.WinDLL('kernel32',use_last_error=True)
                dll.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; dll.OpenProcess.restype=wintypes.HANDLE
                dll.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
                dll.CloseHandle.argtypes=[wintypes.HANDLE]
                handles=[dll.OpenProcess(0x100000,False,pid) for pid in owned]
                try:
                    self.assertTrue(all(handles)); worker.proc.kill(); worker.proc.wait(timeout=5)
                    for handle in handles: self.assertEqual(dll.WaitForSingleObject(handle,5000),0)
                finally:
                    for handle in handles:
                        if handle: dll.CloseHandle(handle)
                session.__exit__(RuntimeError,None,None)
            self.assertEqual(os.environ.get('CUDA_VISIBLE_DEVICES'),original)


def run_suite():
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__, fromlist=['*'])))
    if not result.wasSuccessful(): raise AssertionError('GPU Lab regression failed')
    return result.testsRun


if __name__ == '__main__': run_suite()
