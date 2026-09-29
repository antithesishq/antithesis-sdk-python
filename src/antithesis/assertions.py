"""This module provides functions for basic assertions:
    * always
    * always_or_unreachable
    * sometimes
    * reachable
    * unreachable

and for rich assertions, which additionally tell Antithesis the values the
assertion compared so it can steer toward the ones most likely to flip it:
    * always_greater_than, always_greater_than_or_equal_to
    * always_less_than, always_less_than_or_equal_to
    * sometimes_greater_than, sometimes_greater_than_or_equal_to
    * sometimes_less_than, sometimes_less_than_or_equal_to
    * always_some
    * sometimes_all

This module allows you to define 
[properties](https://antithesis.com/docs/properties_assertions/properties/) 
about your program or [test template](https://antithesis.com/docs/test_templates/first_test/).
It's part of the [Antithesis Python SDK](https://antithesis.com/docs/using_antithesis/sdk/python/),
which enables Python applications to integrate with the 
[Antithesis platform](https://antithesis.com/).

These functions are no-ops with minimal performance overhead when called outside of
the Antithesis environment. However, if the environment variable `ANTITHESIS_SDK_LOCAL_OUTPUT`
is set, these functions will log to the file pointed to by that variable using a structured
JSON format defined [here](https://antithesis.com/docs/using_antithesis/sdk/fallback/).
This allows you to make use of the Antithesis assertions package in your regular testing,
or even in production. In particular, very few assertions frameworks offer a convenient way to 
define [Sometimes assertions](https://antithesis.com/docs/best_practices/sometimes_assertions/), 
but they can be quite useful even outside Antithesis. To enumerate the assertions your
code declares -- including ones a local run never reaches -- see `antithesis.catalog`.

Each function in this package takes a parameter called `message`, which is a human
readable identifier used to aggregate assertions. Antithesis generates one test
property per unique `message` and this test property will be named "\\<message\\>" in
the [triage report](https://antithesis.com/docs/reports/). Different
assertions in different parts of the code should have a different `message`, but
the same assertion should always have the same `message` even if it is moved to
a different file.

Each function also takes a parameter called `details`, which is a key-value map of
optional additional information provided by the user to add context for assertion
failures. The information logged will appear in the 
[triage report](https://antithesis.com/docs/reports/), under
the details section of the corresponding property. Normally the values passed to
`details` are evaluated on every call, but serialized only when emitting.
Omit `details` or pass `None` for no details; an explicit empty mapping is preserved.
Other values are wrapped under `value`. If details
cannot be serialized, the SDK reports `antithesis_error` identifying the assertion
ID and emits the assertion without details.

"""

from typing import Any, Mapping, Union, Dict, Optional, cast
from inspect import currentframe

import json
import os

from antithesis._internal import (
    dispatch_output,
    ASSERTION_CATALOG_ENV_VAR,
    ASSERTION_CATALOG_NAME,
)
from ._details import details_object, dispatch_guidance, dispatch_with_details
from ._assertinfo import AssertInfo, AssertionKind
from ._guidance import (
    BOOLEAN,
    NUMERIC,
    guidance_info,
    should_emit_numeric,
)
from ._location import _get_location_info
from ._tracking import assert_tracker, get_tracker_entry

_WAS_HIT = True  # Assertion was reached at runtime
_MUST_BE_HIT = True  # Assertion must be reached at least once
_OPTIONALLY_HIT = False  # Assertion may or may not be reachable
_ASSERTING_TRUE = True  # Assertion condition should be True
_ASSERTING_FALSE = False  # Assertion condition should be False


def _emit_assert(assert_info: AssertInfo) -> None:
    """Formats and forwards the assertion provided to the
    presently configured handler.

    Args:
        assert_info (AssertInfo): The internal representation for a Basic Assertion
    """

    wrapped_assert = {"antithesis_assert": assert_info.to_dict()}
    dispatch_with_details(
        wrapped_assert, wrapped_assert["antithesis_assert"], "details",
        assert_info.assert_id, dispatch_output,
    )


# pylint: disable=too-many-arguments
def _assert_impl(
    cond: bool,
    message: str,
    details: Optional[Mapping[str, Any]],
    loc_info: Dict[str, Union[str, int]],
    hit: bool,
    must_hit: bool,
    assert_type: str,
    display_type: str,
    assert_id: str,
):
    """Composes, tracks, and emits assertions that should be forwarded
    to the configured handler.

    Args:
        cond (bool): Runtime condition for the basic assertion
        message (str): Unique message associated with a basic assertion
        details (Optional[Mapping[str, Any]]): Named details associated with a basic
            assertion at runtime
        loc_info (Dict[str, Union[str, int]]): Caller information for the basic
            assertion (runtime and catalog)
        hit (bool): True for runtime assertions, False if from an Assertion Catalog
        must_hit (bool): True if assertion must be hit at runtime
        assert_type (AssertType): Logical handling type for a basic assertion
        display_type (AssertionKind): Human readable name for a basic assertion
        assert_id (str): Unique id for the basic assertion
    """
    filename = cast(str, loc_info.get("file", ""))
    classname = cast(str, loc_info.get("class", ""))
    tracker_entry = get_tracker_entry(assert_tracker, assert_id, filename, classname)

    # Always grab the filename and classname captured when the tracker_entry was established
    # This provides the consistency needed between instrumentation-time and runtime
    if filename != tracker_entry.filename:
        loc_info["file"] = tracker_entry.filename

    if classname != tracker_entry.classname:
        loc_info["class"] = tracker_entry.classname

    if hit:
        count = tracker_entry.inc_passes() if cond else tracker_entry.inc_fails()
        if count != 1:
            return

    assert_info = AssertInfo(
        hit,
        must_hit,
        assert_type,
        display_type,
        message,
        cond,
        assert_id,
        loc_info,
        details,
    )
    _emit_assert(assert_info)


def _hit_assert(
    condition: bool,
    message: str,
    details: Optional[Mapping[str, Any]],
    display_type: AssertionKind,
    must_hit: bool,
) -> None:
    """Common runtime path for the public assertion functions. The tracker is
    keyed by `message`. When the tracker shows this assertion should not emit,
    just bump the counter.
    """
    entry = assert_tracker.get(message)
    if entry is not None and (entry.passes if condition else entry.fails) > 0:
        if condition:
            entry.inc_passes()
        else:
            entry.inc_fails()
        return

    # Two frames up from here is the caller of the public assertion function.
    # currentframe() can return None on implementations without frame support;
    # _get_location_info(None) emits an empty location.
    frame = currentframe()
    caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
    location_info = _get_location_info(caller)
    _assert_impl(
        condition,
        message,
        details,
        location_info,
        _WAS_HIT,
        must_hit,
        display_type.assert_type,
        display_type,
        message,
    )


def always(condition: bool, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
    """Asserts that `condition` is true every time this function
    is called. This test property will be viewable in the
    “Antithesis SDK: Always” group of your triage report.

    Args:
        condition (bool): Indicates if the assertion is true
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _hit_assert(condition, message, details, AssertionKind.ALWAYS, _MUST_BE_HIT)


def always_or_unreachable(
    condition: bool, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `condition` is true every time this function
    is called. The corresponding test property will pass if the
    assertion is never encountered. This test property will be
    viewable in the “Antithesis SDK: Always” group of your triage
    report.

    Args:
        condition (bool): Indicates if the assertion is true
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _hit_assert(
        condition, message, details, AssertionKind.ALWAYS_OR_UNREACHABLE, _OPTIONALLY_HIT
    )


def sometimes(condition: bool, message: str, details: Optional[Mapping[str, Any]] = None) -> None:
    """Asserts that `condition` is true at least one time that this function
    was called. (If the assertion is never encountered, the test property
    will therefore fail.) This test property will be viewable in the
    “Antithesis SDK: Sometimes” group.

    Args:
        condition (bool): Indicates if the assertion is true
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _hit_assert(condition, message, details, AssertionKind.SOMETIMES, _MUST_BE_HIT)


def reachable(message: str, details: Optional[Mapping[str, Any]] = None) -> None:
    """Reachable asserts that a line of code is reached at least
    once. The corresponding test property will pass if this function
    is ever called. (If it is never called the test property will
    therefore fail.) This test property will be viewable in the
    “Antithesis SDK: Reachablity assertions” group.

    Args:
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _hit_assert(
        _ASSERTING_TRUE, message, details, AssertionKind.REACHABLE, _MUST_BE_HIT
    )


def unreachable(message: str, details: Optional[Mapping[str, Any]] = None) -> None:
    """Unreachable asserts that a line of code is never reached.
    The corresponding test property will fail if this function
    is ever called. (If it is never called the test property will
    therefore pass.) This test property will be viewable in the
    “Antithesis SDK: Reachablity assertions” group.

    Args:
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _hit_assert(
        _ASSERTING_FALSE, message, details, AssertionKind.UNREACHABLE, _OPTIONALLY_HIT
    )


# pylint: disable=too-many-arguments
def assert_raw(
    condition: bool,
    message: str,
    details: Optional[Mapping[str, Any]],
    loc_filename: str,
    loc_function: str,
    loc_class: str,
    loc_begin_line: int,
    loc_begin_column: int,
    hit: bool,
    must_hit: bool,
    assert_type: str,
    display_type: str,
    assert_id: str,
    guidance_data: Optional[Mapping[str, Any]] = None,
):
    """This is a low-level method designed to be used by third-party frameworks.
    Regular users of the assertions module should not call it.

    This is primarily intended for use by adapters from other
    diagnostic tools that intend to output Antithesis-style
    assertions.

    Be certain to provide an assertion catalog entry
    for each assertion issued with `rawAssert()`.  Assertion catalog
    entries are also created using `rawAssert()`, by setting the value
    of the `hit` parameter to false.

    Please refer to the general Antithesis documentation regarding the use of the
    [Fallback SDK](https://antithesis.com/docs/using_antithesis/sdk/fallback/)
    for additional information.

    Args:
        condition (bool): Runtime condition for the basic assertion
        message (str): Unique message associated with a basic assertion
        details (Optional[Mapping[str, Any]]): Named details associated with a basic assertion at runtime
        loc_filename (str): The name of the source file containing the called assertion
        loc_function (str): The name of the function containing the called assertion
        loc_class (str): The name of the class for the function containing the called assertion
        loc_begin_line (int): The line number for the called assertion
        loc_begin_column (int): The column number for the called assertion
        hit (bool): True for runtime assertions, False if from an Assertion Catalog
        must_hit (bool): True if assertion must be hit at runtime
        assert_type (str): Logical handling type for a basic assertion
        display_type (str): Human readable name for a basic assertion
        assert_id (str): Unique id for the basic assertion
        guidance_data (Optional[Mapping[str, Any]]): The guidance values of a rich
            assertion, merged over `details` exactly as the rich assertions merge
            them. Leave unset for a plain assertion.
    """

    if hit and guidance_data is not None:
        details = _merge_guidance(details, guidance_data)

    loc_info = cast(
        Dict[str, Union[str, int]],
        {
            "file": loc_filename,
            "function": loc_function,
            "class": loc_class,
            "begin_line": loc_begin_line,
            "begin_column": loc_begin_column,
        },
    )

    _assert_impl(
        condition,
        message,
        details,
        loc_info,
        hit,
        must_hit,
        assert_type,
        display_type,
        assert_id,
    )


def _merge_guidance(
    details: Optional[Mapping[str, Any]], guidance_data: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Caller details with the guidance values merged over them."""
    if details is None:
        return guidance_data
    merged = dict(details_object(details) or {})
    merged.update(guidance_data)
    return merged


# pylint: disable=too-many-arguments
def _rich_numeric(
    condition: bool,
    left: Any,
    right: Any,
    message: str,
    details: Optional[Mapping[str, Any]],
    display_type: AssertionKind,
    maximize: bool,
) -> None:
    # Two frames up from here is the caller of the public assertion function,
    # as in _hit_assert.
    frame = currentframe()
    caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
    loc_info = _get_location_info(caller)
    guidance_data = {"left": left, "right": right}

    # _assert_impl normalizes loc_info against the tracker entry for this id,
    # so the guidance below reports the same location the assertion does.
    _assert_impl(
        condition,
        message,
        _merge_guidance(details, guidance_data),
        loc_info,
        _WAS_HIT,
        _MUST_BE_HIT,
        display_type.assert_type,
        display_type,
        message,
    )

    if should_emit_numeric(message, maximize, left, right, dispatch_output):
        _emit_guidance(
            guidance_info(NUMERIC, message, message, loc_info, maximize, _WAS_HIT, guidance_data),
            message,
        )


def _rich_boolean(
    condition: bool,
    named_bools: Mapping[str, bool],
    message: str,
    details: Optional[Mapping[str, Any]],
    display_type: AssertionKind,
    maximize: bool,
) -> None:
    frame = currentframe()
    caller = frame.f_back.f_back if frame is not None and frame.f_back is not None else None
    loc_info = _get_location_info(caller)
    guidance_data = dict(named_bools)

    _assert_impl(
        condition,
        message,
        _merge_guidance(details, guidance_data),
        loc_info,
        _WAS_HIT,
        _MUST_BE_HIT,
        display_type.assert_type,
        display_type,
        message,
    )

    _emit_guidance(
        guidance_info(BOOLEAN, message, message, loc_info, maximize, _WAS_HIT, guidance_data),
        message,
    )


def always_greater_than(
    left: Any, right: Any, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `left > right` every time this function is called.

    Equivalent to `always(left > right, ...)`, except that Antithesis is also
    told the values compared, so it can steer toward the ones most likely to
    flip the assertion. `left` and `right` are merged into `details`.

    Args:
        left (Any): The left operand of the comparison
        right (Any): The right operand of the comparison
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_numeric(
        left > right, left, right, message, details,
        AssertionKind.ALWAYS, False,
    )

def always_greater_than_or_equal_to(
    left: Any, right: Any, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `left >= right` every time this function is called.

    Equivalent to `always(left >= right, ...)`, except that Antithesis is also
    told the values compared, so it can steer toward the ones most likely to
    flip the assertion. `left` and `right` are merged into `details`.

    Args:
        left (Any): The left operand of the comparison
        right (Any): The right operand of the comparison
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_numeric(
        left >= right, left, right, message, details,
        AssertionKind.ALWAYS, False,
    )

def always_less_than(
    left: Any, right: Any, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `left < right` every time this function is called.

    Equivalent to `always(left < right, ...)`, except that Antithesis is also
    told the values compared, so it can steer toward the ones most likely to
    flip the assertion. `left` and `right` are merged into `details`.

    Args:
        left (Any): The left operand of the comparison
        right (Any): The right operand of the comparison
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_numeric(
        left < right, left, right, message, details,
        AssertionKind.ALWAYS, True,
    )

def always_less_than_or_equal_to(
    left: Any, right: Any, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `left <= right` every time this function is called.

    Equivalent to `always(left <= right, ...)`, except that Antithesis is also
    told the values compared, so it can steer toward the ones most likely to
    flip the assertion. `left` and `right` are merged into `details`.

    Args:
        left (Any): The left operand of the comparison
        right (Any): The right operand of the comparison
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_numeric(
        left <= right, left, right, message, details,
        AssertionKind.ALWAYS, True,
    )

def sometimes_greater_than(
    left: Any, right: Any, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `left > right` at least one time that this function is called.

    Equivalent to `sometimes(left > right, ...)`, except that Antithesis is also
    told the values compared, so it can steer toward the ones most likely to
    flip the assertion. `left` and `right` are merged into `details`.

    Args:
        left (Any): The left operand of the comparison
        right (Any): The right operand of the comparison
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_numeric(
        left > right, left, right, message, details,
        AssertionKind.SOMETIMES, True,
    )

def sometimes_greater_than_or_equal_to(
    left: Any, right: Any, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `left >= right` at least one time that this function is called.

    Equivalent to `sometimes(left >= right, ...)`, except that Antithesis is also
    told the values compared, so it can steer toward the ones most likely to
    flip the assertion. `left` and `right` are merged into `details`.

    Args:
        left (Any): The left operand of the comparison
        right (Any): The right operand of the comparison
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_numeric(
        left >= right, left, right, message, details,
        AssertionKind.SOMETIMES, True,
    )

def sometimes_less_than(
    left: Any, right: Any, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `left < right` at least one time that this function is called.

    Equivalent to `sometimes(left < right, ...)`, except that Antithesis is also
    told the values compared, so it can steer toward the ones most likely to
    flip the assertion. `left` and `right` are merged into `details`.

    Args:
        left (Any): The left operand of the comparison
        right (Any): The right operand of the comparison
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_numeric(
        left < right, left, right, message, details,
        AssertionKind.SOMETIMES, False,
    )

def sometimes_less_than_or_equal_to(
    left: Any, right: Any, message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that `left <= right` at least one time that this function is called.

    Equivalent to `sometimes(left <= right, ...)`, except that Antithesis is also
    told the values compared, so it can steer toward the ones most likely to
    flip the assertion. `left` and `right` are merged into `details`.

    Args:
        left (Any): The left operand of the comparison
        right (Any): The right operand of the comparison
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_numeric(
        left <= right, left, right, message, details,
        AssertionKind.SOMETIMES, False,
    )

def always_some(
    named_bools: Mapping[str, bool], message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that at least one of `named_bools` is true every time this
    function is called.

    Equivalent to `always(any(named_bools.values()), ...)`, except that
    Antithesis is also told each proposition separately. `named_bools` is
    merged into `details`.

    Args:
        named_bools (Mapping[str, bool]): The propositions, keyed by name
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_boolean(
        any(named_bools.values()), named_bools, message, details,
        AssertionKind.ALWAYS, False,
    )


def sometimes_all(
    named_bools: Mapping[str, bool], message: str, details: Optional[Mapping[str, Any]] = None
) -> None:
    """Asserts that every one of `named_bools` is true at least one time that
    this function is called.

    Equivalent to `sometimes(all(named_bools.values()), ...)`, except that
    Antithesis is also told each proposition separately. `named_bools` is
    merged into `details`.

    Args:
        named_bools (Mapping[str, bool]): The propositions, keyed by name
        message (str): The unique message associated with the assertion. Must be provided as a string literal.
        details (Optional[Mapping[str, Any]]): Named details associated with the assertion
    """
    _rich_boolean(
        all(named_bools.values()), named_bools, message, details,
        AssertionKind.SOMETIMES, True,
    )

def _guidance_loc_info(
    loc_filename: str,
    loc_function: str,
    loc_class: str,
    loc_begin_line: int,
    loc_begin_column: int,
) -> Dict[str, Union[str, int]]:
    return cast(
        Dict[str, Union[str, int]],
        {
            "file": loc_filename,
            "function": loc_function,
            "class": loc_class,
            "begin_line": loc_begin_line,
            "begin_column": loc_begin_column,
        },
    )


def _emit_guidance(record: Dict[str, Any], guidance_id: str) -> None:
    dispatch_guidance({"antithesis_guidance": record}, guidance_id, dispatch_output)


# pylint: disable=too-many-arguments
def _numeric_guidance_raw(
    left: Any,
    right: Any,
    message: str,
    maximize: bool,
    loc_filename: str,
    loc_function: str,
    loc_class: str,
    loc_begin_line: int,
    loc_begin_column: int,
    hit: bool,
    guidance_id: str,
):
    guidance_data = None
    if hit:
        if not should_emit_numeric(guidance_id, maximize, left, right, dispatch_output):
            return
        guidance_data = {"left": left, "right": right}

    _emit_guidance(
        guidance_info(
            NUMERIC,
            guidance_id,
            message,
            _guidance_loc_info(
                loc_filename, loc_function, loc_class, loc_begin_line, loc_begin_column
            ),
            maximize,
            hit,
            guidance_data,
        ),
        guidance_id,
    )


# pylint: disable=too-many-arguments
def _boolean_guidance_raw(
    named_bools: Optional[Mapping[str, Any]],
    message: str,
    maximize: bool,
    loc_filename: str,
    loc_function: str,
    loc_class: str,
    loc_begin_line: int,
    loc_begin_column: int,
    hit: bool,
    guidance_id: str,
):
    _emit_guidance(
        guidance_info(
            BOOLEAN,
            guidance_id,
            message,
            _guidance_loc_info(
                loc_filename, loc_function, loc_class, loc_begin_line, loc_begin_column
            ),
            maximize,
            hit,
            named_bools if hit else None,
        ),
        guidance_id,
    )


# ----------------------------------------------------------------------
# Evaluate once - on load
# -------------------------------------------------------
_CATALOG = os.getenv(ASSERTION_CATALOG_ENV_VAR)
if _CATALOG is not None:
    # Imported here, not at the top: antithesis.catalog imports assert_raw
    # from this module, so it must load after the definitions above.
    from antithesis import catalog as _catalog_module
    from antithesis._internal import catalog_resolve as _catalog_resolve

    if os.path.isdir(_CATALOG):
        instrumentation_folder = _catalog_resolve.select_instrumentation_folder(_CATALOG)
        if instrumentation_folder is not None:
            instrumentation_path = os.path.join(_CATALOG, instrumentation_folder)
            json_catalog_path = os.path.join(
                instrumentation_path, f"{ASSERTION_CATALOG_NAME}.json"
            )
            # A coverage-only build (assertion cataloging disabled) has a sym table
            # but no catalog
            if os.path.isfile(json_catalog_path):
                _catalog_module.register(_catalog_module.load(json_catalog_path))

            # Coverage/instrumentation activation (no-op if already active). If activated
            # here, coverage will only be partial and will not be aware of code that has
            # already run. For best results, use the `python -m antithesis` runner
            try:
                from antithesis._internal import coverage

                coverage.activate_module(instrumentation_folder)
            except Exception:
                pass
    elif os.path.isfile(_CATALOG):
        # A plain catalog file, e.g. written by `python -m antithesis.catalog`
        _catalog_module.register(_catalog_module.load(_CATALOG))
    else:
        PROBLEM_TEXT = "must refer to an accessible directory or file"
        print(f"Environment variable {ASSERTION_CATALOG_ENV_VAR!r} {PROBLEM_TEXT}")
        print(f"Ignoring it because it is set to {_CATALOG!r}")
