""" Source Code Metadata

This module provides a class to contain
source code metadata for assertion callers.

"""

from typing import Union, Any
from inspect import FrameInfo
import json


def _get_class_name(frame_info: Any) -> str:
    try:
        class_name = frame_info.f_locals["self"].__class__.__name__
    except KeyError:
        class_name = ""
    return class_name


# pylint: disable=too-few-public-methods
class LocationInfo:
    """Used to contain source code info obtained from assertion callers.

    Attributes:
        filename (str): The name of the source file containing the called assertion
        function (str): The name of the function containing the called assertion
        classname (str): The name of the class for the function containing the called assertion
        begin_line (int): The line number for the called assertion
        begin_column (int): The column number for the called assertion

    """

    def __init__(self, frame_info: Union[FrameInfo, None]) -> None:
        """Initializes a LocationInfo from an assertion caller's stack frame

        Args:
            frame_info (:obj:`FrameInfo`, optional): Assertion caller's stack frame info or None

        """

        self.filename = ""
        self.begin_line = 0
        self.begin_column = 0
        self.function = ""
        self.classname = ""
        if frame_info is None:
            print("LocInfo not available")
            return
        self.filename = frame_info.filename
        self.begin_line = frame_info.lineno
        self.begin_column = 0
        self.function = frame_info.function
        self.classname = _get_class_name(frame_info.frame)

    def to_json(self) -> str:
        """Provides a JSON representation of LocationInfo

        Returns:
            (str): A JSON representation of LocationInfo

        """
        return json.dumps(self, default=vars)
