from typing import Dict


class TrackerInfo:
    def __init__(self, filename: str, classname: str):
        self._filename = filename
        self._classname = classname
        self._passes = 0
        self._fails = 0

    def inc_passes(self):
        self._passes = self._passes + 1

    def inc_fails(self):
        self._fails = self._fails + 1

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def classname(self) -> str:
        return self._classname

    @property
    def passes(self) -> int:
        return self._passes

    @property
    def fails(self) -> int:
        return self._fails


assert_tracker: Dict[str, TrackerInfo] = {}


def get_tracker_entry(tracker, id, filename, classname):
    entry = tracker.get(id)
    if entry is None:
        entry = TrackerInfo(filename, classname)
        tracker[id] = entry
    return entry
