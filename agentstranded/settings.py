"""Packaged, data-only defaults shared by normal play and competitions."""
import json
from pathlib import Path

CONFIG_DIRECTORY = Path(__file__).parent / "configs"
DEFAULTS = json.loads((CONFIG_DIRECTORY / "defaults.json").read_text(encoding="utf-8"))
SIMULATION_DEFAULTS = DEFAULTS["simulation"]
