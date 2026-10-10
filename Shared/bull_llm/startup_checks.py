"""Essential offline boot checks; full regression remains a separate release gate."""
from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys
import tempfile

def require(condition, detail):
    if not condition: raise RuntimeError(detail)

def verify_files(root, manifest, names):
    root = Path(root).resolve()
    require(bool(names), 'Required manifest group is empty')
    for name in names:
        path = (root / name).resolve()
        require(path.is_relative_to(root), 'Manifest path escapes bundle')
        expected = manifest['files'].get(name)
        require(isinstance(expected, str) and len(expected) == 64, 'Missing manifest digest: ' + name)
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                'Bundle integrity failure: ' + name)

def import_modules(*names):
    for name in names: importlib.import_module('Shared.bull_llm.' + name)

def checks(root, version, client_name):
    root = Path(root)
    manifest = json.loads((root / 'RELEASE_MANIFEST.json').read_text(encoding='utf-8-sig'))
    require(isinstance(manifest.get('files'), dict), 'Invalid release manifest')
    def version_check():
        require(manifest.get('version') == version, 'Release/client version mismatch')
        verify_files(root, manifest, [client_name, 'Tests/startup_smoke.py', 'Setup/BULL.launcher.bin',
            'Setup.exe', 'Setup.ps1', 'BULL-v0.29.0.1.ps1', 'Tools/Update-BULL-Shortcuts.ps1'])
        from .client_launcher import verify_installed
        verify_installed(root)
    def group(prefix):
        names = [p.relative_to(root).as_posix() for p in (root / prefix).rglob('*')
                 if p.is_file() and p.suffix in ('.py', '.json') and '__pycache__' not in p.parts]
        names += [name for name in manifest['files'] if name.startswith(prefix + '/') and name not in names]
        verify_files(root, manifest, names)
    def write_probe():
        from .storage import atomic_json
        with tempfile.TemporaryDirectory(prefix='bull-boot-') as directory:
            path = Path(directory) / 'probe.json'
            atomic_json(path, {'ok': True})
            require(json.loads(path.read_text()) == {'ok': True}, 'Atomic JSON roundtrip failed')
    def telemetry_protocol():
        from .system_telemetry import parse_sample
        require(parse_sample('{"cpu_util":12.5,"ram_used_bytes":1,"ram_total_bytes":2}')['cpu_util'] == 12.5,
                'Resource protocol invalid')
    def schema_check():
        schema = json.loads((root / 'Schemas/bull_benchmark_pack_manifest_v1.schema.json').read_text(encoding='utf-8'))
        require(schema.get('type') == 'object' and schema.get('additionalProperties') is False, 'Pack schema invalid')
    def language_check():
        catalog = json.loads((root / 'Assets/Localization/ui.en.json').read_text(encoding='utf-8'))
        require(catalog.get('schema') == 'bull-ui-catalog' and catalog.get('translations', {}).get('Наборы тестов') == 'Test packs', 'UI language catalog invalid')
    def artwork_check():
        for prefix in ('splash', 'splash-matrix'):
            data = (root / f'Assets/Brand/{prefix}-{version}.png').read_bytes()
            require(len(data) >= 24 and data[:8] == b'\x89PNG\r\n\x1a\n', 'Splash PNG invalid')
            width, height = struct.unpack('>II', data[16:24])
            require(500 <= width <= 4096 and 500 <= height <= 4096, 'Splash dimensions invalid')
    return [
        ('Python compatibility', lambda: require(sys.version_info >= (3, 10), 'Python 3.10+ required')),
        ('Release version and client integrity', version_check),
        ('Engine module integrity', lambda: group('Shared')),
        ('Application entrypoint integrity', lambda: group('Apps')),
        ('Schema integrity', lambda: group('Schemas')),
        ('Interface and splash asset integrity', lambda: verify_files(root, manifest,
            ['Assets/Localization/ui.en.json', f'Assets/Brand/splash-{version}.png',
             f'Assets/Brand/splash-matrix-{version}.png', 'Assets/Brand/brand-lock.json',
             'Assets/Brand/bull-mark-console-48.ansi.b64', 'Assets/Brand/bull-icon-matrix.ico',
             'Assets/Brand/bull-setup.ico'])),
        ('Runtime adapters', lambda: import_modules('runtime.adapters', 'runtime.events')),
        ('Storage and language modules', lambda: import_modules('storage', 'i18n', 'presentation')),
        ('Backend transport modules', lambda: import_modules('backends', 'http_transport')),
        ('Evidence contracts', lambda: import_modules('core.contracts', 'evidence')),
        ('Pack library and selection', lambda: import_modules('evaluation.registry', 'evaluation.pack_library', 'evaluation.pack_selection')),
        ('Author workshop', lambda: import_modules('evaluation.author_workshop', 'author_workshop_ui')),
        ('Results and navigation modules', lambda: import_modules('results_report', 'startup_window', 'terminal_ui', 'installer', 'readiness', 'pack_download', 'diagnostics_ui')),
        ('CPU/RAM sample protocol', telemetry_protocol),
        ('Atomic storage roundtrip', write_probe),
        ('Pack manifest schema', schema_check),
        ('English interface catalog', language_check),
        ('Startup artwork format', artwork_check),
    ]

def run(root, version, client_name):
    suite = checks(root, version, client_name)
    print('BULL_STARTUP_TOTAL\t' + str(len(suite)), flush=True)
    for index, (name, check) in enumerate(suite, 1):
        print('BULL_STARTUP_TEST\t' + name, flush=True)
        check()
        print('BULL_STARTUP_COMPLETE\t' + str(index), flush=True)
    print(f'PASS {len(suite)}/{len(suite)}', flush=True)
