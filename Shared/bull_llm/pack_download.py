"""Explicit bounded HTTPS download, followed by the existing data-only ZIP gate."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import tempfile
import time
import math
import urllib.parse
import urllib.request

from .evaluation.pack_library import ZipLimits


def checked_url(value):
    if not isinstance(value,str) or not 1 <= len(value) <= 4096 or any(ord(c) < 33 for c in value):
        raise ValueError('PACK_DOWNLOAD_URL')
    try:
        parts = urllib.parse.urlsplit(value)
        port = parts.port
    except ValueError:
        raise ValueError('PACK_DOWNLOAD_URL') from None
    if (parts.scheme != 'https' or not parts.hostname or parts.username is not None or
            parts.password is not None or (port is not None and not 1 <= port <= 65535)):
        raise ValueError('PACK_DOWNLOAD_HTTPS_REQUIRED')
    return urllib.parse.urlunsplit((parts.scheme,parts.netloc,parts.path,parts.query,''))


class PackRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = 5
    max_repeats = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def download_pack(source, destination, *, max_bytes=None, timeout=60):
    source = checked_url(source)
    limit = ZipLimits().max_archive_bytes if max_bytes is None else max_bytes
    if type(limit) is not int or not 0 < limit <= ZipLimits().max_archive_bytes:
        raise ValueError('PACK_DOWNLOAD_LIMIT')
    if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0 < timeout <= 600:
        raise ValueError('PACK_DOWNLOAD_TIMEOUT')
    target = Path(destination)
    deadline = time.monotonic() + timeout
    opener = urllib.request.build_opener(PackRedirects())
    request = urllib.request.Request(source,headers={'User-Agent':'BULL-Pack-Installer/1','Accept':'application/zip'})
    created = False
    try:
        with opener.open(request,timeout=min(15,timeout)) as response:
            checked_url(response.geturl())
            length = response.headers.get('Content-Length')
            if length is not None and (not str(length).isdigit() or int(length) > limit):
                raise ValueError('PACK_DOWNLOAD_TOO_LARGE')
            received = 0
            with target.open('xb') as stream:
                created = True
                while True:
                    if time.monotonic() > deadline: raise ValueError('PACK_DOWNLOAD_TIMEOUT')
                    chunk = response.read(min(256 * 1024,limit - received + 1))
                    if not chunk: break
                    received += len(chunk)
                    if received > limit: raise ValueError('PACK_DOWNLOAD_TOO_LARGE')
                    stream.write(chunk)
            if not received or (length is not None and received != int(length)):
                raise ValueError('PACK_DOWNLOAD_INCOMPLETE')
        return target
    except Exception:
        # Only remove a file created by this invocation; never clobber a caller file.
        if created and target.exists() and not target.is_symlink():target.unlink(missing_ok=True)
        raise


@contextmanager
def archive_source(source):
    value = str(source).strip().strip('"')
    if '://' not in value:
        yield Path(value)
        return
    checked_url(value)
    with tempfile.TemporaryDirectory(prefix='bull-pack-download-') as directory:
        yield download_pack(value,Path(directory)/'pack.zip')
