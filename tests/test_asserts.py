import json
from inspect import stack

import pytest
from antithesis.assertions import (
    always, 
    always_or_unreachable, 
    sometimes, 
    assert_raw,
    reachable,
    unreachable,
)

from .handler_helper import setup_local_handler

@pytest.fixture
def details_example():
    details = {
        "pens": 10,
        "weight": 41.75,
        "title": "some stationary",
        "validated": True,
        "verified": False,
    }
    return details

# TODO: Presently this always results in a NoopHandler from the perspective of assertions.py module
# needs investogation, and repair,  maybe more extensive? reload(internal) is needed
def test_always(setup_local_handler, details_example):
    always(True, "always test", details_example)

def test_always_or_unreachable(setup_local_handler, details_example):
    always_or_unreachable(True, "alwaysOrUnreachable test", details_example)

def test_sometimes(setup_local_handler, details_example):
    sometimes(True, "sometimes test", details_example)

def test_reachable(setup_local_handler, details_example):
    reachable("reachable test", details_example)

def test_unreachable(setup_local_handler, details_example):
    reachable("unreachable test", details_example)

def test_assert_raw(setup_local_handler, details_example):
    assert_raw(
        True,
        "assert_raw test",
        details_example,
        "test_asserts.py",
        "test_assert_raw",
        None,
        25,
        4,
        True,
        True,
        "always",
        "Always",
        "assert_raw test",
    )
