"""Locating the platform-produced assertion catalog for this process.

On the Antithesis platform, instrumentation writes one subdirectory per
instrumented app/service under a common parent directory (named by the
``ANTITHESIS_ASSERTION_CATALOG`` environment variable), each holding that
app's ``assertion_catalog.json``. These helpers decide which subdirectory
belongs to the running process.
"""

import json
import os
import sys
from importlib.util import find_spec
from inspect import currentframe
from typing import Optional

from .sdk_constants import (
    ASSERTION_CATALOG_NAME,
    COVERAGE_MODULE_LIST,
)


def _get_subdirs(dir_path: str) -> list:
    if not os.path.isdir(dir_path):
        return []
    walk_results = next(os.walk(dir_path))
    return walk_results[1]  # directories at index=1, files at index=2


def _get_module_list(file_path: str) -> list:
    """Reads and parses the JSON representation of a module
    list.  This list will be used to identify what python
    modules were processed at instrumentation time.
    In cases where there are more than one python app/service
    that can be run in a container, these apps/services will
    each have separate assertion catalogs. Knowing what python
    modules should be importable at runtime, will determine
    which specific assertion catalog should be associated with
    an app/service - and that catalog will be registered with
    the fuzzer.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            mod_list = json.loads(f.read())
        module_list = mod_list["module_list"]
        return module_list if isinstance(module_list, list) else []
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("[STATUS]", json.dumps({'antithesis_warning': {'message': f"Antithesis: ignoring unreadable module list {file_path!r}: {e}"}}), file=sys.stderr)
        return []


def _get_grade(module_list: list) -> float:
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
    subdirectory will contain `assertion_catalog.json`.
    (Instrumentors before late 2026 also wrote a legacy
    `assertion_catalog.py` rendition there; nothing reads it.)
    """
    subdirs = _get_subdirs(from_path)
    lx = len(subdirs)
    if lx < 2:
        return subdirs[0] if lx == 1 else None

    selected_grade = 0.0
    selected_subdir = None
    for subdir in subdirs:
        py_module_list_path = os.path.join(
            from_path, subdir, f"{COVERAGE_MODULE_LIST}.json"
        )
        module_list = _get_module_list(py_module_list_path)
        if len(module_list) > 0:
            print(f"Nonempty module list found in {py_module_list_path!r}")
            print(f"{module_list = }")
            grade = _get_grade(module_list)
            if grade > selected_grade:
                selected_grade = grade
                selected_subdir = subdir
    return selected_subdir


def _recorded_instrumentation_module() -> Optional[str]:
    try:
        from antithesis._internal.coverage import get_instrumentation_module

        return get_instrumentation_module()
    except Exception:
        return None


def _marker_module_from_caller() -> Optional[str]:
    """The module named by the `# antithesis-module:` marker of the nearest frame
    outside the antithesis package -- i.e. the code that imported the SDK. Read
    statically from that module's file, so it works even though that module is still
    mid-import (its own module-level marker global would not be set yet)."""
    try:
        from antithesis._internal.coverage import resolve_module_from_marker
    except Exception:
        return None
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../antithesis
    frame = currentframe()  # own frame is inside pkg_dir, so the loop skips it
    while frame is not None:
        filename = frame.f_code.co_filename
        try:
            outside = bool(filename) and not os.path.abspath(filename).startswith(pkg_dir)
        except OSError:
            outside = False
        if outside:
            module = resolve_module_from_marker(filename)
            if module is not None:
                return module
        frame = frame.f_back
    return None


def select_instrumentation_folder(from_path: str) -> Optional[str]:
    """Locate this program's instrumentation subdir (which holds its
    `assertion_catalog.json`)."""
    module = _recorded_instrumentation_module()
    if module is not None:
        catalog = os.path.join(from_path, module, f"{ASSERTION_CATALOG_NAME}.json")
        if os.path.isfile(catalog):
            return module
        return None  # identity known but its catalog isn't here -> nothing to load

    # No recorded identity: prefer the importing module's marker if its catalog is
    # present, else fall back to the single-subdir default.
    marker = _marker_module_from_caller()
    if marker is not None and os.path.isfile(
        os.path.join(from_path, marker, f"{ASSERTION_CATALOG_NAME}.json")
    ):
        return marker

    # No recorded identity and no usable marker: fall back to the importability
    # "vote" (`_get_instrumentation_folder`) so a marker-less image resolves the
    # same way older builds always have.
    return _get_instrumentation_folder(from_path)
