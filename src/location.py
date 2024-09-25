from typing import Union
from inspect import FrameInfo


class LocationInfo:
    def __init__(self, tbk: Union[FrameInfo, None]) -> None:
        self._filename = "filename"
        self._begin_line = 0
        self._begin_col = 0
        self._function = "function"
        self._class = "class"
        if tbk is None:
            print("LocInfo not available")
            return
        # print("filename: '%s'  lineno: '%d'  function: '%s'" % (tbk.filename, tbk.lineno, tbk.function))
        self._filename = tbk.filename
        self._begin_line = tbk.lineno
        self._begin_col = 0
        self._function = tbk.function
        self._class = "?c_lass"

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
