import pytest
from .handler_helper import setup_local_handler, setup_noop_handler
    
def test_local_handler(setup_local_handler):
    from antithesis._internal import _HANDLER, LocalHandler

    assert isinstance(_HANDLER, LocalHandler)

def test_noop_handler(setup_noop_handler):
    from antithesis._internal import _HANDLER, NoopHandler

    assert isinstance(_HANDLER, NoopHandler)
