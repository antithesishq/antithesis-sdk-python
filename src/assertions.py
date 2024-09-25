from enum import StrEnum
from typing import Any, Mapping, Union, Dict
from inspect import currentframe, getframeinfo, Traceback, stack

from assertinfo import AssertInfo, AssertionDisplay, AssertType
from location import LocationInfo
from tracking import assert_tracker, get_tracker_entry

was_hit = True
must_be_hit = True
optionally_hit = False
expecting_true = True

universal_test = AssertType.ALWAYS
existential_test = AssertType.SOMETIMES
reachability_test = AssertType.REACHABILITY


def emit_assert(ai: AssertInfo) -> None:
    if ai.hit:
        print("HIT: %s" % ai)
    else:
        print("REG: %s" % ai)


def assert_impl(
    cond: bool,
    message: str,
    details: Mapping[str, Any],
    loc: LocationInfo,
    hit: bool,
    must_hit: bool,
    assert_type: str,
    display_type: str,
    id: str,
):
    tracker_entry = get_tracker_entry(assert_tracker, id, loc.filename, loc.classname)

    # Always grab the filename and classname captured when the tracker_entry was established
    # This provides the consistency needed between instrumentation-time and runtime
    if loc.filename != tracker_entry.filename:
        loc.filename = tracker_entry.filename

    if loc.classname != tracker_entry.classname:
        loc.classname = tracker_entry.classname

    ai = AssertInfo(
        hit, must_hit, assert_type, display_type, message, cond, id, loc, details
    )

    if not hit:
        emit_assert(ai)
        return

    if cond:
        tracker_entry.inc_passes()
        if tracker_entry.passes == 1:
            emit_assert(ai)
    else:
        tracker_entry.inc_fails()
        if tracker_entry.fails == 1:
            emit_assert(ai)


def makeKey(message: str, loc_info: LocationInfo) -> str:
    return message


def always_or_unreachable(
    condition: bool, message: str, details: Mapping[str, Any]
) -> None:
    all_frames = stack()
    this_frame = all_frames[1]
    location_info = LocationInfo(this_frame)
    id = makeKey(message, location_info)
    assert_impl(
        condition,
        message,
        details,
        location_info,
        was_hit,
        optionally_hit,
        universal_test,
        AssertionDisplay.ALWAYS_OR_UNREACHABLE_DISPLAY,
        id,
    )


def sometimes(condition: bool, message: str, details: Mapping[str, Any]) -> None:
    all_frames = stack()
    this_frame = all_frames[1]
    location_info = LocationInfo(this_frame)
    id = makeKey(message, location_info)
    assert_impl(
        condition,
        message,
        details,
        location_info,
        was_hit,
        must_be_hit,
        existential_test,
        AssertionDisplay.SOMETIMES_DISPLAY,
        id,
    )


# ----------------------------------------------------------------------
# For project.scripts support
# ----------------------------------------------------------------------
import sys


def cmd_always():
    num_args = len(sys.argv)
    if num_args >= 3:
        message = (sys.argv[1]).strip()
        cond_text = (sys.argv[1]).strip().lower()
        for i in range(2, num_args):
            arg = sys.argv[i].lower()
            if arg == "t":
                condition = True
            else:
                condition = False
            always_or_unreachable(condition, message, {})


def cmd_sometimes():
    num_args = len(sys.argv)
    if num_args >= 3:
        message = (sys.argv[1]).strip()
        cond_text = (sys.argv[1]).strip().lower()
        for i in range(2, num_args):
            arg = sys.argv[i].lower()
            if arg == "t":
                condition = True
            else:
                condition = False
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
    print("Adding: %d + %d => %d" % (num1, num2, the_sum))


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
    print("Subtracting: %d - %d => %d" % (num1, num2, the_diff))
