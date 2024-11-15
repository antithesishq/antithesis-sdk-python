import json
from inspect import stack

import pytest
from antithesis._location import _get_location_info
from antithesis._assertinfo import AssertInfo, AssertionDisplay 

@pytest.fixture
def location_example():
    all_frames = stack()
    this_frame = all_frames[0]
    return _get_location_info(this_frame)

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

def test_assertion_info_to_json(location_example, details_example):

    assertion_display = AssertionDisplay.ALWAYS_OR_UNREACHABLE
    assert_type = assertion_display.assert_type()

    hit_value = True
    must_hit_value = False
    assertion_display_value = assertion_display.value
    assert_type_value = assert_type.value
    message_value = "The assertion message"
    condition_value = True
    assert_id_value = message_value
    loc_info_value = location_example
    details_value = details_example

    assert_info = AssertInfo(
        hit_value,
        must_hit_value,
        assert_type_value,
        assertion_display_value,
        message_value,
        condition_value,
        assert_id_value,
        loc_info_value,
        details_value
    )

    json_assert_info = json.dumps(assert_info.to_dict())
    decoded_assert_info = json.loads(json_assert_info)

    assert 'condition' in decoded_assert_info
    assert 'must_hit' in decoded_assert_info
    assert 'hit' in decoded_assert_info
    assert 'id' in decoded_assert_info
    assert 'message' in decoded_assert_info
    assert 'display_type' in decoded_assert_info
    assert 'assert_type' in decoded_assert_info
    assert 'location' in decoded_assert_info
    assert 'details' in decoded_assert_info

    assert decoded_assert_info['condition'] == condition_value
    assert decoded_assert_info['must_hit'] == must_hit_value
    assert decoded_assert_info['hit'] == hit_value
    assert decoded_assert_info['id'] == assert_id_value
    assert decoded_assert_info['message'] == message_value
    assert decoded_assert_info['display_type'] == assertion_display_value
    assert decoded_assert_info['assert_type'] == assert_type_value

    decoded_loc_value = decoded_assert_info['location']
    decoded_details_value = decoded_assert_info['details']
  
    for k,v in location_example.items():
        assert k in decoded_loc_value
        decoded_val = decoded_loc_value.get(k)
        assert not decoded_val is None
        assert decoded_val == v

    for k,v in details_example.items():
        assert k in decoded_details_value
        decoded_val = decoded_details_value.get(k)
        assert not decoded_val is None
        assert decoded_val == v
