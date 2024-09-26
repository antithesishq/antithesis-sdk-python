""" Source Code Metadata

This module provides a dictionary to contain
source code metadata for assertion callers.

"""

from typing import Union, Any, Dict
from inspect import FrameInfo
import json


def _get_class_name(frame_info: Any) -> str:
    try:
        class_name = frame_info.f_locals["self"].__class__.__name__
    except KeyError:
        class_name = ""
    return class_name


def get_location_info(frame_info: Union[FrameInfo, None]) -> Dict[str, Union[str, int]]:
    """Provides a dictionary containing source code info obtained from assertion callers.

    Args:
        frame_info (:obj:`FrameInfo`, optional): Assertion caller's stack frame info or None

    Returns:
        (Dict[str, Union[str, int]]): a dictionary containing source code info
            obtained from assertion callers.

    """
    if frame_info is None:
        print("LocInfo not available")
        return {
            "filename": "",
            "function": "",
            "class": "",
            "begin_line": 0,
            "begin_column": 0,
        }
    return {
        "filename": frame_info.filename,
        "function": frame_info.function,
        "class": _get_class_name(frame_info.frame),
        "begin_line": frame_info.lineno,
        "begin_column": 0,
    }


# [PH] # pylint: disable=too-few-public-methods
# [PH] class LocationInfo:
# [PH]     """Used to contain source code info obtained from assertion callers.
# [PH]
# [PH]     Attributes:
# [PH]         filename (str): The name of the source file containing the called assertion
# [PH]         function (str): The name of the function containing the called assertion
# [PH]         classname (str): The name of the class for the function containing the called assertion
# [PH]         begin_line (int): The line number for the called assertion
# [PH]         begin_column (int): The column number for the called assertion
# [PH]
# [PH]     """
# [PH]
# [PH]     def __init__(self, frame_info: Union[FrameInfo, None]) -> None:
# [PH]         """Initializes a LocationInfo from an assertion caller's stack frame
# [PH]
# [PH]         Args:
# [PH]             frame_info (:obj:`FrameInfo`, optional): Assertion caller's stack frame info or None
# [PH]
# [PH]         """
# [PH]         self.filename = ""
# [PH]         self.begin_line = 0
# [PH]         self.begin_column = 0
# [PH]         self.function = ""
# [PH]         self.classname = ""
# [PH]         if frame_info is None:
# [PH]             return
# [PH]         self.filename = frame_info.filename
# [PH]         self.begin_line = frame_info.lineno
# [PH]         self.begin_column = 0
# [PH]         self.function = frame_info.function
# [PH]         self.classname = _get_class_name(frame_info.frame)
# [PH]
# [PH]     def to_json(self) -> str:
# [PH]         """Provides a JSON representation of LocationInfo
# [PH]
# [PH]         Returns:
# [PH]             (str): A JSON representation of LocationInfo
# [PH]
# [PH]         """
# [PH]         return json.dumps(self, default=vars)
