"""Explicit SSH onboarding. A per-user address book is opt-in, not an auto-connect policy.

Only references to private keys are retained; their bytes are never read or copied.
The existing transport and its strict host-key verification remain authoritative.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re

from .i18n import localized_print as print
import shlex
import subprocess
import uuid
from pathlib import Path

from .storage import atomic_json
from .presentation import terminal_text
from .terminal_ui import selection, pause

FIELDS = ('id', 'name', 'route', 'transport', 'endpoint', 'backend', 'host_public_key', 'host_key_fingerprint')


def vault_dir():
    # No directory is created until the user explicitly chooses to remember a server.
    base = Path(os.environ['LOCALAPPDATA']) if os.environ.get('LOCALAPPDATA') else Path.home() / '.local/share'
    return base / 'BULL' / 'connections'


def read_document(path):
    with Path(path).open('rb') as stream:
        data = stream.read(256 * 1024 + 1)
    if len(data) > 256 * 1024:
        raise ValueError('Файл настроек слишком большой (максимум 256 KiB).')
    document = json.loads(data.decode('utf-8-sig'))
    if not isinstance(document, dict):
        raise ValueError('Ожидается JSON-объект.')
    return document


def clean_entry(core, entry):
    raw = {key: entry.get(key) for key in FIELDS}
    raw.update(schema='local-llm-connection', version=1)
    result = core._validate_connection_bundle(raw)
    result['identity_file'] = str(entry.get('identity_file') or '')
    return result


def saved_connections(core):
    result = []
    for path in sorted(vault_dir().glob('*.json'))[:100]:
        try:
            result.append(clean_entry(core, read_document(path)))
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return result


def same_server(a, b):
    return (a.get('endpoint') == b.get('endpoint') and
            a.get('backend') == b.get('backend') and
            a.get('host_key_fingerprint') == b.get('host_key_fingerprint'))


def remember_connection(core, entry):
    entry = clean_entry(core, entry)
    path = vault_dir() / (entry['id'] + '.json')
    if path.exists() and not same_server(read_document(path), entry):
        raise ValueError('Сохранённый сервер с этим ID отличается. Автоматическая замена запрещена.')
    atomic_json(path, entry)
    return path


def private_key_path(value):
    path = Path(value.strip().strip('"')).expanduser().resolve()
    if not path.is_file() or path.suffix.casefold() == '.pub':
        raise ValueError('Нужен существующий приватный ключ, не .pub. Ключ не копируется в программу.')
    return path


def _alias_name(value):
    alias = str(value or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', alias):
        raise ValueError('SSH-алиас: 1–128 символов A-Z, a-z, 0-9, точка, подчёркивание или дефис.')
    return alias


def _ssh_path(value):
    raw = str(value or '').strip().strip('"')
    raw = raw.replace('%d', str(Path.home()))
    raw = os.path.expandvars(raw)
    if '%' in raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.home() / path
    return path.resolve()


def configured_ssh_aliases():
    """List simple aliases from the primary user config; Includes still work by typing."""
    path = Path.home() / '.ssh' / 'config'
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if len(data) > 256 * 1024:
        return []
    result = []
    for raw_line in data.decode('utf-8-sig', errors='replace').splitlines():
        line = raw_line.split('#', 1)[0].strip()
        if not line or not line.casefold().startswith('host '):
            continue
        try:
            names = shlex.split(line[5:], posix=False)
        except ValueError:
            continue
        for name in names:
            name = name.strip('"')
            if not any(char in name for char in '*?!') and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', name):
                if name not in result:
                    result.append(name)
    return result[:20]


def resolve_ssh_alias(core, value):
    """Resolve a direct key-based OpenSSH alias without connecting to the server."""
    alias = _alias_name(value)
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    result = subprocess.run(
        ['ssh', '-G', '--', alias], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8,
        creationflags=flags,
    )
    if result.returncode or len(result.stdout) > 256 * 1024:
        detail = core._decode_subprocess_output(result.stderr).strip()
        raise ValueError('OpenSSH не смог прочитать алиас.' + (f' {detail}' if detail else ''))
    values = {}
    for line in core._decode_subprocess_output(result.stdout).splitlines():
        key, separator, raw = line.partition(' ')
        if separator:
            values.setdefault(key.casefold(), []).append(raw.strip())
    for option in ('proxycommand', 'proxyjump'):
        configured = [item for item in values.get(option, []) if item and item.casefold() != 'none']
        if configured:
            raise ValueError(f'Алиас использует {option}. В быстром режиме поддерживается прямое SSH-подключение; используйте ручной мастер.')
    host = core._validate_ssh_host((values.get('hostname') or [''])[-1])
    user = core._validate_ssh_user((values.get('user') or [''])[-1])
    if not user:
        raise ValueError('В SSH-алиасе не определён User. Добавьте его в ~/.ssh/config.')
    port = int((values.get('port') or ['22'])[-1])
    if not 1 <= port <= 65535:
        raise ValueError('SSH-алиас вернул порт вне диапазона 1..65535.')
    identities = []
    for raw in values.get('identityfile', []):
        path = _ssh_path(raw)
        if path and path.is_file() and path.suffix.casefold() != '.pub' and path not in identities:
            identities.append(path)
    if not identities:
        raise ValueError('Для алиаса не найден приватный IdentityFile. Добавьте IdentityFile в ~/.ssh/config или откройте инструкцию по ключам.')
    known_hosts = []
    for raw in values.get('userknownhostsfile', []):
        try:
            parts = shlex.split(raw, posix=False)
        except ValueError:
            parts = raw.split()
        for item in parts:
            path = _ssh_path(item)
            if path and path not in known_hosts:
                known_hosts.append(path)
    for fallback in (Path.home() / '.ssh/known_hosts', Path.home() / '.ssh/known_hosts2'):
        if fallback not in known_hosts:
            known_hosts.append(fallback)
    return {
        'alias': alias, 'host': host, 'user': user, 'port': port,
        'identity_file': str(identities[0]), 'known_hosts_files': known_hosts,
    }


def known_host_key_matches(host_public_key, host, port, known_hosts_files):
    """Check the scanned key against OpenSSH trust, including hashed host entries."""
    expected = ' '.join(str(host_public_key).split()[:2])
    marker = str(host) if int(port) == 22 else f'[{host}]:{int(port)}'
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    for path in known_hosts_files:
        path = Path(path)
        if not path.is_file():
            continue
        try:
            result = subprocess.run(
                ['ssh-keygen', '-F', marker, '-f', str(path)],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=5, creationflags=flags,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode or len(result.stdout) > 256 * 1024:
            continue
        for line in result.stdout.decode('ascii', errors='ignore').splitlines():
            parts = line.split()
            for index, part in enumerate(parts[:-1]):
                if part in ('ssh-ed25519', 'ecdsa-sha2-nistp256', 'ssh-rsa'):
                    if part + ' ' + parts[index + 1] == expected:
                        return True
    return False


def install_entry(core, entry, remember=False):
    """Stage a validated public bundle; delegate actual activation to existing code."""
    entry = clean_entry(core, entry)
    key = private_key_path(entry['identity_file'])
    for old in core.connection_entries():
        if old.get('id') == entry['id'] and not same_server(old, entry):
            raise ValueError('Существующее подключение отличается. Старый ключ сервера не будет перезаписан.')
    if remember:
        path = vault_dir() / (entry['id'] + '.json')
        if path.exists() and not same_server(read_document(path), entry):
            raise ValueError('ID уже занят другим сохранённым сервером. Замена запрещена.')
    raw = {field: entry[field] for field in FIELDS}
    raw.update(schema='local-llm-connection', version=1)
    staged = core.connection_store_path().parent / ('connection-import-' + uuid.uuid4().hex + '.json')
    try:
        atomic_json(staged, raw)
        imported = core.import_connection_bundle(staged, str(key), activate=True)
    finally:
        staged.unlink(missing_ok=True)
    if remember:
        remember_connection(core, imported)
    return imported


def scan_host_key(core, host, port):
    host = core._validate_ssh_host(host)
    port = int(port)
    if not 1 <= port <= 65535:
        raise ValueError('Порт должен быть от 1 до 65535.')
    # No shell, credentials or SSH login; the returned key is UNTRUSTED until compared independently.
    result = subprocess.run(['ssh-keyscan', '-T', '5', '-t', 'ed25519', '-p', str(port), host],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode or len(result.stdout) > 16384:
        raise ValueError('Не получен ключ сервера. Проверьте адрес/порт. Можно импортировать Connection JSON.')
    keys = set()
    for line in result.stdout.decode('ascii', errors='strict').splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] == 'ssh-ed25519':
            keys.add(parts[1] + ' ' + parts[2])
    if len(keys) != 1:
        raise ValueError('Сервер не вернул один однозначный Ed25519 ключ. Используйте Connection JSON.')
    key = keys.pop()
    blob = base64.b64decode(key.split()[1], validate=True)
    fingerprint = 'SHA256:' + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')
    return key, fingerprint


class Cancelled(Exception):
    pass


def ask(core, title, default='', required=False):
    while True:
        suffix = f' [{default}]' if default else ''
        value = core.read_user_input(f'{title}{suffix} › ').strip()
        if value == '0': raise Cancelled()
        if value or default: return value or str(default)
        if not required: return ''
        print('Поле обязательно. 0 — отменить настройку без изменений.')


def confirm_install(core, entry):
    endpoint = entry['endpoint']
    core.ui_header('Проверить и сохранить', 'Подключения / Итог')
    print(terminal_text(f"  {entry['name']}\n  SSH: {endpoint['user']}@{endpoint['host']}:{endpoint['port']}"))
    print(f"  Ollama на сервере: 127.0.0.1:{entry['backend']['remote_port']}")
    print(terminal_text(f"  Ключ: {entry['identity_file']}\n  Сервер: {entry['host_key_fingerprint']}"))
    print('  Сервер и роутер не изменяются. При недоступности настройки сохранятся.')
    core.ui_menu_item('1', 'Сохранить для следующих версий и подключиться', 'Адрес и путь к ключу — в личной папке Windows; ключ не копируется')
    core.ui_menu_item('2', 'Подключиться только из этого билда', 'Настройки останутся в Runtime этой копии программы')
    core.ui_menu_item('0', 'Отменить без изменений')
    value = core.read_user_input('Выбор › ').strip()
    if value not in ('1', '2'):
        return None
    result = install_entry(core, entry, remember=value == '1')
    core.green(); print('Настройки сохранены. Проверяю связь с сервером…'); core.white()
    return result


def new_ssh_alias_connection(core):
    """Create the normal pinned BULL connection from one OpenSSH alias."""
    try:
        core.ui_header('Подключиться по SSH-алиасу', 'Подключения / Быстрое подключение',
                       'Введите Host из ~/.ssh/config. Остальные поля BULL прочитает через OpenSSH.')
        aliases = configured_ssh_aliases()
        if aliases:
            print('Найдены простые алиасы:', terminal_text(', '.join(aliases)))
        else:
            print('Алиасы не показаны. Их всё равно можно ввести вручную, включая записи из Include.')
        print('Поддерживается прямой key-based SSH. ProxyJump/ProxyCommand на этом экране не используются.')
        alias = ask(core, 'SSH-алиас (например bull-home)', required=True)
        resolved = resolve_ssh_alias(core, alias)
        print('\nПроверяю ключ сервера…')
        public, fingerprint = scan_host_key(core, resolved['host'], resolved['port'])
        trusted = known_host_key_matches(
            public, resolved['host'], resolved['port'], resolved['known_hosts_files'])
        print(terminal_text(
            f"  {resolved['alias']} → {resolved['user']}@{resolved['host']}:{resolved['port']}\n"
            f"  IdentityFile: {resolved['identity_file']}\n"
            f"  Fingerprint: {fingerprint}"
        ))
        if trusted:
            core.green(); print('  OK · ключ сервера совпадает с записью в вашем OpenSSH known_hosts.'); core.white()
        else:
            core.yellow(); print('  В OpenSSH known_hosts нет совпадающего ключа. Нужна независимая проверка.'); core.white()
            print('  На Windows-сервере: ssh-keygen -lf C:/ProgramData/ssh/ssh_host_ed25519_key.pub -E sha256')
            expected = ask(core, 'Fingerprint SHA256:…, полученный НА СЕРВЕРЕ', required=True)
            if expected != fingerprint:
                raise ValueError('Fingerprint не совпал. Подключение НЕ сохранено.')
        cid = 'ssh-' + hashlib.sha256(
            f"{resolved['host']}:{resolved['port']}:{resolved['user']}".encode()).hexdigest()[:16]
        entry = dict(
            schema='local-llm-connection', version=1, id=cid,
            name=resolved['alias'], route='direct', transport='ssh',
            endpoint=dict(host=resolved['host'], user=resolved['user'], port=resolved['port']),
            backend=dict(type='ollama', remote_port=11434),
            host_public_key=public, host_key_fingerprint=fingerprint,
            identity_file=resolved['identity_file'],
        )
        return confirm_install(core, clean_entry(core, entry))
    except Cancelled:
        print('Настройка отменена. Ничего не сохранено.')
        return None


def show_ssh_key_guide(core):
    config = Path.home() / '.ssh' / 'config'
    core.ui_header('SSH-ключ и алиас за несколько шагов', 'Подключения / Инструкция',
                   'BULL ничего не создаёт без вашей команды и никогда не копирует приватный ключ.')
    print('1. На клиентском компьютере создайте отдельный ключ:')
    print(r'   .\Client\New-BULL-ClientKey.ps1')
    print(r'   Передавайте на сервер только bull_access.pub. Файл bull_access остаётся у вас.')
    print('\n2. Добавьте публичный ключ на сервер.')
    print(r'   Проще всего: Install-BULL-v0.24.0.0.cmd → Server и укажите файл .pub.')
    print(r'   Для готового OpenSSH добавьте одну строку .pub в C:\Users\<SERVER_USER>\.ssh\authorized_keys.')
    print('\n3. Создайте или дополните файл:', terminal_text(str(config)))
    print('''
   Host bull-home
       HostName 203.0.113.10
       User <SERVER_USER>
       Port 22
       IdentityFile ~/.ssh/bull_access
       IdentitiesOnly yes''')
    print('\n4. Один раз проверьте в PowerShell: ssh bull-home')
    print('   Сверьте показанный fingerprint с сервером. Для ключа с паролем можно выполнить ssh-add ~/.ssh/bull_access.')
    print('\n5. В BULL выберите Подключения → SSH-алиас и введите bull-home.')
    print('\nБезопасность: не публикуйте приватный ключ и не открывайте наружу Ollama 11434/llama.cpp 8080.')


def new_ssh_connection(core, defaults=None):
    defaults = defaults or {}
    try:
        core.ui_header('Новый сервер по SSH', 'Подключения / Новый сервер', '4 шага. 0 на любом шаге — отменить без сохранения.')
        print('Нужны: адрес сервера, SSH-пользователь и приватный ключ, уже разрешённый на сервере.')
        print('Локальная Ollama не нужна. Для Интернета нужен доступный SSH-порт или VPN.')
        print('\n1/4 · Адрес')
        host = core._validate_ssh_host(ask(core, 'IP или DNS (без http://)', defaults.get('host', ''), True))
        user = core._validate_ssh_user(ask(core, 'Пользователь SSH на сервере', defaults.get('user', ''), True))
        port = int(ask(core, 'Внешний SSH-порт', defaults.get('port') or 22))
        if not 1 <= port <= 65535: raise ValueError('SSH-порт должен быть от 1 до 65535.')
        print('\n2/4 · Ключ доступа')
        print('Укажите приватный ключ без .pub. Для ключа с паролем заранее используйте ssh-agent.')
        key_path = private_key_path(ask(core, 'Путь к ключу', defaults.get('identity_file', ''), True))
        name = ask(core, 'Название сервера', host)
        advanced = ask(core, 'Enter — Ollama на порту 11434; A — другой порт', '')
        if advanced.casefold() not in ('', 'a', 'а'):
            raise ValueError('Введите Enter или A. Параметры не сохранены.')
        remote_port = int(ask(core, 'Порт Ollama внутри сервера', 11434)) if advanced else 11434
        print('\n3/4 · Проверка подлинности сервера')
        print('Получаю публичный ключ сервера (это ещё НЕ подтверждает его подлинность)…')
        public, fingerprint = scan_host_key(core, host, port)
        print('Полученный fingerprint:', fingerprint)
        print('Независимо получите fingerprint на самом сервере или у его администратора:')
        print('  Windows: ssh-keygen -lf C:/ProgramData/ssh/ssh_host_ed25519_key.pub -E sha256')
        print('  Linux:   ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256')
        expected = ask(core, 'Вставьте SHA256:…, полученный НА СЕРВЕРЕ (0 — отмена)', required=True)
        if expected != fingerprint:
            raise ValueError('Fingerprint не совпал. Подключение НЕ сохранено. Проверьте адрес и ключ сервера.')
        cid = 'ssh-' + hashlib.sha256(f'{host}:{port}:{user}'.encode()).hexdigest()[:16]
        entry = dict(schema='local-llm-connection', version=1, id=cid, name=name, route='direct', transport='ssh',
                     endpoint=dict(host=host, user=user, port=port), backend=dict(type='ollama', remote_port=remote_port),
                     host_public_key=public, host_key_fingerprint=fingerprint, identity_file=str(key_path))
        return confirm_install(core, clean_entry(core, entry))
    except Cancelled:
        print('Настройка отменена. Ничего не сохранено.')
        return None


def pick_entry(core, rows, title):
    core.ui_header(title, 'Подключения')
    if not rows:
        print('Подключений пока нет.'); pause(core); return None
    for index, row in enumerate(rows, 1):
        endpoint = row['endpoint']
        key_ok = Path(row.get('identity_file') or '').is_file()
        core.ui_menu_item(str(index), terminal_text(row['name']),
                          terminal_text(f"{endpoint['user']}@{endpoint['host']}:{endpoint['port']}"),
                          'ключ найден' if key_ok else 'нужен путь к ключу')
    while True:
        value = core.read_user_input('Номер сервера (0 — назад) › ').strip()
        if value in ('', '0'): return None
        row = selection(value, rows)
        if row is not None: return dict(row)
        print('Нет такого номера. Выберите сервер из списка.')


def import_old(core):
    folder = core.read_user_input('Папка старого билда (0 — назад) › ').strip().strip('"')
    if folder in ('', '0'): return None
    root = Path(folder).expanduser().resolve()
    store = root / 'Runtime/connections.json'
    if store.is_file():
        rows = [clean_entry(core, item) for item in read_document(store).get('connections', {}).values()]
        if rows:
            entry = pick_entry(core, rows, 'Подключения старого билда')
            if entry:
                if not Path(entry['identity_file']).is_file():
                    entry['identity_file'] = str(private_key_path(ask(core, 'Новый путь к приватному ключу', required=True)))
                return confirm_install(core, entry)
            return None
    settings = root / 'backend_settings.json'
    if settings.is_file():
        profiles = read_document(settings).get('remote_access', {}).get('profiles', {})
        rows = [(name, value) for name, value in profiles.items() if value.get('host')]
        for index, (name, value) in enumerate(rows, 1):
            core.ui_menu_item(index, terminal_text(name), terminal_text(value.get('host')))
        if rows:
            chosen = selection(core.read_user_input('Профиль (0 — назад) › ').strip(), rows)
            if chosen:
                print('Перенесём адрес и путь к ключу. Подлинность сервера нужно подтвердить заново.')
                return new_ssh_connection(core, chosen[1])
    print('Подключений не найдено. Создайте сервер через мастер SSH.'); pause(core)
    return None


def advanced_menu(core):
    while True:
        core.ui_header('Дополнительно', 'Подключения / Дополнительно')
        core.ui_menu_item('1', 'Импорт Connection JSON', 'Файл от администратора + ваш приватный ключ')
        core.ui_menu_item('2', 'Перенести из старой версии', 'Выбрать папку предыдущего билда')
        core.ui_menu_item('3', 'Проверить SSH выбранного сервера', 'Не запускает модели')
        core.ui_menu_item('4', 'Инструкция по доступу через Интернет', 'Подготовка сервера, VPN и роутера')
        core.ui_menu_item('5', 'Устаревшие SSH-профили', 'Совместимость: LAN, VPN, direct, auto')
        core.ui_menu_item('6', 'Забыть сервер в личной папке', 'Не удаляет ключ и не отзывает доступ на сервере')
        core.ui_menu_item('0', 'Назад')
        value = core.read_user_input('Выбор › ').strip()
        if value in ('', '0'): return None
        if value == '1':
            path = ask(core, 'Connection JSON (из доверенного источника)', required=True).strip('"')
            entry = core._validate_connection_bundle(read_document(path))
            entry['identity_file'] = str(private_key_path(ask(core, 'Ваш приватный ключ', required=True)))
            if confirm_install(core, entry): return '__connection_changed__'
        elif value == '2':
            if import_old(core): return '__connection_changed__'
        elif value == '3':
            if core.load_backend_settings().get('target_mode') != 'remote':
                print('Сейчас выбран локальный режим. SSH не используется.')
            else:
                ok, detail = core._test_ssh_endpoint(core.resolve_remote_endpoint(force=True), timeout=6)
                print(('SSH OK: ' if ok else 'SSH недоступен: ') + terminal_text(detail))
            pause(core)
        elif value == '4': core.show_internet_access_guide(); pause(core)
        elif value == '5':
            result = core.remote_access_menu()
            if result: return result
        elif value == '6':
            entry = pick_entry(core, saved_connections(core), 'Забыть сервер')
            if entry and core.read_user_input('Введите DELETE для удаления только записи › ').strip() == 'DELETE':
                (vault_dir() / (entry['id'] + '.json')).unlink(missing_ok=True)
                print('Запись удалена из личной папки. Ключ и настройки текущего билда сохранены.')
                pause(core)
        else: print('Выберите пункт 0–6.')


def connection_menu(core):
    while True:
        core.clear_console()
        core.ui_header('Подключения', 'Главная / Подключения', 'Где запускать модели? Локальная Ollama для SSH не требуется.')
        settings = core.load_backend_settings()
        remote = settings.get('target_mode') == 'remote'
        core.ui_status_strip([('Выбрано', 'удалённый сервер' if remote else 'этот компьютер', 'info')])
        core.ui_menu_item('1', 'Использовать этот компьютер', 'Ollama на localhost; не подключается к серверу')
        core.ui_menu_item('2', 'Подключиться по SSH-алиасу', 'Введите только Host из ~/.ssh/config', 'БЫСТРО')
        core.ui_menu_item('3', 'Выбрать сохранённый сервер', 'Включая подключения из других версий')
        core.ui_menu_item('4', 'Настроить сервер вручную', 'Адрес → пользователь и ключ → проверка → подключение')
        core.ui_menu_item('5', 'Как создать SSH-ключ и алиас', 'Пошаговая инструкция без изменения системы')
        core.ui_menu_item('6', 'Дополнительно', 'Импорт, перенос старых настроек, проверка SSH, Интернет')
        core.ui_menu_item('0', 'Назад')
        try:
            value = core.read_user_input('Выбор › ').strip()
            if value in ('', '0'): return None
            if value == '1': core.use_local_backend(); return '__connection_changed__'
            if value == '2':
                if new_ssh_alias_connection(core): return '__connection_changed__'
            elif value == '3':
                # Keep both differing entries visible: no implicit merge of identities.
                local = [clean_entry(core, x) for x in core.connection_entries()]
                rows = local + [x for x in saved_connections(core) if not any(
                    x['id'] == y['id'] and same_server(x, y) for y in local)]
                entry = pick_entry(core, rows, 'Сохранённые серверы')
                if entry:
                    if not Path(entry['identity_file']).is_file():
                        entry['identity_file'] = str(private_key_path(ask(core, 'Путь к приватному ключу', required=True)))
                    if confirm_install(core, entry): return '__connection_changed__'
            elif value == '4':
                if new_ssh_connection(core): return '__connection_changed__'
            elif value == '5':
                show_ssh_key_guide(core); pause(core)
            elif value == '6':
                result = advanced_menu(core)
                if result: return result
            else: print('Выберите пункт 0–6.')
        except Cancelled:
            print('Отменено без сохранения.')
        except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
            core.yellow(); print('Не удалось завершить действие:', terminal_text(str(exc))); core.white()
            print('Проверьте SSH-алиас или адрес, порт и файл ключа. Старые подключения сохранены.')
            pause(core)
