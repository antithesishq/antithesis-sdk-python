"""Basic Assertions

This module provides functions for basic assertions:
    * always
    * always_or_unreachable
    * sometimes
    * reachable
    * unreachable

This module enables defining [test properties] about your program or [workload].
It is part of the [Antithesis Python SDK], which enables Python applications to integrate
with the [Antithesis platform].

These functions are no-ops with minimal performance overhead when called outside of
the Antithesis environment. However, if the environment variable ANTITHESIS_SDK_LOCAL_OUTPUT
is set, these functions will log to the file pointed to by that variable using a
structured JSON format defined [here]. This allows you to make use of the Antithesis
assertions package in your regular testing, or even in production. In particular,
very few assertions frameworks offer a convenient way to define [Sometimes assertions],
but they can be quite useful even outside Antithesis.

Each function in this package takes a parameter called message, which is a human
readable identifier used to aggregate assertions. Antithesis generates one test
property per unique message and this test property will be named "<message>" in
the [triage report].

This test property either passes or fails, which depends upon the evaluation of every
assertion that shares its message. Different assertions in different parts of the code
should have different message, but the same assertion should always have the same
message even if it is moved to a different file.

Each function also takes a parameter called details, which is a key-value map of
optional additional information provided by the user to add context for assertion
failures. The information that is logged will appear in the [triage report], under
the details section of the corresponding property. Normally the values passed to
details are evaluated at runtime.

"""

from ast import literal_eval
from typing import Any, Mapping, Union, Dict, Optional, cast
from importlib.util import find_spec
import inspect

import json
import os
from pathlib import Path
import re
import sys

from antithesis_sdk._internal import (
    dispatch_output,
    ASSERTION_CATALOG_ENV_VAR,
    ASSERTION_CATALOG_NAME,
)
from ._assertinfo import AssertInfo, AssertionDisplay
from ._location import _get_location_info
from ._tracking import assert_tracker, get_tracker_entry

_WAS_HIT = True  # Assertion was reached at runtime
_MUST_BE_HIT = True  # Assertion must be reached at least once
_OPTIONALLY_HIT = False  # Assertion may or may not be reachable
_ASSERTING_TRUE = True  # Assertion condition should be True
_ASSERTING_FALSE = True  # Assertion condition should be False
_MAX_EXCERPT_WIDTH = 40  # Maximum length of an excerpt used fo error reporting


def _emit_assert(assert_info: AssertInfo) -> None:
    """Formats and forwards the assertion provided to the
    presently configured handler.

    Args:
        assert_info (AssertInfo): The internal representation for a Basic Assertion
    """

    wrapped_assert = {"antithesis_assert": assert_info.to_dict()}
    dispatch_output(json.dumps(wrapped_assert, indent=2))


# pylint: disable=too-many-arguments
def assert_impl(
    cond: bool,
    message: str,
    details: Mapping[str, Any],
    loc_info: Dict[str, Union[str, int]],
    hit: bool,
    must_hit: bool,
    assert_type: str,
    display_type: str,
    assert_id: str,
):
    """Composes, tracks and emits assertions that should be forwarded
    to the configured handler.

    Args:
        cond (bool): Runtime condition for the basic assertion
        message (str): Unique message associated with a basic assertion
        details (Mapping[str, Any]): Named details associated with a basic
            assertion at runtime
        loc_info (Dict[str, Union[str, int]]): Caller information for the basic
            assertion (runtime and catalog)
        hit (bool): True for runtime assertions, False if from an Assertion Catalog
        must_hit (bool): True if assertion must be hit at runtime
        assert_type (AssertType): Logical handling type for a basic assertion
        display_type (AssertionDisplay): Human readable name for a basic assertion
        assert_id (str): Unique id for the basic assertion
    """
    filename = cast(str, loc_info.get("filename", ""))
    classname = cast(str, loc_info.get("class", ""))
    tracker_entry = get_tracker_entry(assert_tracker, assert_id, filename, classname)

    # Always grab the filename and classname captured when the tracker_entry was established
    # This provides the consistency needed between instrumentation-time and runtime
    if filename != tracker_entry.filename:
        loc_info["filename"] = tracker_entry.filename

    if classname != tracker_entry.classname:
        loc_info["class"] = tracker_entry.classname

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

    if not hit:
        _emit_assert(assert_info)
        return

    if cond:
        tracker_entry.inc_passes()
        if tracker_entry.passes == 1:
            _emit_assert(assert_info)
    else:
        tracker_entry.inc_fails()
        if tracker_entry.fails == 1:
            _emit_assert(assert_info)


def _make_key(message: str, _loc_info: Dict[str, Union[str, int]]) -> str:
    """Composes a tracker lookup key.

    Args:
        message (str): The text for a basic assertion
        _loc_info (Dict[str, Union[str, int]]): The location infor for a basic assertion

    Returns:
        str: The tracker lookup key
    """
    return message


def always(condition: bool, message: str, details: Mapping[str, Any]) -> None:
    """Asserts that condition is true every time this function
    is called. This test property will be viewable in the
    “Antithesis SDK: Always” group of your triage report.

    Args:
        condition (bool): Indicates if the assertion is true
        message (str): The unique message associated with the assertion
        details (Mapping[str, Any]): Named details associated with the assertion
    """
    all_frames = inspect.stack()
    this_frame = all_frames[1]
    location_info = _get_location_info(this_frame)
    assert_id = _make_key(message, location_info)
    display_type = AssertionDisplay.ALWAYS
    assert_type = display_type.assert_type()
    assert_impl(
        condition,
        message,
        details,
        location_info,
        _WAS_HIT,
        _MUST_BE_HIT,
        assert_type,
        display_type,
        assert_id,
    )


def always_or_unreachable(
    condition: bool, message: str, details: Mapping[str, Any]
) -> None:
    """Asserts that condition is true every time this function
    is called. The corresponding test property will pass if the
    assertion is never encountered. This test property will be
    viewable in the “Antithesis SDK: Always” group of your triage
    report.

    Args:
        condition (bool): Indicates if the assertion is true
        message (str): The unique message associated with the assertion
        details (Mapping[str, Any]): Named details associated with the assertion
    """
    all_frames = inspect.stack()
    this_frame = all_frames[1]
    location_info = _get_location_info(this_frame)
    assert_id = _make_key(message, location_info)
    display_type = AssertionDisplay.ALWAYS_OR_UNREACHABLE
    assert_type = display_type.assert_type()
    assert_impl(
        condition,
        message,
        details,
        location_info,
        _WAS_HIT,
        _OPTIONALLY_HIT,
        assert_type,
        display_type,
        assert_id,
    )


def sometimes(condition: bool, message: str, details: Mapping[str, Any]) -> None:
    """Asserts that condition is true at least one time that this function
    was called. (If the assertion is never encountered, the test property
    will therefore fail.) This test property will be viewable in the
    “Antithesis SDK: Sometimes” group.

    Args:
        condition (bool): Indicates if the assertion is true
        message (str): The unique message associated with the assertion
        details (Mapping[str, Any]): Named details associated with the assertion
    """
    all_frames = inspect.stack()
    this_frame = all_frames[1]
    location_info = _get_location_info(this_frame)
    assert_id = _make_key(message, location_info)
    display_type = AssertionDisplay.SOMETIMES
    assert_type = display_type.assert_type()
    assert_impl(
        condition,
        message,
        details,
        location_info,
        _WAS_HIT,
        _MUST_BE_HIT,
        assert_type,
        display_type,
        assert_id,
    )


def reachable(message: str, details: Mapping[str, Any]) -> None:
    """Reachable asserts that a line of code is reached at least
    once. The corresponding test property will pass if this function
    is ever called. (If it is never called the test property will
    therefore fail.) This test property will be viewable in the
    “Antithesis SDK: Reachablity assertions” group.

    Args:
        condition (bool): Indicates if the assertion is true
        message (str): The unique message associated with the assertion
        details (Mapping[str, Any]): Named details associated with the assertion
    """
    all_frames = inspect.stack()
    this_frame = all_frames[1]
    location_info = _get_location_info(this_frame)
    assert_id = _make_key(message, location_info)
    display_type = AssertionDisplay.ALWAYS
    assert_type = display_type.assert_type()
    assert_impl(
        _ASSERTING_TRUE,
        message,
        details,
        location_info,
        _WAS_HIT,
        _MUST_BE_HIT,
        assert_type,
        display_type,
        assert_id,
    )


def unreachable(message: str, details: Mapping[str, Any]) -> None:
    """Unreachable asserts that a line of code is never reached.
    The corresponding test property will fail if this function
    is ever called. (If it is never called the test property will
    therefore pass.) This test property will be viewable in the
    “Antithesis SDK: Reachablity assertions” group.

    Args:
        condition (bool): Indicates if the assertion is true
        message (str): The unique message associated with the assertion
        details (Mapping[str, Any]): Named details associated with the assertion
    """
    all_frames = inspect.stack()
    this_frame = all_frames[1]
    location_info = _get_location_info(this_frame)
    assert_id = _make_key(message, location_info)
    display_type = AssertionDisplay.ALWAYS
    assert_type = display_type.assert_type()
    assert_impl(
        _ASSERTING_FALSE,
        message,
        details,
        location_info,
        _WAS_HIT,
        _OPTIONALLY_HIT,
        assert_type,
        display_type,
        assert_id,
    )


# pylint: disable=too-many-arguments
def assert_raw(
    condition: bool,
    message: str,
    details: Mapping[str, Any],
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
):
    """For adapter use.  Composes, tracks and emits assertions that should be forwarded
    to the configured handler.

    Args:
        condition (bool): Runtime condition for the basic assertion
        message (str): Unique message associated with a basic assertion
        details (Mapping[str, Any]): Named details associated with a basic assertion at runtime
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
    """

    loc_info = cast(
        Dict[str, Union[str, int]],
        {
            "filename": loc_filename,
            "function": loc_function,
            "class": loc_class,
            "begin_line": loc_begin_line,
            "begin_column": loc_begin_column,
        },
    )

    assert_impl(
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


def _readlines(fname: str, verbose=False) -> list[str]:
    all_lines = []
    with open(fname, "r", encoding="utf-8") as f:
        for line in f:
            if verbose:
                print(line, end="")
            all_lines.append(line)
    return all_lines


def _get_subdirs(dir_path: str) -> list[str]:
    if not os.path.isdir(dir_path):
        return []
    walk_results = next(os.walk(dir_path))
    return walk_results[1]  # directories at index=1, files at index=2


def _get_module_list(file_path: str) -> list[str]:
    """Reads all lines in file_path, looking for any comment
    lines that contain:
    `module_name = '<module_name>'`
    Parse these lines and return a list of the module names
    found.  This list will be used to identify what python
    modules contained assertions at instrumentation time.
    In cases where there are more than one python app/service
    that can be run in a container, these apps/services will
    each have separate assertion catalogs. Knowing what python
    modules should be importable at runtime, will determine
    which specific assertion catalog should be associated with
    an app/service - and that catalog will be registered with
    the fuzzer.
    """

    listed_modules = []
    rx = re.compile(r"^\s*#\s*module_name\s*=\s*(\S*)\s*")
    lines = _readlines(file_path)
    for line in lines:
        maybe_match = rx.match(line)
        if maybe_match is not None:
            matched_repr = maybe_match.group(1)
            module_name = literal_eval(matched_repr)
            listed_modules.append(module_name)
    return listed_modules


def _get_grade(module_list: list[str]) -> float:
    """Count the number of modules that can be loaded
    from this list, and return the overall grade of loadable
    modules found in the range 0.0 to 1.0
    """
    num_modules = float(len(module_list))
    num_found = 0
    for module_name in module_list:
        this_spec = find_spec(module_name)
        if this_spec is not None:
            num_found = num_found + 1
    return num_found / num_modules


def _get_instrumentation_folder(from_path: str) -> Optional[str]:
    """Determines which subfolder of `from_path` contains the
    assertion catalog that corresponds to the app/service
    in this python instance that is using the Antithesis SDK.
    In cases where there are more than one python app/service
    that can be run in a container, these apps/services will
    each have separate assertion catalogs.  All such apps
    and services that are instrumented will write instrumentation
    generated files to a subdirectory named `python-xxxxxxxxxxxx`
    where `xxxxxxxxxxxx` represents the generated module name
    used in the `xxxxxxxxxxxx.sym.tsv` file.  Each of these
    subdirectories will have a common parent directory, which
    is provided at instrumentation time, using the `-p` command
    line argument.  In addition to the symbols file, each
    subdirectory will contain `assertion_catalog.py` and
    `assertion_catalog.json`.  The `assertion_catalog.py` file
    provides a more readable version of the catalog data, than
    is found in the `assertion_catalog.json` file.  It is
    safer to process the assertion catalog by read/parse json
    than it is to import/exec the `assertion_catalog.py` file.
    """
    subdirs = _get_subdirs(from_path)
    lx = len(subdirs)
    if lx < 2:
        return subdirs[0] if lx == 1 else None

    selected_grade = 0.0
    selected_subdir = None
    for subdir in subdirs:
        py_catalog_path = os.path.join(
            from_path, subdir, f"{ASSERTION_CATALOG_NAME}.py"
        )
        module_list = _get_module_list(py_catalog_path)
        if len(module_list) > 0:
            print(f"Nonempty catalog found in {py_catalog_path!r}")
            print(f"{module_list = }")
            grade = _get_grade(module_list)
            if grade > selected_grade:
                selected_grade = grade
                selected_subdir = subdir
    return selected_subdir


def _process_json_catalog(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        idx = 0
        lines = f.readlines()
        for line in lines:
            idx = idx + 1
            try:
                the_dict = json.loads(line)
                assert_impl(
                    the_dict["condition"],
                    the_dict["message"],
                    the_dict["details"],
                    the_dict["location_info"],
                    the_dict["hit"],
                    the_dict["must_hit"],
                    the_dict["assert_type"],
                    the_dict["display_type"],
                    the_dict["id"],
                )
            except json.JSONDecodeError:
                print("Unable to parse as JSON:")
                lx = len(line)
                excerpt = (
                    line
                    if lx < _MAX_EXCERPT_WIDTH
                    else line[0:_MAX_EXCERPT_WIDTH] + "..."
                )
                print(f"[{idx}] {excerpt!r}")


# ----------------------------------------------------------------------
# Evaluate once - on load
# -------------------------------------------------------
_CATALOG = os.getenv(ASSERTION_CATALOG_ENV_VAR)
if _CATALOG is not None:
    cat_path = Path(_CATALOG)
    if cat_path.is_dir():

        instrumentation_folder = _get_instrumentation_folder(_CATALOG)
        if instrumentation_folder is not None:
            instrumentation_path = os.path.join(_CATALOG, instrumentation_folder)
            json_catalog_path = os.path.join(
                instrumentation_path, f"{ASSERTION_CATALOG_NAME}.json"
            )
            _process_json_catalog(json_catalog_path)
    else:
        PROBLEM_TEXT = "must refer to an accessible directory"
        print(f"Environment variable {ASSERTION_CATALOG_ENV_VAR!r} {PROBLEM_TEXT}")
        print(f"Ignoring it because it is set to {cat_path!r}")


# ----------------------------------------------------------------------
# For project.scripts support
# ----------------------------------------------------------------------
def _cmd_always():
    """Smoke-test for always_or_unreachable.

    Examples:
        Should be executed from a devshell

        >>> $ always "this always works" t t f t f
        HIT: AlwaysOrUnreachable 'this always works' => True
        HIT: AlwaysOrUnreachable 'this always works' => False
    """
    num_args = len(sys.argv)
    if num_args >= 3:
        message = (sys.argv[1]).strip()
        for i in range(2, num_args):
            arg = sys.argv[i].lower()
            condition = bool(arg == "t")
            always_or_unreachable(condition, message, {})


def _cmd_sometimes():
    """Smoke-test for sometimes.

    Examples:
        Should be executed from a devshell

        >>> $ sometimes "this works at least once" t t f t f
        HIT: Sometimes 'this works at least once' => True
        HIT: Sometimes 'this works at least once' => False
    """
    num_args = len(sys.argv)
    if num_args >= 3:
        message = (sys.argv[1]).strip()
        for i in range(2, num_args):
            arg = sys.argv[i].lower()
            condition = bool(arg == "t")
            sometimes(condition, message, {})


def _add():
    """Smoke-test for adding two integers.

    Examples:
        Should be executed from a devshell

        >>> $ addx 55 11
        Adding: 55 + 11 => 66
    """
    num1 = 0
    num2 = 0
    if len(sys.argv) > 1:
        maybe_num1 = sys.argv[1]
        if maybe_num1.isdigit():
            num1 = int(maybe_num1)

    if len(sys.argv) > 2:
        maybe_num2 = sys.argv[2]
        if maybe_num2.isdigit():
            num2 = int(maybe_num2)

    the_sum = num1 + num2
    print(f"Adding: {num1} + {num2} => {the_sum}")
