""" Basic Assertion Information

This module contains classes used to contain
the details for basic assertions.

"""

from enum import StrEnum
from typing import Any, Mapping
from location import LocationInfo


class AssertType(StrEnum):
    """Used to differentiate type of basic assertions"""

    ALWAYS = "always"
    SOMETIMES = "sometimes"
    REACHABILITY = "reachability"


class AssertionDisplay(StrEnum):
    """Used to provide human readable names for basic assertions"""

    ALWAYS_DISPLAY = "Always"
    ALWAYS_OR_UNREACHABLE_DISPLAY = "AlwaysOrUnreachable"
    SOMETIMES_DISPLAY = "Sometimes"
    REACHABLE_DISPLAY = "Reachable"
    UNREACHABLE_DISPLAY = "Unreachable"


# pylint: disable=too-many-instance-attributes
class AssertInfo:
    """Used to contain assertion details.

    Attributes:
        _hit (bool): True for runtime assertions, False if from an Assertion Catalog
        _must_hit (bool): True if assertion must be hit at runtime
        _assert_type (AssertType): Logical handling type for a basic assertion
        _display_type (AssertionDisplay): Human readable name for a basic assertion
        _message (str): Unique message associated with a basic assertion
        _cond (bool): Runtime condition for the basic assertion
        _id (str): Unique id for the basic assertion
        _loc_info (LocationInfo): Caller information for the basic assertion (runtime and catalog)
        _details (Mapping[str, Any]): Named details associated with a basic assertion at runtime

    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        hit: bool,
        must_hit: bool,
        assert_type: str,
        display_type: str,
        message: str,
        cond: bool,
        assert_id: str,
        loc_info: LocationInfo,
        details: Mapping[str, Any],
    ) -> None:
        self._hit = hit
        self._must_hit = must_hit
        self._assert_type = assert_type
        self._display_type = display_type
        self._message = message
        self._cond = cond
        self._id = assert_id
        self._loc_info = loc_info
        self._details = details

    @property
    def hit(self) -> bool:
        return self._hit

    @property
    def must_hit(self) -> bool:
        return self._must_hit

    @property
    def assert_type(self) -> str:
        return self._assert_type

    @property
    def display_type(self) -> str:
        return self._display_type

    @property
    def message(self) -> str:
        return self._message

    @property
    def cond(self) -> bool:
        return self._cond

    @property
    def assert_id(self) -> str:
        return self._id

    @property
    def loc_info(self) -> LocationInfo:
        return self._loc_info

    @property
    def details(self) -> Mapping[str, Any]:
        return self._details

    def __str__(self):
        return f"{self.display_type} '{self.message}' => {self.cond}"
