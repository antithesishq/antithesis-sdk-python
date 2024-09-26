""" Source Code Metadata

This module provides a class to contain
source code metadata for assertion callers.

"""

from typing import Union, Any
from inspect import FrameInfo


def _get_class_name(frame_info: Any) -> str:

    try:
        class_name = frame_info.f_locals["self"].__class__.__name__
    except KeyError:
        class_name = ""
    return class_name


#pylint: disable=too-many-instance-attributes
class LocationInfo:
    """Used to contain source code info obtained from assertion callers.

    Attributes:
        _filename (str): The name of the source file containing the called assertion
        _function (str): The name of the function containing the called assertion
        _class (str): The name of the class for the function containing the called assertion
        _begin_line (int): The line number for the called assertion
        _begin_col (int): The column number for the called assertion

    """

    def __init__(self, frame_info: Union[FrameInfo, None]) -> None:
        """Initializes a LocationInfo from an assertion caller's stack frame

        Args:
            frame_info (:obj:`FrameInfo`, optional): Assertion caller's stack frame info or None

        """

        self._filename = ""
        self._begin_line = 0
        self._begin_col = 0
        self._function = ""
        self._class = ""
        if frame_info is None:
            print("LocInfo not available")
            return
        self._filename = frame_info.filename
        self._begin_line = frame_info.lineno
        self._begin_col = 0
        self._function = frame_info.function
        self._class = _get_class_name(frame_info.frame)

    @property
    def classname(self) -> str:
        """str: The name of the class for the function containing the called assertion"""
        return self._class

    @classname.setter
    def classname(self, value: str) -> None:
        self._class = value

    @property
    def filename(self) -> str:
        """str: The name of the source file containing the called assertion"""
        return self._filename

    @filename.setter
    def filename(self, value: str) -> None:
        self._filename = value

    @property
    def function(self) -> str:
        """str: The name of the function containing the called assertion"""
        return self._function

    @function.setter
    def function(self, value: str) -> None:
        self._function = value

    @property
    def begin_line(self) -> int:
        """int: The line number for the called assertion"""
        return self._begin_line

    @begin_line.setter
    def begin_line(self, value: int) -> None:
        self._begin_line = value

    @property
    def begin_col(self) -> int:
        """int: The column number for the called assertion"""
        return self._begin_col

    @begin_col.setter
    def begin_col(self, value: int) -> None:
        self._begin_col = value
