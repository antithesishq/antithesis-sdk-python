"""Details normalization and serialization shared by assertion and lifecycle records."""

import json
import threading
from collections.abc import Mapping
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Set

# JavaScript's Number.MAX_SAFE_INTEGER + 1: consumers parsing JSON numbers as
# doubles round anything at or beyond this magnitude.
_UNSAFE_INTEGER = 2**53
_warned_codes: Set[int] = set()
_warning_lock = threading.Lock()

# Under this table a sixteen-digit integer token becomes a space followed by
# sixteen ones. In json.dumps output an integer token follows a space (after
# ":" or ","), "[" or its own "-", so those bytes become a space and digits
# become "1". Every other byte becomes "0", in particular the "." before a
# fraction and the "e" or sign before an exponent, so the sixteen-digit
# mantissa of a computed double never matches.
_INTEGER_TOKEN_TABLE = bytes(
    0x31 if 0x30 <= byte <= 0x39 else 0x20 if byte in b" [-" else 0x30
    for byte in range(256)
)
_SIXTEEN_DIGIT_INTEGER = b" " + b"1" * 16

_WARNINGS = {
    6002: 'Python SDK replaced non-finite numbers in details for "{}" '
          'with the strings "NaN", "Infinity" or "-Infinity"',
    6003: 'Python SDK emitted integers beyond ±2^53 in details for "{}"; '
          'consumers that parse JSON numbers as doubles will round them',
    6004: 'Python SDK skipped numeric guidance for "{}" because an operand was not finite',
}


def details_object(details: Any) -> Optional[Mapping]:
    """Preserve objects and wrap other values without traversing user details."""
    if details is None or isinstance(details, Mapping):
        return details
    return {"value": details}


def _encode_mapping(value: Any) -> Dict:
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _may_warn(serialized: str) -> bool:
    """Whether the serialized record can contain anything the warnings are about.

    json writes non-finite floats as the tokens NaN, Infinity and -Infinity,
    and an integer of magnitude >= 2^53 has at least sixteen digits. Only
    integer tokens count: the shortest repr of nearly every computed double
    also carries sixteen digits, and firing on those made the walk the common
    case. Either can also occur inside a string; that only costs the walk,
    never a wrong answer. The record is an object, so no token starts the text.
    """
    return ("NaN" in serialized or "Infinity" in serialized
            or _SIXTEEN_DIGIT_INTEGER in serialized.encode().translate(_INTEGER_TOKEN_TABLE))


class _Inspection:
    """Warning codes found while json re-reads the text it produced.

    The record is parsed back rather than the caller's data walked again, so
    caller data is read exactly once per emission whatever the text says.
    json calls parse_int for every integer token and parse_constant for the
    NaN, Infinity and -Infinity tokens it wrote for non-finite floats; the
    latter are replaced by their spellings on the way in, so re-serializing
    the parsed record is the corrected output.
    """

    def __init__(self) -> None:
        self.codes: Set[int] = set()

    def parse_int(self, text: str) -> int:
        value = int(text)
        if abs(value) >= _UNSAFE_INTEGER:
            self.codes.add(6003)
        return value

    def parse_constant(self, name: str) -> str:
        self.codes.add(6002)
        return name


def _diagnostic(kind: str, code: int, message: str, context: str) -> str:
    return json.dumps({kind: {"code": code, "message": message, "context": context}})


def warn_once(code: int, context: str, output: Callable[[str], Any]) -> None:
    """Report a warning the first time this process has cause to."""
    with _warning_lock:
        if code in _warned_codes:
            return
        _warned_codes.add(code)
    message = _WARNINGS[code].format(context)
    message += "; later occurrences in this process are not reported"
    output(_diagnostic("antithesis_warning", code, message, context))


def _serialization_error(context: str, error: Exception) -> str:
    try:
        reason = str(error) or type(error).__name__
    except MemoryError:
        raise
    except Exception:  # A user __str__ can raise anything.
        reason = type(error).__name__
    return _diagnostic(
        "antithesis_error", 6001,
        f'Python SDK failed to serialize details for "{context}": {reason}', context,
    )


class SerializationFailure(Enum):
    OMIT_DETAILS = auto()
    EMPTY_DETAILS = auto()
    DROP_PACKET = auto()


def dispatch_guidance(
    record: Dict[str, Any],
    context: str,
    output: Callable[[str], Any],
) -> None:
    dispatch_with_details(record, record["antithesis_guidance"], "guidance_data", context, output,
                          on_error=SerializationFailure.DROP_PACKET)


def dispatch_with_details(
    record: Dict[str, Any],
    container: Dict[str, Any],
    key: str,
    context: str,
    output: Callable[[str], Any],
    on_error: SerializationFailure = SerializationFailure.OMIT_DETAILS,
) -> None:
    codes: Set[int] = set()
    try:
        serialized = json.dumps(record, default=_encode_mapping)
        # The C encoder cannot report numbers as it writes them, so the text it
        # produced is inspected instead, and only when a cheap test says there
        # may be something to find.
        if key in container and _may_warn(serialized):
            inspection = _Inspection()
            parsed = json.loads(serialized, parse_int=inspection.parse_int,
                                parse_constant=inspection.parse_constant)
            codes = inspection.codes
            if 6002 in codes:
                serialized = json.dumps(parsed)
    except MemoryError:
        raise
    except Exception as error:  # User Mapping implementations can raise arbitrary exceptions.
        if key not in container:
            raise
        output(_serialization_error(context, error))
        if on_error is SerializationFailure.DROP_PACKET:
            return
        if on_error is SerializationFailure.OMIT_DETAILS:
            del container[key]
        else:
            container[key] = {}
        serialized = json.dumps(record)
    else:
        for code in sorted(codes):
            warn_once(code, context, output)
    output(serialized)
