"""Deterministic optional base ZIPs; runtime never installs them implicitly."""
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Shared.bull_llm.evaluation.catalog import engine_registry_policy
from Shared.bull_llm.evaluation.pack_library import PackLibrary
from Shared.bull_llm.evaluation.registry import load_pack


def build():
    destination = ROOT / "BasePacks"
    destination.mkdir(exist_ok=True)
    policy = engine_registry_policy("0.29.0.1")
    for directory in sorted((ROOT / "BenchmarkPacks").iterdir()):
        if not directory.is_dir():
            continue
        pack = load_pack(directory, policy, "public")
        target = destination / (pack.identity + ".zip")
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    entry = zipfile.ZipInfo(path.relative_to(directory).as_posix(), (2026, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    entry.external_attr = 0o100644 << 16
                    archive.writestr(entry, path.read_bytes())
        preview = PackLibrary(destination, policy).inspect_zip(target)
        assert preview.compiled_sha256 == pack.compiled_sha256
        print(target.name + " - " + str(len(pack.cases)) + " tests")


if __name__ == "__main__":
    build()
