import os
import pytest
import importlib
import antithesis._internal

# TESTING ONLY
# Redeclare to avoid loading internal.py early
TESTING_OUTPUT_ENV_VAR: str = "ANTITHESIS_SDK_LOCAL_OUTPUT"

@pytest.fixture
def setup_local_handler(monkeypatch, tmp_path):
    out_file = str(tmp_path / "test_out.json")
    monkeypatch.setenv(TESTING_OUTPUT_ENV_VAR, out_file)
    assert os.getenv(TESTING_OUTPUT_ENV_VAR) == out_file
    importlib.reload(antithesis._internal)

@pytest.fixture
def setup_noop_handler():
    assert os.getenv(TESTING_OUTPUT_ENV_VAR) is None
    importlib.reload(antithesis._internal)
