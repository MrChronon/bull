import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


class RuntimeFollowupTests(unittest.TestCase):
    core=None

    def test_gpu_keeps_resource_counters_without_temperature_or_power(self):
        row=self.core.GpuSampler.parse_line('5120, 12288, 75, [N/A], [N/A]')
        sampler=self.core.GpuSampler(); sampler.samples=[row]
        summary=sampler.summary()
        self.assertEqual(summary['vram_peak_mib'],5120)
        self.assertEqual(summary['gpu_util_avg'],75)
        self.assertIsNone(summary['gpu_power_avg_w'])

    def test_gpu_nonfinite_or_missing_counters_are_not_zero(self):
        self.assertIsNone(self.core.GpuSampler.parse_line('N/A,N/A,N/A,N/A,N/A'))
        row=self.core.GpuSampler.parse_line('nan,12288,inf,N/A,N/A')
        self.assertIsNone(row['vram_used_mib']); self.assertIsNone(row['gpu_util'])

    def test_known_no_think_model_uses_fast_without_changing_benchmark_policy(self):
        with patch.object(self.core,'model_capabilities',return_value={'completion'}):
            self.assertIs(self.core.chat_think_value('ordinary',True)[0],False)
            self.assertIs(self.core.normalize_think_value('ordinary',True)[0],True)

    def test_unknown_capabilities_do_not_fabricate_support(self):
        with patch.object(self.core,'model_capabilities',return_value=None):
            self.assertIs(self.core.chat_think_value('ordinary',True)[0],True)

    def test_explicit_400_has_one_chat_only_fallback(self):
        cfg={'think':True}; session={'tools_mode':'off'}
        with patch.object(self.core,'chat_agent',side_effect=[RuntimeError('Ollama HTTP 400: does not support thinking'),('ok','',{})]) as agent, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.core.chat_agent_with_capabilities([],cfg,True,session),('ok','',{}))
        self.assertEqual(agent.call_count,2); self.assertIs(cfg['think'],False)
        self.assertEqual(session['run_mode'],'fast')

    def test_unrelated_error_or_tool_agent_is_not_retried(self):
        for message,tools in [('HTTP 401: does not support thinking','off'),('HTTP 400: other error','off'),('HTTP 400: does not support thinking','on')]:
            with patch.object(self.core,'chat_agent',side_effect=RuntimeError(message)) as agent:
                with self.assertRaises(RuntimeError):self.core.chat_agent_with_capabilities([],{'think':True},True,{'tools_mode':tools})
                self.assertEqual(agent.call_count,1)

    def test_reap_kills_waits_and_closes_pipes_after_timeout(self):
        from Shared.bull_llm.owned_processes import own,reap
        process=Mock(); process.poll.return_value=None
        process.wait.side_effect=[subprocess.TimeoutExpired('fixture',3),0]
        own(process); reap(process)
        process.kill.assert_called_once(); self.assertEqual(process.wait.call_count,2)
        process.stdout.close.assert_called_once(); process.stderr.close.assert_called_once()

    def test_real_owned_child_releases_directory_without_stopping_unrelated_child(self):
        from Shared.bull_llm.owned_processes import own,close_all,reap
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); target=root/'held.txt'; target.write_text('fixture')
            owned=own(subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
            other=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
            try:
                close_all(); self.assertIsNotNone(owned.poll()); self.assertIsNone(other.poll())
                self.assertTrue(owned.stdout.closed); target.unlink(); self.assertFalse(target.exists())
            finally:reap(owned); reap(other)

    def test_launcher_is_verified_and_appears_only_after_materialization(self):
        from Shared.bull_llm.client_launcher import PAYLOAD,materialize,verify_installed
        source=Path(self.core.__file__).parent/PAYLOAD
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'Setup').mkdir()
            data=source.read_bytes(); (root/PAYLOAD).write_bytes(data)
            (root/'RELEASE_MANIFEST.json').write_text(json.dumps({'files':{PAYLOAD:hashlib.sha256(data).hexdigest()}}))
            verify_installed(root); self.assertFalse((root/'BULL.exe').exists())
            materialize(root); self.assertEqual((root/'BULL.exe').read_bytes(),data)
            (root/'Runtime').mkdir()
            (root/'Runtime/installation_state.json').write_text(json.dumps({'status':'complete'}))
            verify_installed(root)
            (root/'BULL.exe').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_installed(root)

    def test_corrupt_payload_never_creates_executable(self):
        from Shared.bull_llm.client_launcher import PAYLOAD,materialize
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'Setup').mkdir(); (root/PAYLOAD).write_bytes(b'MZbad')
            (root/'RELEASE_MANIFEST.json').write_text(json.dumps({'files':{PAYLOAD:'0'*64}}))
            with self.assertRaises(ValueError):materialize(root)
            self.assertFalse((root/'BULL.exe').exists())

    def test_failed_installation_state_removes_only_new_unchanged_launcher(self):
        from Shared.bull_llm.installer import InstallationServices
        for existing in (False,True):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory); executable=root/'BULL.exe'
                if existing:executable.write_bytes(b'fixture')
                service=InstallationServices(Mock(__file__=str(root/'core.py')))
                def create(_):
                    executable.write_bytes(b'fixture')
                    return executable
                with patch('Shared.bull_llm.client_launcher.materialize',side_effect=create), \
                     patch('Shared.bull_llm.client_launcher.verified_payload',return_value=b'fixture'), \
                     patch('Shared.bull_llm.storage.atomic_json',side_effect=OSError('fixture')):
                    with self.assertRaises(OSError):service.complete({'ok':True,'summary':'666/666'},{'connection':False,'packs':{'count':0}})
                self.assertEqual(executable.exists(),existing)

    def test_failed_completion_does_not_remove_concurrently_changed_launcher(self):
        from Shared.bull_llm.installer import InstallationServices
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); executable=root/'BULL.exe'
            service=InstallationServices(Mock(__file__=str(root/'core.py')))
            def create(_):
                executable.write_bytes(b'fixture')
                return executable
            def fail(*args,**kwargs):
                executable.write_bytes(b'changed by another writer')
                raise OSError('fixture')
            with patch('Shared.bull_llm.client_launcher.materialize',side_effect=create), \
                 patch('Shared.bull_llm.client_launcher.verified_payload',return_value=b'fixture'), \
                 patch('Shared.bull_llm.storage.atomic_json',side_effect=fail):
                with self.assertRaises(OSError):service.complete({'ok':True,'summary':'666/666'},{'connection':False,'packs':{'count':0}})
            self.assertEqual(executable.read_bytes(),b'changed by another writer')

    def test_pinned_known_hosts_path_with_spaces_is_quoted_without_disabling_trust(self):
        with tempfile.TemporaryDirectory(prefix='bull ssh space ') as directory:
            known=Path(directory)/'known_hosts'; known.write_text('public fixture')
            endpoint={'host':'example.org','port':22,'user':'example','known_hosts_file':str(known)}
            with patch.object(self.core,'remote_access_settings',return_value={}):
                arguments=self.core._ssh_base_args(endpoint,batch=True)
            self.assertIn('StrictHostKeyChecking=yes',arguments)
            self.assertIn('BatchMode=yes',arguments)
            self.assertIn('UserKnownHostsFile="'+known.as_posix()+'"',arguments)
            self.assertNotIn('StrictHostKeyChecking=no',arguments)

    def test_missing_resources_all_have_explicit_warning_without_fake_zero(self):
        record={'record_schema_version':4,'execution_status':'ok','identity':{'benchmark':'case','model':'model'},
                'score':{'native':{'value':1},'final':{'value':1}},
                'primary':{'task_completed':True,'eval_rate':20},
                'telemetry':{'gpu':{'samples':0,'status':'ssh_host_key_verification_failed'},
                             'system':{'samples':0,'status':'ssh_host_key_verification_failed'}}}
        out=io.StringIO()
        with patch.object(self.core,'get_language',return_value='ru'),contextlib.redirect_stdout(out):
            self.core.render_benchmark_run_summary(record,1,1)
        for counter in ('GPU','VRAM','CPU','RAM'):
            self.assertIn(counter+' N/A',out.getvalue())
            self.assertIn(counter+' недоступен',out.getvalue())
        self.assertIn('ssh_host_key_verification_failed',out.getvalue())

    def test_ssh_failure_classification_does_not_publish_private_error_text(self):
        self.assertEqual(self.core.resource_sampler_failure('No host key is known for private endpoint.'),'ssh_host_key_verification_failed')
        self.assertEqual(self.core.resource_sampler_failure('Permission denied (publickey).'),'ssh_authentication_failed')


def run_suite(core):
    RuntimeFollowupTests.core=core
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeFollowupTests))
    if not result.wasSuccessful():raise AssertionError('Runtime follow-up regression failed')
    return result.testsRun
