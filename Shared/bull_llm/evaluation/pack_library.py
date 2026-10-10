"""Local ZIP installation for the BULL data-only pack library.

This module does not select tests, download content, execute code or change the
production catalog. Published versions are never overwritten. Caller-supplied
roots keep tests independent from a real user's persistent library.
"""

from __future__ import annotations

import os
import re
import stat
import sys
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from .registry import (
    PACK_ID_RE, VERSION_RE, LoadedPack, PackValidationError, RegistryFinding,
    RegistryPolicy, _load_json, load_pack,
)


DATA_SUFFIXES = frozenset({".json", ".yaml", ".yml", ".md", ".txt"})
WINDOWS_DEVICE = re.compile(r"^(?:con|prn|aux|nul|conin\$|conout\$|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)", re.I)
UNSAFE_COMPONENT = re.compile(r'[<>:"|?*\x00-\x1f\x7f]')
REPARSE_POINT = 0x400


@dataclass(frozen=True)
class ZipLimits:
    max_archive_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 128 * 1024 * 1024
    max_file_bytes: int = 8 * 1024 * 1024
    max_entries: int = 4096
    max_compression_ratio: int = 200

    def __post_init__(self):
        for value in vars(self).values():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("ZIP limits must be positive integers")


def default_pack_library_root(
    environment: Mapping[str, str] | None = None, *, platform: str | None = None,
) -> Path:
    """Return the Windows per-user location without creating it or falling back."""
    if (sys.platform if platform is None else platform) != "win32":
        raise PackValidationError("PACK_PLATFORM_UNSUPPORTED", "default library location currently supports Windows only")
    value = (os.environ if environment is None else environment).get("LOCALAPPDATA", "")
    base = Path(value)
    if not value or not base.is_absolute():
        raise PackValidationError("PACK_LIBRARY_LOCATION", "LOCALAPPDATA must be an absolute user directory")
    return base / "BULL" / "BenchmarkPacks"


def _lstat(path: Path):
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _no_link(path: Path, details):
    if stat.S_ISLNK(details.st_mode) or getattr(details, "st_file_attributes", 0) & REPARSE_POINT:
        raise PackValidationError("PACK_LIBRARY_LINK", "library paths cannot contain links or reparse points", path)


def _directory(path: Path, *, create: bool = False) -> bool:
    """Check every existing ancestor before creating a directory, without resolve()."""
    for item in (*reversed(path.parents), path):
        details = _lstat(item)
        if details is None and create:
            try:
                item.mkdir()
            except FileExistsError:
                pass
            details = _lstat(item)
        if details is None:
            return False
        _no_link(item, details)
        if not stat.S_ISDIR(details.st_mode):
            raise PackValidationError("PACK_LIBRARY_PATH", "expected a regular directory", item)
    return True


def _entry_parts(name: str, *, directory: bool) -> tuple[str, ...]:
    if directory and name.endswith("/"):
        name = name[:-1]
    parts = tuple(name.split("/"))
    if (not name or "\\" in name or len(name) > 180 or len(parts) > 12 or
            unicodedata.normalize("NFC", name) != name):
        raise PackValidationError("ZIP_UNSAFE_PATH", "invalid archive path")
    for part in parts:
        if (not part or part in {".", ".."} or part != part.strip() or part.endswith(".") or
                UNSAFE_COMPONENT.search(part) or WINDOWS_DEVICE.match(part)):
            raise PackValidationError("ZIP_UNSAFE_PATH", "unsafe archive path component")
    return parts


def _file_type(parts: tuple[str, ...]):
    if any(part.startswith(".") for part in parts) or Path(parts[-1]).suffix.casefold() not in DATA_SUFFIXES:
        raise PackValidationError("ZIP_FILE_TYPE_FORBIDDEN", "only JSON YAML Markdown and TXT pack data are accepted")


def _preflight(archive: zipfile.ZipFile, limits: ZipLimits):
    entries = archive.infolist()
    if not entries or len(entries) > limits.max_entries:
        raise PackValidationError("ZIP_LIMIT_EXCEEDED", "archive entry budget exceeded or archive is empty")
    total = 0
    paths = {}
    explicit = set()
    rows = []
    for entry in entries:
        if entry.flag_bits & 1:
            raise PackValidationError("ZIP_ENCRYPTED", "encrypted pack entries are not supported")
        mode = entry.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if (kind not in {0, stat.S_IFREG, stat.S_IFDIR} or
                entry.external_attr & REPARSE_POINT or
                ((kind == stat.S_IFDIR) != entry.is_dir() and kind != 0)):
            raise PackValidationError("ZIP_LINK_OR_SPECIAL_FILE", "links and special files are forbidden")
        parts = _entry_parts(entry.orig_filename, directory=entry.is_dir())
        if not entry.is_dir():
            _file_type(parts)
        if entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
            raise PackValidationError("ZIP_INVALID", "unsupported ZIP compression method")
        if (entry.file_size > limits.max_file_bytes or
                entry.file_size > max(1, entry.compress_size) * limits.max_compression_ratio or
                (entry.is_dir() and entry.file_size != 0)):
            raise PackValidationError("ZIP_LIMIT_EXCEEDED", "file size or compression ratio budget exceeded")
        total += entry.file_size
        if total > limits.max_total_bytes:
            raise PackValidationError("ZIP_LIMIT_EXCEEDED", "expanded archive budget exceeded")
        folded = tuple(part.casefold() for part in parts)
        if folded in explicit:
            raise PackValidationError("ZIP_PATH_COLLISION", "duplicate archive path")
        explicit.add(folded)
        for count in range(1, len(parts) + 1):
            original, key = parts[:count], folded[:count]
            is_dir = count < len(parts) or entry.is_dir()
            previous = paths.get(key)
            if previous is not None and previous != (original, is_dir):
                raise PackValidationError("ZIP_PATH_COLLISION", "case alias or file/directory collision")
            paths[key] = (original, is_dir)
        rows.append((entry, parts))

    manifests = [parts for entry, parts in rows if not entry.is_dir() and parts[-1] == "manifest.json"]
    if len(manifests) != 1 or len(manifests[0]) not in {1, 2}:
        raise PackValidationError("ZIP_PACK_LAYOUT", "ZIP must contain one root-level pack or one enclosing directory")
    prefix = manifests[0][:-1]
    for entry, parts in rows:
        if prefix and not ((parts == prefix and entry.is_dir()) or
                           (parts[:len(prefix)] == prefix and len(parts) > len(prefix))):
            raise PackValidationError("ZIP_PACK_LAYOUT", "archive contains files outside the pack")
    return rows, prefix


def _extract(archive, rows, prefix, target, limits):
    total = 0
    for entry, parts in rows:
        relative = parts[len(prefix):]
        if not relative:
            continue
        path = target.joinpath(*relative)
        if entry.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with archive.open(entry) as source, path.open("xb") as destination:
            while True:
                chunk = source.read(64 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                total += len(chunk)
                if size > min(entry.file_size, limits.max_file_bytes) or total > limits.max_total_bytes:
                    raise PackValidationError("ZIP_LIMIT_EXCEEDED", "actual expanded bytes exceed the declared budget")
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())
        if size != entry.file_size:
            raise PackValidationError("ZIP_INVALID", "entry size differs from the ZIP directory")


def _validated_pack(path, policy, visibility):
    try:
        return load_pack(path, policy, visibility)
    except PackValidationError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
        raise PackValidationError("PACK_INVALID", "pack contains invalid structured data", path) from error


class PackLibrary:
    def __init__(self, root: str | Path, policy: RegistryPolicy, *, limits: ZipLimits | None = None):
        self.root = Path(os.path.abspath(root))
        self.policy = policy
        self.limits = ZipLimits() if limits is None else limits

    def _installed(self, path, visibility, *, include_size=False):
        _directory(path)
        stack, count, total = [path], 0, 0
        while stack:
            for item in stack.pop().iterdir():
                details = item.lstat()
                _no_link(item, details)
                count += 1
                if count > self.limits.max_entries:
                    raise PackValidationError("ZIP_LIMIT_EXCEEDED", "installed pack entry budget exceeded")
                if stat.S_ISDIR(details.st_mode):
                    stack.append(item)
                elif stat.S_ISREG(details.st_mode):
                    _file_type(item.relative_to(path).parts)
                    total += details.st_size
                    if details.st_size > self.limits.max_file_bytes or total > self.limits.max_total_bytes:
                        raise PackValidationError("ZIP_LIMIT_EXCEEDED", "installed pack byte budget exceeded")
                else:
                    raise PackValidationError("PACK_LIBRARY_LINK", "special files are forbidden", item)
        pack = _validated_pack(path, self.policy, visibility)
        if path.name != pack.identity:
            raise PackValidationError("PACK_LIBRARY_IDENTITY", "directory does not match pack identity", path)
        if len({case.id for case in pack.cases}) != len(pack.cases):
            raise PackValidationError("PACK_AMBIGUOUS_CASE_ID", "case IDs must be unique within a library pack", path)
        return (pack, total) if include_size else pack

    def size_bytes(self, pack_id: str, version: str) -> int:
        """Bounded, link-rejecting observed size of one installed version."""
        pack = self.get(pack_id, version)
        return self._installed(pack.root, pack.visibility.value, include_size=True)[1]

    def scan(self) -> tuple[RegistryFinding, ...]:
        """List invalid versions as findings without hiding healthy versions."""
        if not _directory(self.root):
            return ()
        findings = []
        for visibility in ("public", "private"):
            branch = self.root / "Installed" / visibility
            if not _directory(branch):
                continue
            for path in sorted(branch.iterdir(), key=lambda item: item.name.casefold()):
                try:
                    pack = self._installed(path, visibility)
                    findings.append(RegistryFinding(path, visibility, pack=pack))
                except (PackValidationError, OSError) as error:
                    findings.append(RegistryFinding(path, visibility, error_code=getattr(error, "code", "PACK_INSTALL_IO"), error_message=str(error)))
        counts = {}
        for row in findings:
            if row.pack is not None:
                counts[row.pack.identity] = counts.get(row.pack.identity, 0) + 1
        return tuple(
            replace(row, pack=None, error_code="DUPLICATE_PACK_ID", error_message="pack identity exists in multiple library branches")
            if row.pack is not None and counts[row.pack.identity] > 1 else row
            for row in findings
        )

    def get(self, pack_id: str, version: str) -> LoadedPack:
        """An exact version is mandatory; a newer installation is never substituted."""
        if (not isinstance(pack_id, str) or not PACK_ID_RE.fullmatch(pack_id) or
                not isinstance(version, str) or not VERSION_RE.fullmatch(version)):
            raise PackValidationError("PACK_LIBRARY_IDENTITY", "invalid pack ID or version")
        matches = []
        for visibility in ("public", "private"):
            branch = self.root / "Installed" / visibility
            if _directory(branch):
                path = branch / f"{pack_id}@{version}"
                if _lstat(path) is not None:
                    matches.append((path, visibility))
        if len(matches) > 1:
            raise PackValidationError("DUPLICATE_PACK_ID", "pack identity exists in multiple library branches")
        if not matches:
            raise KeyError(f"Benchmark pack not installed: {pack_id}@{version}")
        return self._installed(*matches[0])

    def inspect_zip(self, source: str | Path) -> LoadedPack:
        """Validate a ZIP for a consent preview without publishing any files.

        The returned root is temporary and is no longer available. Consumers
        must use the validated metadata, never open documentation from it.
        """
        return self._zip_operation(Path(source), preview=True)

    def install_zip(self, source: str | Path, *, expected_compiled_sha256=None,
                    expected_manifest_sha256=None) -> LoadedPack:
        """Preflight, bounded extraction, registry validation, atomic publication."""
        return self._zip_operation(Path(source), expected_compiled_sha256=expected_compiled_sha256,
                                   expected_manifest_sha256=expected_manifest_sha256)

    def _zip_operation(self, source, **options):
        try:
            return self._install_zip(source, **options)
        except PackValidationError:
            raise
        except (zipfile.BadZipFile, EOFError, RuntimeError, NotImplementedError) as error:
            raise PackValidationError("ZIP_INVALID", "archive is damaged or unsupported") from error
        except OSError as error:
            raise PackValidationError("PACK_INSTALL_IO", "cannot read archive or publish the pack") from error
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
            raise PackValidationError("PACK_INVALID", "pack contains invalid structured data") from error

    def _install_zip(self, source: Path, *, preview=False, expected_compiled_sha256=None,
                     expected_manifest_sha256=None) -> LoadedPack:
        with source.open("rb") as stream:
            if os.fstat(stream.fileno()).st_size > self.limits.max_archive_bytes:
                raise PackValidationError("ZIP_LIMIT_EXCEEDED", "archive byte budget exceeded")
            with zipfile.ZipFile(stream) as archive:
                rows, prefix = _preflight(archive, self.limits)
                if preview:
                    with tempfile.TemporaryDirectory(prefix="bull-pack-preview-") as temporary:
                        unpacked = Path(temporary)
                        _extract(archive, rows, prefix, unpacked, self.limits)
                        return self._validate_import(unpacked)
                _directory(self.root, create=True)
                lock = self.root / ".install.lock"
                try:
                    lock_stream = lock.open("xb")
                except FileExistsError as error:
                    raise PackValidationError("PACK_INSTALL_BUSY", "another installation lock exists; do not remove it while BULL is running") from error
                try:
                    stage_root = self.root / ".staging"
                    _directory(stage_root, create=True)
                    with tempfile.TemporaryDirectory(prefix="pack-", dir=stage_root) as temporary:
                        unpacked = Path(temporary) / "content"
                        unpacked.mkdir()
                        _extract(archive, rows, prefix, unpacked, self.limits)
                        pack = self._validate_import(unpacked)
                        visibility = pack.visibility.value
                        if ((expected_compiled_sha256 is not None and pack.compiled_sha256 != expected_compiled_sha256) or
                                (expected_manifest_sha256 is not None and pack.manifest_sha256 != expected_manifest_sha256)):
                            raise PackValidationError("PACK_PREVIEW_CHANGED", "ZIP differs from the approved preview; inspect it again")
                        for branch in ("public", "private"):
                            existing = self.root / "Installed" / branch
                            if _directory(existing) and _lstat(existing / pack.identity) is not None:
                                raise PackValidationError("PACK_VERSION_EXISTS", "install a new pack version instead of overwriting an existing version")
                        branch_root = self.root / "Installed" / visibility
                        _directory(branch_root, create=True)
                        destination = branch_root / pack.identity
                        os.rename(unpacked, destination)
                        return replace(pack, root=destination)
                finally:
                    lock_stream.close()
                    lock.unlink()

    def _validate_import(self, unpacked):
        metadata = _load_json(unpacked / "manifest.json", self.policy.max_json_bytes)
        visibility = metadata.get("visibility") if isinstance(metadata, dict) else None
        if visibility not in {"public", "private"}:
            raise PackValidationError("INVALID_LIFECYCLE", "pack visibility must be public or private")
        pack = _validated_pack(unpacked, self.policy, visibility)
        if not pack.runnable:
            raise PackValidationError("PACK_NOT_RUNNABLE", "retired packs cannot be installed for new runs")
        if len({case.id for case in pack.cases}) != len(pack.cases):
            raise PackValidationError("PACK_AMBIGUOUS_CASE_ID", "case IDs must be unique within a library pack")
        return pack

    def move_to_trash(self, pack_id: str, version: str) -> Path:
        """Recoverable removal of one exact installed version, not a tree delete."""
        from uuid import uuid4
        pack = self.get(pack_id, version)
        lock = self.root / ".install.lock"
        try:
            stream = lock.open("xb")
        except FileExistsError as error:
            raise PackValidationError("PACK_INSTALL_BUSY", "another library operation is in progress") from error
        try:
            # Revalidate inside the lock, including each ancestor.
            pack = self.get(pack_id, version)
            trash = self.root / "Trash"
            _directory(trash, create=True)
            destination = trash / (pack.identity + "-" + uuid4().hex)
            os.rename(pack.root, destination)
            return destination
        finally:
            stream.close()
            lock.unlink()


__all__ = ["PackLibrary", "ZipLimits", "default_pack_library_root"]
