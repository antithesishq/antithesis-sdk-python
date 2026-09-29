""" Basic Assertion Information

This module contains classes used to contain
the details for basic assertions.

"""

#from enum import StrEnum
from enum import Enum
from typing import Any, Mapping, Union, Dict, Optional

from ._details import details_object


class AssertType(str, Enum):
    """Used to differentiate type of basic assertions"""

    ALWAYS = "always"
    SOMETIMES = "sometimes"
    REACHABILITY = "reachability"


class AssertionKind(str, Enum):
    """Which assertion function a declaration came from.

    This is the typed form of the ``display_type`` field of serialized
    assertion events; the enum value is that string, which is also how the
    triage report labels the property. It is distinct from `AssertType`,
    the three-way wire-level type, which cannot tell `always` from
    `always_or_unreachable`, or `reachable` from `unreachable`, without
    also consulting ``must_hit``.
    """

    ALWAYS = "Always"
    ALWAYS_OR_UNREACHABLE = "AlwaysOrUnreachable"
    SOMETIMES = "Sometimes"
    REACHABLE = "Reachable"
    UNREACHABLE = "Unreachable"

    @property
    def display_type(self) -> str:
        """str: The ``display_type`` string serialized events carry for this kind."""
        return self.value

    @property
    def assert_type(self) -> AssertType:
        """AssertType: The wire-level assertion type for this kind."""
        if self in (AssertionKind.ALWAYS, AssertionKind.ALWAYS_OR_UNREACHABLE):
            return AssertType.ALWAYS
        if self == AssertionKind.SOMETIMES:
            return AssertType.SOMETIMES
        return AssertType.REACHABILITY

    @property
    def must_hit(self) -> bool:
        """bool: Whether the property fails when the assertion is never reached."""
        return self in (
            AssertionKind.ALWAYS,
            AssertionKind.SOMETIMES,
            AssertionKind.REACHABLE,
        )


# pylint: disable=too-many-instance-attributes
class AssertInfo:
    """Used to contain assertion details.

    Attributes:
        _hit (bool): True for runtime assertions, False if from an Assertion Catalog
        _must_hit (bool): True if assertion must be hit at runtime
        _assert_type (str): Logical handling type for a basic assertion
        _display_type (str): Human readable name for a basic assertion
        _message (str): Unique message associated with a basic assertion
        _condition (bool): Runtime condition for the basic assertion
        _id (str): Unique id for the basic assertion
        _loc_info (Dict[str, Union[str, int]]): Caller information for the basic
            assertion (runtime and catalog)
        _details (Mapping[str, Any]): Named details associated with a basic
            assertion at runtime

    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        hit: bool,
        must_hit: bool,
        assert_type: str,
        display_type: str,
        message: str,
        condition: bool,
        assert_id: str,
        loc_info: Dict[str, Union[str, int]],
        details: Optional[Mapping[str, Any]],
    ) -> None:
        self._hit = hit
        self._must_hit = must_hit
        self._assert_type = assert_type
        self._display_type = display_type
        self._message = message
        self._condition = condition
        self._id = assert_id
        self._loc_info = loc_info
        self._details = details

    @property
    def hit(self) -> bool:
        """bool: True for runtime assertions, False if from an Assertion Catalog"""
        return self._hit

    @property
    def must_hit(self) -> bool:
        """bool: True if assertion must be hit at runtime"""
        return self._must_hit

    @property
    def assert_type(self) -> str:
        """str: Logical handling type for a basic assertion"""
        return self._assert_type

    @property
    def display_type(self) -> str:
        """str: Human readable name for a basic assertion"""
        return self._display_type

    @property
    def message(self) -> str:
        """str: Unique message associated with a basic assertion"""
        return self._message

    @property
    def condition(self) -> bool:
        """bool: Runtime condition for the basic assertion"""
        return self._condition

    @property
    def assert_id(self) -> str:
        """str: Unique id for the basic assertion"""
        return self._id

    @property
    def loc_info(self) -> Dict[str, Union[str, int]]:
        """Dict[str, Union[str, int]]: Basic Assertion caller information
        (runtime and catalog)
        """
        return self._loc_info

    @property
    def details(self) -> Optional[Mapping[str, Any]]:
        """Mapping[str, Any]: Named details associated with a basic assertion
        at runtime
        """
        return self._details

    def __str__(self):
        """The informal printable string representation of an AssertInfo object.

        Returns:
            str: The informal printable string representation of an AssertInfo object.
        """
        return f"{self.display_type} '{self.message}' => {self.condition}"

    def to_dict(self) -> Dict[str, Any]:
        """A dictionary representation of an AssertInfo object

        Returns:
            Dict[str, Any]: The dictionary representation of an AssertInfo object.
        """
        the_dict = {
            "condition": self.condition,
            "must_hit": self.must_hit,
            "hit": self.hit,
            "id": self.assert_id,
            "message": self.message,
            "display_type": self.display_type,
            "assert_type": self.assert_type,
            "location": self.loc_info,
        }
        if self.hit and self.details is not None:
            the_dict["details"] = details_object(self.details)
        return the_dict
