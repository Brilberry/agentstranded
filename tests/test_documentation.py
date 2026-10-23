from ast import literal_eval
import os
from pathlib import Path
import subprocess
import sys


def test_overview_headless_snippet():
    root = Path(__file__).resolve().parents[1]
    guide = root / "agentstranded/OVERVIEW.md"
    code = guide.read_text(encoding="utf-8").split("```python\n", 1)[1].split("```", 1)[0]
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=root,
        env={**os.environ, "PYTHONPATH": str(root)},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    survivors = literal_eval(result.stdout.strip())
    assert [name for name, _ in survivors] == ["Ari", "Bo", "Cyra", "Dax", "Ena"]
    assert all(isinstance(alive, bool) for _, alive in survivors)
