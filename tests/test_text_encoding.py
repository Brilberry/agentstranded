import json
import os

import pytest

from agentstranded.competition import load
from agentstranded.report_view import render_html


@pytest.mark.parametrize("json5", [False, True])
def test_config_loader_reads_utf8_names(tmp_path, json5):
    path = tmp_path / ("team.json5" if json5 else "team.json")
    value = {"name": "Île “Ari” — 漂流 🏝"}
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    assert load(path, json5=json5) == value


def test_unicode_report_round_trip(tmp_path):
    path = tmp_path / "report.md"
    path.write_text("# Agent Stranded\n\n“Ari” — 漂流 🏝", encoding="utf-8")
    html = render_html(path).read_text(encoding="utf-8")
    assert "“Ari” — 漂流 🏝" in html
    assert "\ufffd" not in html


def test_optional_locale_emulation_catches_implicit_decoding(tmp_path):
    if not os.environ.get("AGENTSTRANDED_TEST_ENCODING"):
        pytest.skip("Run with AGENTSTRANDED_TEST_ENCODING=cp1252 to verify locale emulation")
    path = tmp_path / "utf8.txt"
    path.write_bytes("”".encode("utf-8"))
    with pytest.raises(UnicodeDecodeError):
        path.read_text()  # Deliberately implicit: prove the emulation exposes the original bug.
    assert path.read_text(encoding="utf-8") == "”"
