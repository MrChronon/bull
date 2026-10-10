"""Install the hash-checked native client only after Setup's verification gate."""
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import time

PAYLOAD = 'Setup/BULL.launcher.bin'


def verified_payload(root):
    root = Path(root)
    manifest = json.loads((root/'RELEASE_MANIFEST.json').read_text(encoding='utf-8-sig'))
    data = (root/PAYLOAD).read_bytes()
    expected = manifest.get('files', {}).get(PAYLOAD)
    offset = struct.unpack_from('<I', data, 60)[0] if len(data) >= 64 else 0
    if (not isinstance(expected, str) or hashlib.sha256(data).hexdigest() != expected or
            not 64 <= len(data) <= 256*1024 or data[:2] != b'MZ' or
            offset < 64 or data[offset:offset+4] != b'PE\0\0'):
        raise ValueError('CLIENT_LAUNCHER_INTEGRITY_FAILED')
    return data


def materialize(root):
    root = Path(root)
    data = verified_payload(root)
    destination = root/'BULL.exe'
    with tempfile.NamedTemporaryFile(prefix='bull-launcher-', suffix='.tmp', dir=root, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        for attempt in range(6):
            try:
                os.replace(temporary, destination)
                return destination
            except OSError as error:
                if getattr(error, 'winerror', None) not in (5,32,33) or attempt == 5:raise
                time.sleep(0.05 * 2**attempt)
    finally:
        temporary.unlink(missing_ok=True)


def verify_installed(root):
    root = Path(root)
    data = verified_payload(root)
    executable = root/'BULL.exe'
    state = root/'Runtime/installation_state.json'
    complete = state.is_file() and json.loads(state.read_text(encoding='utf-8-sig')).get('status') == 'complete'
    if complete and not executable.is_file():raise ValueError('INSTALLED_CLIENT_LAUNCHER_MISSING')
    if executable.exists() and executable.read_bytes() != data:raise ValueError('INSTALLED_CLIENT_LAUNCHER_MODIFIED')
