import os
import pytest
import importlib
import internal

# Redeclare to avoid loading internal.py early
LOCAL_OUTPUT_ENV_VAR: str = "ANTITHESIS_SDK_LOCAL_OUTPUT"

@pytest.fixture
def setup_local_handler(monkeypatch):
    monkeypatch.setenv(LOCAL_OUTPUT_ENV_VAR, 'test_out.json')
    assert os.getenv(LOCAL_OUTPUT_ENV_VAR) == 'test_out.json'
    importlib.reload(internal)

@pytest.fixture
def setup_noop_handler():
    assert os.getenv(LOCAL_OUTPUT_ENV_VAR) is None
    importlib.reload(internal)