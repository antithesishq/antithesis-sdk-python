"""Guidance tracking and emission.

Guidance accompanies a rich assertion: alongside the assertion itself, the SDK
reports the values the assertion compared, so that Antithesis can steer
exploration toward the values most likely to flip it.

Numeric guidance requires finite operands. Only the most extreme `left - right`
gap seen so far for a guidance id reaches the wire, because that is the only one
that tells the platform something new. The gap itself can overflow to infinity.
Boolean guidance is never filtered.
"""

import math
import threading
from typing import Any, Callable, Dict, Mapping, Optional, Union

from ._details import warn_once

NUMERIC = "numeric"
BOOLEAN = "boolean"


class _NumericTracker:
    """The most extreme gap emitted so far for one guidance id.

    `maximize` is fixed when the entry is created, matching every other
    Antithesis SDK: a guidance id has one direction for the life of the process.
    """

    def __init__(self, maximize: bool):
        self._maximize = maximize
        # None until the first hit, which therefore always emits. A sentinel
        # would need a value more extreme than any gap, and there isn't one:
        # a gap can legitimately be infinite.
        self._mark: Optional[float] = None
        self._lock = threading.Lock()

    def should_emit(self, gap: float) -> bool:
        """Whether `gap` improves on the mark, updating it if so."""
        with self._lock:
            if self._mark is None:
                self._mark = gap
                return True
            if gap > self._mark if self._maximize else gap < self._mark:
                self._mark = gap
                return True
            return False


_numeric_trackers: Dict[str, _NumericTracker] = {}
_numeric_trackers_lock = threading.Lock()


def _numeric_tracker(guidance_id: str, maximize: bool) -> _NumericTracker:
    """The tracker for `guidance_id`, created on first use."""
    tracker = _numeric_trackers.get(guidance_id)
    if tracker is not None:
        return tracker
    with _numeric_trackers_lock:
        # setdefault, not assignment: two threads racing the first call for an
        # id must agree on one tracker.
        return _numeric_trackers.setdefault(guidance_id, _NumericTracker(maximize))


def should_emit_numeric(
    guidance_id: str, maximize: bool, left: Any, right: Any, output: Callable[[str], Any]
) -> bool:
    """Whether finite operands improve this id's gap after conversion to doubles.

    Non-finite operands never do; the guidance they suppress is replaced by a
    warning on `output`, so the wire records why nothing came.
    """
    left, right = float(left), float(right)
    if not math.isfinite(left) or not math.isfinite(right):
        warn_once(6004, guidance_id, output)
        return False
    return _numeric_tracker(guidance_id, maximize).should_emit(left - right)


def guidance_info(
    guidance_type: str,
    guidance_id: str,
    message: str,
    loc_info: Dict[str, Union[str, int]],
    maximize: bool,
    hit: bool,
    guidance_data: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """The wire representation of one guidance record."""
    the_dict: Dict[str, Any] = {
        "guidance_type": guidance_type,
        "id": guidance_id,
        "message": message,
        "location": loc_info,
        "maximize": maximize,
        "hit": hit,
    }
    if hit and guidance_data is not None:
        the_dict["guidance_data"] = guidance_data
    return the_dict
