""" Source Code Metadata

This module provides a dictionary to contain
source code metadata for assertion callers.

"""

from typing import Union, Any, Dict, Optional
from inspect import FrameInfo


def _get_class_name(frame_info: Any) -> str:
    try:
        class_name = frame_info.f_locals["self"].__class__.__name__
    except KeyError:
        class_name = ""
    return class_name


def _get_location_info(frame_info: Optional[FrameInfo]) -> Dict[str, Union[str, int]]:
    """Provides a dictionary containing source code info obtained from assertion callers.

    Args:
        frame_info (:obj:`FrameInfo`, optional): Assertion caller's stack frame info or None

    Returns:
        Dict[str, Union[str, int]]: a dictionary containing source code info
            obtained from assertion callers.

    """
    if frame_info is None:
        print("LocInfo not available")
        return {
            "file": "",
            "function": "",
            "class": "",
            "begin_line": 0,
            "begin_column": 0,
        }
    return {
        "file": frame_info.filename,
        "function": frame_info.function,
        "class": _get_class_name(frame_info.frame),
        "begin_line": frame_info.lineno,
        "begin_column": 0,
    }
