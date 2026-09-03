""" Source Code Metadata

This module provides a dictionary to contain
source code metadata for assertion callers.

"""

from types import FrameType
from typing import Union, Dict, Optional


def _get_class_name(frame: FrameType) -> str:
    try:
        class_name = frame.f_locals["self"].__class__.__name__
    except KeyError:
        class_name = ""
    return class_name


def _get_location_info(frame: Optional[FrameType]) -> Dict[str, Union[str, int]]:
    """Provides a dictionary containing source code info obtained from assertion callers.

    Args:
        frame (:obj:`FrameType`, optional): Assertion caller's stack frame or None

    Returns:
        Dict[str, Union[str, int]]: a dictionary containing source code info
            obtained from assertion callers.

    """
    if frame is None:
        print("LocInfo not available")
        return {
            "file": "",
            "function": "",
            "class": "",
            "begin_line": 0,
            "begin_column": 0,
        }
    return {
        "file": frame.f_code.co_filename,
        "function": frame.f_code.co_name,
        "class": _get_class_name(frame),
        "begin_line": frame.f_lineno,
        "begin_column": 0,
    }
