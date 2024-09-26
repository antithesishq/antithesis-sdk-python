import json
from inspect import stack
import pytest
from location import get_location_info

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
    return get_location_info(this_frame)

def test_location_to_json(location_example):
    loc_info = json.dumps(location_example)
    decoded_loc_info = json.loads(loc_info)

    assert 'filename' in decoded_loc_info
    assert 'function' in decoded_loc_info
    assert 'class' in decoded_loc_info
    assert 'begin_line' in decoded_loc_info
    assert 'begin_column' in decoded_loc_info

    decoded_filename = decoded_loc_info['filename']
    assert  decoded_filename == __file__

    assert decoded_loc_info['function'] == 'location_example'
    assert decoded_loc_info['class'] == ''
    assert decoded_loc_info['begin_column'] == 0
