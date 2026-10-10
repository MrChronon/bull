"""Best-effort update of existing BULL-owned shortcuts, with fixed local tools."""
import os
from pathlib import Path
import subprocess


def sync_shortcuts(root, theme):
    root = Path(root).resolve()
    script = root / 'Tools/Update-BULL-Shortcuts.ps1'
    if os.name != 'nt' or not script.is_file():
        return True
    theme = 'matrix_bright' if theme == 'matrix_bright' else 'bull_red'
    env = {key: value for key, value in os.environ.items() if key.casefold() != 'psmodulepath'}
    try:
        result = subprocess.run([
            'powershell.exe', '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(script), '-Quiet', '-UpdateExistingOnly', '-Theme', theme,
        ], cwd=root, env=env, capture_output=True, timeout=15,
           creationflags=subprocess.CREATE_NO_WINDOW)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
