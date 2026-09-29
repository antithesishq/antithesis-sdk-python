"""This module gives read and write access to the
[assertion catalog](https://antithesis.com/docs/reference/sdk/assertion_cataloging/):
the set of assertion declarations in your code, whether or not they ever run.

It exists for local tooling rather than for Antithesis tests: enumerating 
the test properties a source tree declares, comparing them against the ones
a local test run actually evaluated, failing CI when a change silently drops an
assertion, or checking an inventory of test properties into the repository.
Workloads use `antithesis.assertions` and `antithesis.random` instead and
never need this module.

On the Antithesis platform the catalog is produced at build time by the
platform's instrumentor; this module is just that machinery, in case you
need it:

* `scan_tree` / `scan_source` / `scan_ast` find assertion declarations in
  source, with the same scanner the platform runs. Nothing is imported or
  executed.
* `write` serializes entries as registration events. `load` reads such a 
  file back; it is what the ``ANTITHESIS_ASSERTION_CATALOG`` environment 
  variable resolution uses. ``load(write(entries))`` round-trips.
* `register` declares entries to the active output handler at runtime, the
  way an instrumented process declares its catalog at startup.
* `assertions()` lists the catalog registered for this process, resolved
  through `ANTITHESIS_ASSERTION_CATALOG`. Outside an instrumented container
  that variable is normally unset and the result is empty -- use `scan_tree`
  on your source instead.

The scanner only catalogs what the platform would: calls to the assertion
functions of `antithesis.assertions` (under any import alias) with a literal
message. Assertions issued through your own wrappers, or with dynamically
built messages, are invisible to any static scan; declare those at runtime
with `register` (or `antithesis.assertions.assert_raw`), which works both
locally and on the platform.

A typical local workflow, with `ANTITHESIS_SDK_LOCAL_OUTPUT` set so
assertions are logged to a file:

```
python -m antithesis.catalog src/ -o catalog.json
ANTITHESIS_ASSERTION_CATALOG=catalog.json pytest
```

The output file then opens with one ``"hit": false`` line per declared
assertion, followed by the assertions the run actually evaluated
(``"hit": true``) -- so the test properties your suite never exercised are
the messages with no ``"hit": true`` line. Equivalently, a harness can skip
the files entirely: call `scan_tree` at session start, `register` the
result, and join in memory.
"""

import json
import os
from dataclasses import replace
from typing import IO, Iterable, List, Optional, Union

from antithesis._assertinfo import AssertInfo, AssertionKind
from antithesis._guidance import NUMERIC, guidance_info
from antithesis._internal.sdk_constants import (
    ASSERTION_CATALOG_ENV_VAR,
    ASSERTION_CATALOG_NAME,
)
from ._types import Assertion, GuidanceDeclaration, SourceLocation
from ._scanner import scan_ast, scan_source, scan_tree
# Platform-only plumbing: which instrumentation subdir belongs to this
# process. Lives in _internal (like the coverage machinery) because the
# local workflow never needs it -- only in-container directory layouts do.
from antithesis._internal import catalog_resolve as _resolve

__all__ = [
    "Assertion",
    "AssertionKind",
    "GuidanceDeclaration",
    "SourceLocation",
    "assertions",
    "load",
    "register",
    "scan_ast",
    "scan_source",
    "scan_tree",
    "write",
]

_MAX_EXCERPT_WIDTH = 40  # Maximum length of an excerpt used for error reporting


def _event_dict(assertion: Assertion) -> dict:
    info = AssertInfo(
        hit=False,
        must_hit=assertion.kind.must_hit,
        assert_type=assertion.kind.assert_type.value,
        display_type=assertion.kind.value,
        message=assertion.message,
        condition=False,
        assert_id=assertion.id,
        loc_info={
            "file": assertion.location.file,
            "function": assertion.location.function,
            "class": assertion.location.class_name,
            "begin_line": assertion.location.begin_line,
            "begin_column": assertion.location.begin_column,
        },
        details=None,
    )
    return {"antithesis_assert": info.to_dict()}


def _event_dicts(assertion: Assertion) -> List[dict]:
    """The wire records one catalog entry declares: the assertion, and for a
    rich assertion the guidance point it also declares."""
    dicts = [_event_dict(assertion)]
    if assertion.guidance is not None:
        dicts.append(
            {
                "antithesis_guidance": guidance_info(
                    assertion.guidance.guidance_type,
                    assertion.id,
                    assertion.message,
                    {
                        "file": assertion.location.file,
                        "function": assertion.location.function,
                        "class": assertion.location.class_name,
                        "begin_line": assertion.location.begin_line,
                        "begin_column": assertion.location.begin_column,
                    },
                    assertion.guidance.maximize,
                    False,
                    None,
                )
            }
        )
    return dicts


def write(entries: Iterable[Assertion], out: Union[str, "os.PathLike", IO[str]]) -> None:
    """Writes catalog entries to `out` (a path or a text file object) as JSON
    lines. `load` reads it back.
    """
    if hasattr(out, "write"):
        for assertion in entries:
            for the_dict in _event_dicts(assertion):
                out.write(json.dumps(the_dict))
                out.write("\n")
    else:
        with open(out, "w", encoding="utf-8") as fp:
            write(entries, fp)


def _kind_of(the_dict: dict) -> Optional[AssertionKind]:
    display_type = the_dict.get("display_type", "")
    for kind in AssertionKind:
        if kind.value == display_type:
            return kind
    # No usable display_type: derive the kind the way the platform does,
    # from the wire-level type plus must_hit.
    assert_type = the_dict.get("assert_type", "")
    must_hit = bool(the_dict.get("must_hit", True))
    if assert_type == "always":
        return AssertionKind.ALWAYS if must_hit else AssertionKind.ALWAYS_OR_UNREACHABLE
    if assert_type == "sometimes":
        return AssertionKind.SOMETIMES
    if assert_type == "reachability":
        return AssertionKind.REACHABLE if must_hit else AssertionKind.UNREACHABLE
    return None


def _assertion_of(the_dict: dict) -> Optional[Assertion]:
    message = the_dict.get("message")
    kind = _kind_of(the_dict)
    if not isinstance(message, str) or kind is None:
        return None
    # Registration events say "location"; the legacy instrumentor catalog
    # file format said "location_info".
    loc = the_dict.get("location")
    if not isinstance(loc, dict):
        loc = the_dict.get("location_info")
    if not isinstance(loc, dict):
        loc = {}
    location = SourceLocation(
        file=str(loc.get("file", "")),
        begin_line=int(loc.get("begin_line", -1)),
        begin_column=int(loc.get("begin_column", -1)),
        class_name=str(loc.get("class", "")),
        function=str(loc.get("function", "")),
    )
    the_id = the_dict.get("id")
    if not isinstance(the_id, str):
        the_id = message
    return Assertion(id=the_id, message=message, kind=kind, location=location)


def _load_file(file_path: str) -> List[Assertion]:
    entries: List[Assertion] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f.readlines(), start=1):
            try:
                the_dict = json.loads(line)
            except json.JSONDecodeError:
                print("Unable to parse as JSON:")
                lx = len(line)
                excerpt = (
                    line
                    if lx < _MAX_EXCERPT_WIDTH
                    else line[0:_MAX_EXCERPT_WIDTH] + "..."
                )
                print(f"[{idx}] {excerpt!r}")
                continue
            if not isinstance(the_dict, dict):
                print(f"Not an assertion catalog entry, skipping: [{idx}]")
                continue
            guidance = the_dict.get("antithesis_guidance")
            if isinstance(guidance, dict):
                # A rich assertion declares both halves, so the guidance line
                # belongs to the assertion line that preceded it rather than
                # being an entry of its own.
                if not guidance.get("hit"):
                    _attach_guidance(entries, guidance, idx)
                continue
            inner = the_dict.get("antithesis_assert")
            if isinstance(inner, dict):
                if inner.get("hit"):
                    # A runtime evaluation, not a declaration. Someone handed
                    # us an event log; take the registrations and move on.
                    continue
                the_dict = inner
            assertion = _assertion_of(the_dict)
            if assertion is None:
                print(f"Not an assertion catalog entry, skipping: [{idx}]")
                continue
            entries.append(assertion)
    return entries


def _attach_guidance(entries: List[Assertion], guidance: dict, idx: int) -> None:
    """Folds a guidance declaration onto the assertion sharing its id."""
    the_id = guidance.get("id")
    guidance_type = guidance.get("guidance_type")
    maximize = guidance.get("maximize")
    if not isinstance(guidance_type, str) or not isinstance(maximize, bool):
        print(f"Not a guidance catalog entry, skipping: [{idx}]")
        return
    declaration = GuidanceDeclaration(guidance_type, maximize)
    for position in range(len(entries) - 1, -1, -1):
        if entries[position].id == the_id:
            entries[position] = replace(entries[position], guidance=declaration)
            return
    print(f"Guidance declaration for an unknown assertion, skipping: [{idx}]")


def load(path: Union[str, "os.PathLike"]) -> List[Assertion]:
    """Reads catalog entries back from a catalog file, or from a directory
    the platform's instrumentor populated (such as the one
    ``ANTITHESIS_ASSERTION_CATALOG`` points to inside a container).

    Lines that do not parse as catalog entries are reported and skipped.
    Raises `FileNotFoundError` if `path` does not exist or is a directory
    in which no catalog can be located.
    """
    path = os.fspath(path)
    if os.path.isfile(path):
        return _load_file(path)
    if os.path.isdir(path):
        # A directory either holds the catalog file itself or is a platform
        # parent directory with one instrumentation subdirectory per app.
        direct = os.path.join(path, f"{ASSERTION_CATALOG_NAME}.json")
        if os.path.isfile(direct):
            return _load_file(direct)
        folder = _resolve.select_instrumentation_folder(path)
        if folder is not None:
            nested = os.path.join(path, folder, f"{ASSERTION_CATALOG_NAME}.json")
            if os.path.isfile(nested):
                return _load_file(nested)
        raise FileNotFoundError(f"no {ASSERTION_CATALOG_NAME}.json found under {path!r}")
    raise FileNotFoundError(f"no such catalog file or directory: {path!r}")


def assertions() -> List[Assertion]:
    """The assertion catalog registered for this process, resolved through
    the ``ANTITHESIS_ASSERTION_CATALOG`` environment variable.

    Inside an instrumented container this is the catalog the platform
    produced for this program. Outside one the variable is normally unset
    and the result is empty: the local catalog is whatever you scanned or
    loaded yourself. Reading it registers nothing and emits nothing.
    """
    path = os.getenv(ASSERTION_CATALOG_ENV_VAR)
    if path is None:
        return []
    try:
        return load(path)
    except FileNotFoundError:
        return []


def register(entries: Iterable[Assertion]) -> None:
    """Declares catalog entries at runtime, emitting each one (with
    ``"hit": false``) through the active output handler.

    This is how an instrumented process declares its catalog at startup, and
    it works the same on the platform and locally -- so it is the right tool
    for declaring assertions no static scan can see (wrapped call sites,
    messages drawn from a data table), as well as for harnesses that scan at
    session start instead of shipping a catalog file.

    Entries are emitted unconditionally: registering the same entry twice
    writes two declaration lines. Consumers should treat declarations as a
    set keyed by message.
    """
    # Deferred: antithesis.assertions imports this module while it loads.
    from antithesis.assertions import (
        _boolean_guidance_raw,
        _numeric_guidance_raw,
        assert_raw,
    )

    for assertion in entries:
        assert_raw(
            False,
            assertion.message,
            None,
            assertion.location.file,
            assertion.location.function,
            assertion.location.class_name,
            assertion.location.begin_line,
            assertion.location.begin_column,
            False,
            assertion.kind.must_hit,
            assertion.kind.assert_type.value,
            assertion.kind.value,
            assertion.id,
        )
        if assertion.guidance is None:
            continue
        # A declaration carries no operands; the raw helpers ignore them when
        # `hit` is false, so the zeros and the empty map never reach the wire.
        if assertion.guidance.guidance_type == NUMERIC:
            _numeric_guidance_raw(
                0,
                0,
                assertion.message,
                assertion.guidance.maximize,
                assertion.location.file,
                assertion.location.function,
                assertion.location.class_name,
                assertion.location.begin_line,
                assertion.location.begin_column,
                False,
                assertion.id,
            )
        else:
            _boolean_guidance_raw(
                {},
                assertion.message,
                assertion.guidance.maximize,
                assertion.location.file,
                assertion.location.function,
                assertion.location.class_name,
                assertion.location.begin_line,
                assertion.location.begin_column,
                False,
                assertion.id,
            )
