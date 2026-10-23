"""Optional non-UTF-8 filesystem locale emulation for portable text-I/O tests."""
import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def filesystem_encoding(monkeypatch):
    encoding = os.environ.get("AGENTSTRANDED_TEST_ENCODING")
    if not encoding:
        return
    original = Path.open

    def open_with_locale(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if "b" not in mode and encoding in (None, "locale"):
            encoding = os.environ["AGENTSTRANDED_TEST_ENCODING"]
        return original(self, mode=mode, buffering=buffering, encoding=encoding,
                        errors=errors, newline=newline)

    monkeypatch.setattr(Path, "open", open_with_locale)
