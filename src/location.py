from typing import Union, Any
from inspect import FrameInfo


def get_class_name(frame_info: Any) -> str:
    try:
        class_name = frame_info.f_locals["self"].__class__.__name__
    except Exception:
        class_name = "?class"
    return class_name


class LocationInfo:
    def __init__(self, frame_info: Union[FrameInfo, None]) -> None:
        self._filename = "filename"
        self._begin_line = 0
        self._begin_col = 0
        self._function = "function"
        self._class = "class"
        if frame_info is None:
            print("LocInfo not available")
            return
        # print("filename: '%s'  lineno: '%d'  function: '%s'" % (frame_info.filename, frame_info.lineno, frame_info.function))
        self._filename = frame_info.filename
        self._begin_line = frame_info.lineno
        self._begin_col = 0
        self._function = frame_info.function
        self._class = get_class_name(frame_info.frame)

    @property
    def classname(self) -> str:
        return self._class

    @classname.setter
    def classname(self, value: str) -> None:
        self._class = value

    @property
    def filename(self) -> str:
        return self._filename

    @filename.setter
    def filename(self, value: str) -> None:
        self._filename = value

    @property
    def function(self) -> str:
        return self._function

    @property
    def begin_line(self) -> int:
        return self._begin_line

    @property
    def begin_col(self) -> int:
        return self._begin_col
