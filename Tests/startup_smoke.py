"""Mandatory boot gate; no release fixtures, inference, SSH or user packs."""
from pathlib import Path
import ast
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if __name__ == '__main__':
    from Shared.bull_llm.startup_checks import run
    client = ROOT / 'bull_client_v0.29.0.1.py'
    tree = ast.parse(client.read_text(encoding='utf-8-sig'))
    version = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(x, ast.Name) and x.id == 'APP_VERSION' for x in node.targets))
    run(ROOT, version, client.name)
