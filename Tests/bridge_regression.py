"""Offline contracts for the BULL compatibility bridge and locked brand."""

from __future__ import annotations

import json
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _png_size(path: Path) -> tuple[int, int]:
    """Read the PNG IHDR dimensions without adding a runtime Pillow dependency."""
    header = path.read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise AssertionError(f"Invalid PNG header: {path.name}")
    return struct.unpack(">II", header[16:24])


def _assert_ico(path: Path) -> None:
    """Validate the ICO directory header using only the Python standard library."""
    header = path.read_bytes()[:6]
    if len(header) != 6:
        raise AssertionError(f"Truncated ICO header: {path.name}")
    reserved, image_type, count = struct.unpack("<HHH", header)
    if reserved != 0 or image_type != 1 or count < 1:
        raise AssertionError(f"Invalid ICO header: {path.name}")


class BridgeTests(unittest.TestCase):
    def test_facade_owns_contract_objects_without_legacy_package(self):
        from Shared.bull_llm import schemas as current
        from Shared.bull_llm.backends import Backend as current_backend
        self.assertEqual(current.BENCH_RECORD_SCHEMA_VERSION, 12)
        self.assertTrue(hasattr(current_backend, "health"))
        self.assertFalse((ROOT / "Shared" / "historical_shared").exists())

    def test_supported_artifacts_are_explicit_and_checkpoint_is_not_resumable(self):
        from Shared.bull_llm.compatibility import supported_legacy_artifacts
        rows = supported_legacy_artifacts()
        self.assertGreaterEqual(len(rows), 11)
        checkpoints = [row for row in rows if row.artifact == "benchmark_checkpoint"]
        self.assertEqual(len(checkpoints), 1)
        self.assertFalse(checkpoints[0].can_resume)

    def test_reader_is_read_only_and_returns_an_independent_copy(self):
        from Shared.bull_llm.compatibility import read_legacy_artifact
        value = {
            "schema": "bull-agent-run",
            "schema_version": 1,
            "run_id": "fixture",
            "metrics": {"success": True},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            before = path.read_bytes()
            info, loaded = read_legacy_artifact(path)
            loaded["metrics"]["success"] = False
            self.assertEqual(info.artifact, "agent_run")
            self.assertEqual(path.read_bytes(), before)
            self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["metrics"]["success"])

    def test_reader_fails_closed_for_unknown_or_nonfinite_schema(self):
        from Shared.bull_llm.compatibility import inspect_legacy_document, read_legacy_artifact
        with self.assertRaises(ValueError):
            inspect_legacy_document({"schema": "unknown", "schema_version": 1})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text('{"schema":"bull-agent-run","schema_version":1,"x":NaN}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_legacy_artifact(path)

    def test_release_has_only_branded_launchers(self):
        for target in (
            "BULL-v0.29.0.1.cmd",
            "BULL-Benchmark-Lab-v0.29.0.1.cmd",
            "BULL-Agent-Lab-v0.29.0.1.cmd",
            "Setup.exe",
            "Setup.cmd",
            "Setup/BULL.launcher.bin",
        ):
            self.assertTrue((ROOT / target).is_file(), target)
        retired_marker = "-".join(("local", "llm"))
        legacy_names = [path for path in ROOT.rglob("*") if retired_marker in path.name.casefold()]
        self.assertEqual(legacy_names, [])

    @unittest.skipUnless(os.name == "nt", "Windows installer integration")
    def test_client_installer_creates_isolated_shortcuts(self):
        with tempfile.TemporaryDirectory(prefix="bull-installer-") as temporary:
            root = Path(temporary)
            from shutil import copyfile
            client = root/'InstalledClient'
            for source,target in (
                ('Tools/Update-BULL-Shortcuts.ps1','Tools/Update-BULL-Shortcuts.ps1'),
                ('Assets/Brand/bull-icon-matrix.ico','Assets/Brand/bull-icon-matrix.ico'),
                ('BULL-v0.29.0.1.ico','BULL-v0.29.0.1.ico'),
                ('Setup/BULL.launcher.bin','BULL.exe'),
            ):
                destination=client/target; destination.parent.mkdir(parents=True,exist_ok=True)
                copyfile(ROOT/source,destination)
            desktop = root / "Desktop"
            programs = root / "Programs"
            result = subprocess.run(
                [
                    "powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(client / "Tools/Update-BULL-Shortcuts.ps1"), "-Quiet",
                    "-DesktopDirectory", str(desktop),
                    "-ProgramsDirectory", str(programs),
                    "-ShortcutStatePath", str(root / 'shortcut_state.json'),
                ],
                cwd=ROOT,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr).decode(errors="replace"))
            self.assertTrue((desktop / "BULL.lnk").is_file())
            self.assertTrue((programs / "BULL.lnk").is_file())
            # Inspect the real shell links, then change their icon without
            # changing target/working directory. Nothing touches the real Desktop.
            reader = root / 'read_link.ps1'
            reader.write_text('param([string]$Path)\n$w=New-Object -ComObject WScript.Shell\n'
                              '$s=$w.CreateShortcut($Path)\n'
                              '@{target=$s.TargetPath;icon=$s.IconLocation;working=$s.WorkingDirectory} | ConvertTo-Json\n', encoding='ascii')
            env = {key:value for key,value in os.environ.items() if key.casefold() != 'psmodulepath'}
            def read_link(path):
                response = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
                                           '-File',str(reader),'-Path',str(path)],env=env,capture_output=True,timeout=20)
                self.assertEqual(response.returncode,0,response.stderr.decode(errors='replace'))
                return json.loads(response.stdout.decode('utf-8-sig'))
            for theme, suffix in [('matrix_bright','bull-icon-matrix.ico,0'),('bull_red','BULL-v0.29.0.1.ico,0')]:
                response = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
                    '-File',str(client/'Tools/Update-BULL-Shortcuts.ps1'),'-Quiet','-UpdateExistingOnly',
                    '-Theme',theme,'-ShortcutStatePath',str(root/'shortcut_state.json')],
                    env=env,capture_output=True,timeout=30)
                self.assertEqual(response.returncode,0,response.stderr.decode(errors='replace'))
                for directory in (desktop, programs):
                    link = read_link(directory/'BULL.lnk')
                    self.assertEqual(Path(link['target']),client/'BULL.exe')
                    self.assertEqual(Path(link['working']),client)
                    self.assertTrue(link['icon'].endswith(suffix),link['icon'])
            # A same-named foreign shortcut, or an unowned empty working
            # directory, must never be changed by the theme updater.
            writer = root / 'foreign_link.ps1'
            writer.write_text('param([string]$Path,[string]$Target,[string]$Working)\n'
                              '$w=New-Object -ComObject WScript.Shell\n$s=$w.CreateShortcut($Path)\n'
                              '$s.TargetPath=$Target\n$s.WorkingDirectory=$Working\n'
                              '$s.IconLocation="shell32.dll,1"\n$s.Save()\n', encoding='ascii')
            for target, working in [(str(root/'other.exe'),str(root)), (str(client/'BULL.exe'),'')]:
                response = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
                    '-File',str(writer),'-Path',str(desktop/'BULL.lnk'),'-Target',target,'-Working',working],
                    env=env,capture_output=True,timeout=20)
                self.assertEqual(response.returncode,0,response.stderr.decode(errors='replace'))
                previous = read_link(desktop/'BULL.lnk')
                response = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
                    '-File',str(client/'Tools/Update-BULL-Shortcuts.ps1'),'-Quiet','-UpdateExistingOnly',
                    '-Theme','matrix_bright','-ShortcutStatePath',str(root/'shortcut_state.json')],
                    env=env,capture_output=True,timeout=30)
                self.assertEqual(response.returncode,0,response.stderr.decode(errors='replace'))
                self.assertEqual(read_link(desktop/'BULL.lnk'),previous)

    def test_brand_assets_are_local_safe_and_have_expected_sizes(self):
        brand = ROOT / "Assets" / "Brand"
        for name in ("bull-mark.svg", "bull-mark-light.svg", "bull-mark-mono.svg", "bull-wordmark.svg"):
            raw = (brand / name).read_text(encoding="utf-8")
            ElementTree.fromstring(raw)
            lowered = raw.lower()
            self.assertNotIn("<script", lowered)
            self.assertNotIn("http://", lowered.replace('http://www.w3.org/2000/svg', ''))
            self.assertNotIn("https://", lowered)
        expected = {"bull-mark-16.png": (16, 16), "bull-mark-512.png": (512, 512),
                    "favicon.png": (32, 32), "github-social-preview.png": (1280, 640)}
        for name, size in expected.items():
            self.assertEqual(_png_size(brand / name), size)
        _assert_ico(ROOT / "BULL-v0.29.0.1.ico")
        lock = json.loads((brand / "brand-lock.json").read_text(encoding="utf-8"))
        master = brand / lock["source_file"]
        self.assertEqual(hashlib.sha256(master.read_bytes()).hexdigest(), lock["source_sha256"])
        self.assertEqual(lock["source_sha256"], "60d91a700b9cd91ad3fd6ad598287a8e2cccd067f2ab0ed7515dd52af44b2269")
        self.assertEqual(lock["derivation"], "crop_resize_only_no_redraw")

    def test_bridge_release_identity_and_measurement_freeze_are_documented(self):
        core = (ROOT / "bull_client_v0.29.0.1.py").read_text(encoding="utf-8")
        self.assertIn("APP_NAME='BULL — Benchmark Lab'", core)
        self.assertIn("APP_VERSION='v0.29.0.1'", core)
        self.assertIn("'СОСТОЯНИЕ BULL'", core)
        self.assertNotIn("'LOCAL' + ' LLM DASHBOARD'", core)
        notes = (ROOT / "Docs" / "RELEASE_NOTES_0.29.0.1.md").read_text(encoding="utf-8")
        for phrase in ("Built-in benchmark prompts", "scorers", "runtime"):
            self.assertIn(phrase, notes)


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BridgeTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("BULL bridge regression failed")
    return result.testsRun


if __name__ == "__main__":
    run_suite()
