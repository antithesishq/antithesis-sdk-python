from enum import StrEnum
from typing import Any, Mapping

from location import LocationInfo


class AssertType(StrEnum):
    ALWAYS = "always"
    SOMETIMES = "sometimes"
    REACHABILITY = "reachability"


class AssertionDisplay(StrEnum):
    ALWAYS_DISPLAY = "Always"
    ALWAYS_OR_UNREACHABLE_DISPLAY = "AlwaysOrUnreachable"
    SOMETIMES_DISPLAY = "Sometimes"
    REACHABLE_DISPLAY = "Reachable"
    UNREACHABLE_DISPLAY = "Unreachable"


class AssertInfo:
    def __init__(
        self,
        hit: bool,
        must_hit: bool,
        assert_type: str,
        display_type: str,
        message: str,
        cond: bool,
        id: str,
        loc_info: LocationInfo,
        details: Mapping[str, Any],
    ) -> None:
        self._hit = hit
        self._must_hit = must_hit
        self._assert_type = assert_type
        self._display_type = display_type
        self._message = message
        self._cond = cond
        self._id = id
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
    def id(self) -> str:
        return self._id

    @property
    def loc_info(self) -> LocationInfo:
        return self._loc_info

    @property
    def details(self) -> Mapping[str, Any]:
        return self._details

    def __str__(self):
        return "%s '%s' => %s" % (self.display_type, self.message, self.cond)
