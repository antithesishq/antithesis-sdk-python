import pytest
import json
from inspect import stack

from location import LocationInfo

@pytest.fixture
def simple_details():
    return {"a":1, "b":"important value"}

def test_simple(simple_details):
    want = '{"a": 1, "b": "important value"}'
    got = json.dumps(simple_details)
    print("GOT: ", got)
    assert want == got

@pytest.fixture
def location_example():
    all_frames = stack()
    this_frame = all_frames[0]
    return LocationInfo(this_frame)

def test_location_to_json(location_example):
    jx = location_example.to_json()
    assert not jx is None

