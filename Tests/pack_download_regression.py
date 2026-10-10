"""Bounded downloads with fake HTTPS responses; never contacts a server."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from Shared.bull_llm.pack_download import archive_source, checked_url, download_pack, PackRedirects


class DownloadTests(unittest.TestCase):
    def response(self, body=b'zip', length='3', url='https://example.invalid/tests.zip'):
        response = io.BytesIO(body)
        response.headers = {} if length is None else {'Content-Length':length}
        response.geturl = lambda:url
        return response

    def fetch(self, destination, response, **kwargs):
        with patch('Shared.bull_llm.pack_download.urllib.request.build_opener',
                   return_value=Mock(open=Mock(return_value=response))):
            return download_pack('https://example.invalid/tests.zip',destination,**kwargs)

    def test_https_preserves_query_but_removes_fragment(self):
        self.assertEqual(checked_url('https://example.invalid/pack?signature=test#part'),
                         'https://example.invalid/pack?signature=test')

    def test_unsafe_urls_fail_before_network(self):
        for url in ('http://host/p.zip','file:///p.zip','https://user:secret@host/p.zip',
                    'https://host:99999/p.zip','https:///p.zip','https://host/\nheader',None):
            with self.subTest(url=url), self.assertRaises(ValueError):checked_url(url)

    def test_redirect_cannot_downgrade_to_http_or_add_credentials(self):
        for url in ('http://host/p.zip','https://user:password@host/p.zip'):
            with self.assertRaises(ValueError):PackRedirects().redirect_request(None,None,302,'',{},url)

    def test_complete_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip'
            self.assertEqual(self.fetch(path,self.response()),path)
            self.assertEqual(path.read_bytes(),b'zip')

    def test_unknown_size_is_still_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip'
            self.fetch(path,self.response(length=None),max_bytes=3)
            self.assertEqual(path.read_bytes(),b'zip')

    def test_oversized_header_fails_without_creating_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip'
            with self.assertRaises(ValueError):self.fetch(path,self.response(length='100'),max_bytes=3)
            self.assertFalse(path.exists())

    def test_stream_cannot_bypass_limit_with_no_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip'
            with self.assertRaises(ValueError):self.fetch(path,self.response(b'1234',None),max_bytes=3)
            self.assertFalse(path.exists())

    def test_truncated_body_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip'
            with self.assertRaises(ValueError):self.fetch(path,self.response(length='4'))
            self.assertFalse(path.exists())

    def test_empty_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip'
            with self.assertRaises(ValueError):self.fetch(path,self.response(b'',None))
            self.assertFalse(path.exists())

    def test_existing_file_is_never_overwritten_or_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip';path.write_bytes(b'owned')
            with self.assertRaises(FileExistsError):self.fetch(path,self.response())
            self.assertEqual(path.read_bytes(),b'owned')

    def test_io_failure_removes_own_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip'
            response = self.response();response.read = Mock(side_effect=[b'x',OSError('fixture')])
            with self.assertRaises(OSError):self.fetch(path,response)
            self.assertFalse(path.exists())

    def test_total_deadline_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp, patch('Shared.bull_llm.pack_download.time.monotonic',side_effect=[0,61]):
            path = Path(tmp)/'pack.zip'
            with self.assertRaises(ValueError):self.fetch(path,self.response())
            self.assertFalse(path.exists())

    def test_invalid_limits_and_timeout_are_rejected(self):
        for options in ({'max_bytes':0},{'max_bytes':True},{'max_bytes':70*1024**2},
                        {'timeout':0},{'timeout':float('nan')},{'timeout':601}):
            with self.assertRaises(ValueError):download_pack('https://host/p.zip','unused',**options)

    def test_local_source_never_downloads(self):
        with patch('Shared.bull_llm.pack_download.download_pack',side_effect=AssertionError('network')):
            with archive_source('"C:/tests/pack.zip"') as path:self.assertEqual(path,Path('C:/tests/pack.zip'))

    def test_url_temporary_directory_is_cleaned(self):
        def fake(source,destination):destination.write_bytes(b'zip');return destination
        with patch('Shared.bull_llm.pack_download.download_pack',side_effect=fake):
            with archive_source('https://host/p.zip') as path:
                directory = path.parent;self.assertTrue(path.exists())
            self.assertFalse(directory.exists())

    def test_untrusted_final_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'pack.zip'
            with self.assertRaises(ValueError):self.fetch(path,self.response(url='http://host/p.zip'))
            self.assertFalse(path.exists())


def run_suite():
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(DownloadTests))
    if not result.wasSuccessful():raise AssertionError('Pack download regression failed')
    return result.testsRun
