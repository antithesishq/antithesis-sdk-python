from enum import StrEnum

from typing import Any, Mapping, Union

from inspect import currentframe, getframeinfo, Traceback, stack

# [PH] for project.scripts support
import sys


was_hit = True
must_be_hit = True
optionally_hit = False
expecting_true = True

universal_test = 'always'
existential_test  = 'sometimes'
reachability_test = 'reachability'

tracker_entry = None

class AssertionDisplay(StrEnum):
    ALWAYS_DISPLAY = 'Always'
    ALWAYS_OR_UNREACHABLE_DISPLAY = 'AlwaysOrUnreachable'
    SOMETIMES_DISPLAY = 'Sometimes'
    REACHABLE_DISPLAY = 'Reachable'
    UNREACHABLE_DISPLAY = 'Unreachable'

class LocationInfo():
    def __init__(self, tbk: Union[Traceback, None]) -> None:
        self._filename = 'filename'
        self._begin_line = 0
        self._begin_col = 0
        self._function = 'function'
        self._class = 'class'
        if tbk is None:
            print("LocInfo not available")
            return
        print("filename: '%s'  lineno: '%d'  function: '%s'" % (tbk.filename, tbk.lineno, tbk.function))
        self._filename = tbk.filename
        self._begin_line = tbk.lineno
        self._begin_col = 0
        self._function = tbk.function
        self._class = '?c_lass'

    @property
    def filename(self):
        return self._filename

    @property
    def function(self):
        return self._function

    @property
    def begin_line(self):
        return self._begin_line

    @property
    def begin_col(self):
        return self._begin_col


def assert_impl(
    cond: bool,
    message: str,
    details: Mapping[str, Any],
    loc: LocationInfo,
    hit: bool,
    must_hit: bool,
    assert_type: str,
    display_type: str,
    id: str
):
	tracker_entry = assert_tracker.get_tracker_entry(id, loc.filename, loc.classname)

	# Always grab the filename and classname captured when the tracker_entry was established
	# This provides the consistency needed between instrumentation-time and runtime
	if loc.filename != tracker_entry.filename:
		loc.filename = tracker_entry.filename
	
	
	if loc.classname != tracker_entry.classname:
		loc.classname = tracker_entry.classname
	
	# aI = AssertInfo(
	# 	hit,
	# 	mustHit,
	# 	assertType,
	# 	displayType,
	# 	message,
	# 	cond,
	# 	id,
	# 	loc,
	# 	details
	# )

	#tracker_entry.emit(aI)

def makeKey(message: str, loc_info: LocationInfo) -> str:
    return message

def always_or_unreachable(condition: bool, message: str, details: Mapping[str, Any] ) -> None:
	all_frames = stack()
	this_frame = all_frames[1]
	location_info = LocationInfo(this_frame)
    id = makeKey(message, location_info)
assert_impl(condition, message, details, location_info, was_hit, optionally_hit, universal_test, AssertionDisplay.ALWAYS_OR_UNREACHABLE_DISPLAY, id)

def cmd_always_or():
    if len(sys.argv) >= 3:
        cond_text = (sys.argv[1]).strip().lower()
        message = (sys.argv[2]).strip()
        condition = False
        if cond_text == "true":
            condition = True
        always_or_unreachable(condition, message, {})

if __name__ == "__main__":
    always_or_unreachable(True, "it works", {})
