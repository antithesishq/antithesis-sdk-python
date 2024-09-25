"""Basic Assertions

This module provides functions for basic assertions:
    * always
    * always_or_unreachable
    * sometimes
    * reachable
    * unreachable

"""

from typing import Any, Mapping
from inspect import stack
import sys

from assertinfo import AssertInfo, AssertionDisplay, AssertType
from location import LocationInfo
from tracking import assert_tracker, get_tracker_entry

WAS_HIT = True  # Assertion was reached at runtime
MUST_BE_HIT = True  # Assertion must be reached at least once
OPTIONALLY_HIT = False  # Assertion may or may not be reachable
EXPECTING_TRUE = True  # Assertion condition should be True

UNIVERSAL_TEST = AssertType.ALWAYS  # Assertion condition must always be True
EXISTENTIAL_TEST = (
    AssertType.SOMETIMES
)  # Assertion condition must be True at least once
REACHABILITY_TEST = AssertType.REACHABILITY  # Assertion is for reachability only


def emit_assert(assert_info: AssertInfo) -> None:
    if assert_info.hit:
        print(f"HIT: {assert_info}")
    else:
        print(f"REG: {assert_info}")


# pylint: disable=too-many-arguments
def assert_impl(
    cond: bool,
    message: str,
    details: Mapping[str, Any],
    loc: LocationInfo,
    hit: bool,
    must_hit: bool,
    assert_type: str,
    display_type: str,
    assert_id: str,
):
    tracker_entry = get_tracker_entry(
        assert_tracker, assert_id, loc.filename, loc.classname
    )

    # Always grab the filename and classname captured when the tracker_entry was established
    # This provides the consistency needed between instrumentation-time and runtime
    if loc.filename != tracker_entry.filename:
        loc.filename = tracker_entry.filename

    if loc.classname != tracker_entry.classname:
        loc.classname = tracker_entry.classname

    assert_info = AssertInfo(
        hit, must_hit, assert_type, display_type, message, cond, assert_id, loc, details
    )

    if not hit:
        emit_assert(assert_info)
        return

    if cond:
        tracker_entry.inc_passes()
        if tracker_entry.passes == 1:
            emit_assert(assert_info)
    else:
        tracker_entry.inc_fassert_infols()
        if tracker_entry.fassert_infols == 1:
            emit_assert(assert_info)


def make_key(message: str, _loc_info: LocationInfo) -> str:
    return message


def always_or_unreachable(
    condition: bool, message: str, details: Mapping[str, Any]
) -> None:
    all_frames = stack()
    this_frame = all_frames[1]
    location_info = LocationInfo(this_frame)
    assert_id = make_key(message, location_info)
    assert_impl(
        condition,
        message,
        details,
        location_info,
        WAS_HIT,
        OPTIONALLY_HIT,
        UNIVERSAL_TEST,
        AssertionDisplay.ALWAYS_OR_UNREACHABLE_DISPLAY,
        assert_id,
    )


def sometimes(condition: bool, message: str, details: Mapping[str, Any]) -> None:
    all_frames = stack()
    this_frame = all_frames[1]
    location_info = LocationInfo(this_frame)
    assert_id = make_key(message, location_info)
    assert_impl(
        condition,
        message,
        details,
        location_info,
        WAS_HIT,
        MUST_BE_HIT,
        EXISTENTIAL_TEST,
        AssertionDisplay.SOMETIMES_DISPLAY,
        assert_id,
    )


# ----------------------------------------------------------------------
# For project.scripts support
# ----------------------------------------------------------------------


def cmd_always():
    num_args = len(sys.argv)
    if num_args >= 3:
        message = (sys.argv[1]).strip()
        for i in range(2, num_args):
            arg = sys.argv[i].lower()
            condition = bool(arg == "t")
            always_or_unreachable(condition, message, {})


def cmd_sometimes():
    num_args = len(sys.argv)
    if num_args >= 3:
        message = (sys.argv[1]).strip()
        for i in range(2, num_args):
            arg = sys.argv[i].lower()
            condition = bool(arg == "t")
            sometimes(condition, message, {})


def add():
    num1 = 0
    num2 = 0
    if len(sys.argv) > 1:
        maybe_num1 = sys.argv[1]
        if maybe_num1.isdigit():
            num1 = int(maybe_num1)

    if len(sys.argv) > 2:
        maybe_num2 = sys.argv[2]
        if maybe_num2.isdigit():
            num2 = int(maybe_num2)

    the_sum = num1 + num2
    print(f"Adding: {num1} + {num2} => {the_sum}")


def sub():
    num1 = 0
    num2 = 0
    if len(sys.argv) > 1:
        maybe_num1 = sys.argv[1]
        if maybe_num1.isdigit():
            num1 = int(maybe_num1)

    if len(sys.argv) > 2:
        maybe_num2 = sys.argv[2]
        if maybe_num2.isdigit():
            num2 = int(maybe_num2)

    the_diff = num1 - num2
    print(f"Subtracting: {num1} - {num2} => {the_diff}")
