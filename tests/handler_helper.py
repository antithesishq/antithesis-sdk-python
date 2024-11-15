import os
import pytest
import importlib
import antithesis._internal

# TESTING ONLY
# Redeclare to avoid loading internal.py early
TESTING_OUTPUT_ENV_VAR: str = "ANTITHESIS_SDK_LOCAL_OUTPUT"

@pytest.fixture
def setup_local_handler(monkeypatch):
    monkeypatch.setenv(TESTING_OUTPUT_ENV_VAR, 'test_out.json')
    assert os.getenv(TESTING_OUTPUT_ENV_VAR) == 'test_out.json'
    importlib.reload(antithesis._internal)

@pytest.fixture
def setup_noop_handler():
    assert os.getenv(TESTING_OUTPUT_ENV_VAR) is None
    importlib.reload(antithesis._internal)
