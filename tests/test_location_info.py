import json
from inspect import stack
import pytest
from antithesis._location import _get_location_info

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
    return _get_location_info(this_frame)

def test_location_to_json(location_example):
    loc_info = json.dumps(location_example)
    decoded_loc_info = json.loads(loc_info)

    assert 'file' in decoded_loc_info
    assert 'function' in decoded_loc_info
    assert 'class' in decoded_loc_info
    assert 'begin_line' in decoded_loc_info
    assert 'begin_column' in decoded_loc_info

    decoded_file = decoded_loc_info['file']
    assert  decoded_file == __file__

    assert decoded_loc_info['function'] == 'location_example'
    assert decoded_loc_info['class'] == ''
    assert decoded_loc_info['begin_column'] == 0

class SomeClass:
    def __init__(self, value: int):
        self._value = value

    def get_frame_info(self):
        all_frames = stack()
        this_frame = all_frames[0]
        return this_frame

@pytest.fixture
def location_with_class_example():
    some_class = SomeClass(217)
    that_frame = some_class.get_frame_info()
    return _get_location_info(that_frame)

def test_location_has_class(location_with_class_example):
    loc_info = json.dumps(location_with_class_example)
    decoded_loc_info = json.loads(loc_info)

    assert 'file' in decoded_loc_info
    assert 'function' in decoded_loc_info
    assert 'class' in decoded_loc_info
    assert 'begin_line' in decoded_loc_info
    assert 'begin_column' in decoded_loc_info

    decoded_file = decoded_loc_info['file']
    assert  decoded_file == __file__

    assert decoded_loc_info['function'] == 'get_frame_info'
    assert decoded_loc_info['class'] == 'SomeClass'
