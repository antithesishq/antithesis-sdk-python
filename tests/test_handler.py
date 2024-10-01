import os
import pytest
import importlib
import internal

# Redeclare to avoid loading internal.py early
LOCAL_OUTPUT_ENV_VAR: str = "ANTITHESIS_SDK_LOCAL_OUTPUT"

def test_local_handler(monkeypatch):
    monkeypatch.setenv(LOCAL_OUTPUT_ENV_VAR, 'test_out.json')
    assert os.getenv(LOCAL_OUTPUT_ENV_VAR) == 'test_out.json'
    importlib.reload(internal)

    from internal import _HANDLER, LocalHandler

    assert isinstance(_HANDLER, LocalHandler)

def test_noop_handler():
    assert os.getenv(LOCAL_OUTPUT_ENV_VAR) is None
    importlib.reload(internal)

    from internal import _HANDLER, NoopHandler

    assert isinstance(_HANDLER, NoopHandler)