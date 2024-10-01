""" Basic Assertion Tracking
This module provides a class to track
assertion usage, including pass/fail counts,
catalog entries and some assertion
metadata that needs to be consistent between
the assertion catalog and runtime occurences

Attributes:

    assert_tracker (Dict[str, TrackerInfo]): Dictionary keyed by
        assert_id for assertions cataloged and encountered. Each
        entry in the dictionary contains TrackerInfo for an assertion.

"""

from typing import Dict


class TrackerInfo:
    """Used to contain assertion runtime usage.

    Attributes:
        _filename (str): The name of the source file containing the called assertion
        _classname (str): The name of the class for the function containing the called assertion
        _passes (int): The number of runtime assertions encountered with condition True
        _fails (int): The number of runtime assertions encountered with condition False

    """

    def __init__(self, filename: str, classname: str):
        """Initializes a TrackerInfo with filename and classname of the associated
        basic assertion.

        Args:
            filename (str): The name of the source file containing the called assertion
            classname (str): The name of the class for the function containing the called assertion

        """
        self._filename = filename
        self._classname = classname
        self._passes = 0
        self._fails = 0

    def inc_passes(self):
        """Increments the total number of passed assertions encountered"""
        self._passes = self._passes + 1

    def inc_fails(self):
        """Increments the total number of failed assertions encountered"""
        self._fails = self._fails + 1

    @property
    def filename(self) -> str:
        """str: The name of the source file containing the called assertion"""
        return self._filename

    @property
    def classname(self) -> str:
        """str: The name of the class for the function containing the called assertion"""
        return self._classname

    @property
    def passes(self) -> int:
        """int: The total number of passed assertions encountered at runtime"""
        return self._passes

    @property
    def fails(self) -> int:
        """int: The total number of failed assertions encountered at runtime"""
        return self._fails


assert_tracker: Dict[str, TrackerInfo] = {}


def get_tracker_entry(
    tracker: Dict[str, TrackerInfo], assert_id: str, filename: str, classname: str
) -> TrackerInfo:
    """Provides the TrackerInfo associated with the assert_id specified.
    If this is the first time the assert_id has been encountered, the
    TrackerInfo is created with the filename and classname given, and
    the pass and fail counts initialized to zero.

    Args:
        tracker (Dict[str, TrackerInfo]): The assertion tracker used to
            obtain existing TrackerInfo entries, and to insert newly
            initialized TrackerInfo entries.
        assert_id (str): The assert_id for an assertion whose TrackerInfo
            is to be obtained
        filename (str): The name of the source file containing the called assertion
        classname (str): The name of the class for the function containing the called assertion
    """
    entry = tracker.get(assert_id)
    if entry is None:
        entry = TrackerInfo(filename, classname)
        tracker[assert_id] = entry
    return entry
