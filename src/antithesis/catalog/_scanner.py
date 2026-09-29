"""The assertion scanner: finds assertion call sites in Python source by
walking its AST, without importing or executing it.

This is the same scanner the Antithesis platform's instrumentor runs at
build time, so what it catalogs locally is what the platform catalogs.
Consequently it only sees what a static scan can see: the assertion
functions of `antithesis.assertions` (under any import alias), called with
a literal message. A call it cannot catalog -- a dynamic message, or a
wrapper function of your own -- is reported and skipped, and would be
skipped by the platform too.
"""

import ast
import os
import sys
from pathlib import PurePath
from typing import Iterator, List, Optional, Tuple

from antithesis._assertinfo import AssertionKind
from antithesis._guidance import BOOLEAN, NUMERIC
from ._types import Assertion, GuidanceDeclaration, SourceLocation

# The rich assertions each declare an assertion of one of the basic kinds, so
# the catalog records them the same way
_NUMERIC_RICH_KINDS = {
    "always_greater_than": AssertionKind.ALWAYS,
    "always_greater_than_or_equal_to": AssertionKind.ALWAYS,
    "always_less_than": AssertionKind.ALWAYS,
    "always_less_than_or_equal_to": AssertionKind.ALWAYS,
    "sometimes_greater_than": AssertionKind.SOMETIMES,
    "sometimes_greater_than_or_equal_to": AssertionKind.SOMETIMES,
    "sometimes_less_than": AssertionKind.SOMETIMES,
    "sometimes_less_than_or_equal_to": AssertionKind.SOMETIMES,
}

_BOOLEAN_RICH_KINDS = {
    "always_some": AssertionKind.ALWAYS,
    "sometimes_all": AssertionKind.SOMETIMES,
}

# Which direction is closer to the flipping point, per rich function.
_GUIDANCE_BY_CANONICAL_NAME = {
    "always_greater_than": GuidanceDeclaration(NUMERIC, False),
    "always_greater_than_or_equal_to": GuidanceDeclaration(NUMERIC, False),
    "always_less_than": GuidanceDeclaration(NUMERIC, True),
    "always_less_than_or_equal_to": GuidanceDeclaration(NUMERIC, True),
    "sometimes_greater_than": GuidanceDeclaration(NUMERIC, True),
    "sometimes_greater_than_or_equal_to": GuidanceDeclaration(NUMERIC, True),
    "sometimes_less_than": GuidanceDeclaration(NUMERIC, False),
    "sometimes_less_than_or_equal_to": GuidanceDeclaration(NUMERIC, False),
    "always_some": GuidanceDeclaration(BOOLEAN, False),
    "sometimes_all": GuidanceDeclaration(BOOLEAN, True),
}

_KIND_BY_CANONICAL_NAME = {
    "always": AssertionKind.ALWAYS,
    "always_or_unreachable": AssertionKind.ALWAYS_OR_UNREACHABLE,
    "sometimes": AssertionKind.SOMETIMES,
    "reachable": AssertionKind.REACHABLE,
    "unreachable": AssertionKind.UNREACHABLE,
    **_NUMERIC_RICH_KINDS,
    **_BOOLEAN_RICH_KINDS,
}

CANONICAL_ASSERTION_FUNCTIONS = set(_KIND_BY_CANONICAL_NAME)
CANONICAL_ASSERTION_MODULE = "assertions"


def get_message_idx(std_fun_name: str) -> int:
    """Where `message` sits in a call to each assertion function."""
    if std_fun_name in ["reachable", "unreachable"]:
        return 0
    # The numeric rich assertions take both operands before the message.
    if std_fun_name in _NUMERIC_RICH_KINDS:
        return 2
    return 1


def value_string_field(node, field_name) -> str:
    "Get the value of a field of a node iff it is a string, otherwise return empty string"
    result = ""
    for (fld_name, fld_value) in ast.iter_fields(node):
        if fld_name == field_name:
            if isinstance(fld_value, str):
                result = fld_value
            break
    return result


class StatementVisitor(ast.NodeVisitor):

    def __init__(self, relpath: str, verbose: bool, found: List[Assertion]):
        self._relpath = relpath
        self._function = PurePath(relpath).stem
        self._lambda_base_name = PurePath(relpath).stem
        self._class = ""

        self._is_verbose = verbose

        self._found = found
        self._assertion_modules = set()

        self._assertion_functions = {}  # key = alias_name;  val = native_fn_name
        # ----------------------------------------------------------------------
        # Examples
        # ----------------------------------------------------------------------
        # "impossible": "unreachable"            # alias is "impossible"
        # "definitely": "always_or_unreachable"  # alias is "definitely"
        # "always":     "always"                 # alias is None

    # key = alias_name;  val = native_fn_name
    def std_assertion_name(self, function_name: str) -> Optional[str]:
        return self._assertion_functions.get(function_name)

    def is_assertions_module(self, module_name: str) -> bool:
        return module_name in self._assertion_modules

    @property
    def is_verbose(self) -> bool:
        return self._is_verbose

    def get_last_segment(self, this_name: str, delim='.') -> str:
        all_parts = this_name.split(delim)
        return all_parts[-1]

    def track_assertion_module(self, module_name, alias_name):
        if alias_name is None:
            self._assertion_modules.add(module_name)
        else:
            self._assertion_modules.add(alias_name)
        as_text = ""
        if alias_name is not None and alias_name != module_name:
            as_text = f" as {alias_name}"
        self.log_note(f"import {module_name}{as_text}")

    def log_note(self, s: str):
        if self.is_verbose:
            print("NOTE", s)

    def log_info(self, s: str):
        if self.is_verbose:
            print("INFO", s)

    def track_assertion_function(self, module_name: str, func_name: str, alias_name: Optional[str]):
        self._assertion_modules.add(module_name)
        if alias_name is None:
            self._assertion_functions[func_name] = func_name
        else:
            self._assertion_functions[alias_name] = func_name
        as_text = ""
        if alias_name is not None and alias_name != func_name:
            as_text = f" as {alias_name}"
        self.log_note(f"from {module_name} import {func_name}{as_text}")

    #--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--
    #
    # (1) import assertions
    # (2) import assertions as ant_functions

    # (3) from ..thirdparty import assertions.always
    # (4) from ..thirdparty import assertions.always as always_true

    # (5) from assertions import always
    # (6) from assertions import sometimes as ocassionally_true
    #
    # (7) from assertions import *
    # (8) from thirdparty.assertions import *
    # (9) from ..thirdparty.assertions import *
    # (A) from ..thirdparty import assertions.always
    #--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--

    # case (1a) import assertions
    # case (1b) import ..thirdparty.assertions
    #   expect call statements where 'module name' ends with 'assertions'
    #   and function name is 'always', 'sometimes', etc.
    #
    # case (2a) import assertions as ant_functions
    # case (2b) import ..thirdparty.assertions as ant_functions
    #   expect call statements where 'module name' is ant_functions
    #   and function name is 'always', 'sometimes', etc.
    #
    # case (3) from ..thirdparty import assertions.always
    # expect call statements where 'name' is assertions.always? or is always
    #--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--

    # --- Import (names)
    # import name [as alias]
    def visit_Import(self, node):
        aliases = node.names
        for alias in aliases:
            this_module = self.get_last_segment(alias.name)
            this_alias = alias.asname
            if this_module == CANONICAL_ASSERTION_MODULE:
                self.track_assertion_module(this_module, this_alias)
        super().generic_visit(node)

    # --- ImportFrom (module, names, level)
    # from <module> import name [as alias],...
    def visit_ImportFrom(self, node):
        this_module = "" if node.module is None else node.module
        last_segment = self.get_last_segment(this_module)
        if last_segment == CANONICAL_ASSERTION_MODULE:
            aliases = node.names
            for alias in aliases:
                last_part = self.get_last_segment(alias.name)
                if last_part in CANONICAL_ASSERTION_FUNCTIONS:
                    this_alias = alias.asname
                    self.track_assertion_function(this_module, last_part, this_alias)
                elif last_part == '*':
                    self.track_assertion_module(this_module, this_module)
                    for fn_name in CANONICAL_ASSERTION_FUNCTIONS:
                        self.track_assertion_function(this_module, fn_name, fn_name)
        elif any(n.name == CANONICAL_ASSERTION_MODULE for n in node.names):
            self.track_assertion_module(CANONICAL_ASSERTION_MODULE, None)
        super().generic_visit(node)

    def get_caller_name(self, sub_node) -> str:
        if isinstance(sub_node, ast.Name):
            sub_node_caller = sub_node.id
        elif isinstance(sub_node, ast.Attribute):
            sub_node_caller = sub_node.attr
        elif isinstance(sub_node, ast.Constant):
            sub_node_caller = f"'{sub_node.value}'"
        elif isinstance(sub_node, ast.Call):
            sub_node_caller = self.get_caller_name(sub_node.func)
        else:
            sub_node_caller = f"?{sub_node.__class__.__name__}"

        return sub_node_caller

    # qualified_fn_name could be 'some_alias.sometimes'
    # std_fn_name is one of: 'always', 'sometimes', 'reachable', etc.
    def did_add_to_catalog(self, node: ast.AST, qualified_fn_name: str, std_fn_name: str) -> bool:
        msg_idx = get_message_idx(std_fn_name)
        msg_arg = self.argument_for_call(node, msg_idx)
        if msg_arg is not None:
            msg_text = self.literal_text(msg_arg)
            if msg_text is not None:
                location = SourceLocation(
                    file=self._relpath,
                    begin_line=node.lineno,
                    # colno is not provided by inspect.stack() FrameInfo
                    # if it were, set begin_column to (node.col_offset + 1)
                    begin_column=0,
                    class_name=self._class,
                    function=self._function,
                )
                self._found.append(
                    Assertion(
                        id=msg_text,
                        message=msg_text,
                        kind=_KIND_BY_CANONICAL_NAME[std_fn_name],
                        location=location,
                        guidance=_GUIDANCE_BY_CANONICAL_NAME.get(std_fn_name),
                    )
                )
                return True
        return False

    def _report_call(self, node, qualified_name: str, added: bool):
        if added:
            self.log_info(f"Added {qualified_name}() [{node.lineno}] to the assertion catalog")
        else:
            self.log_info(f"Did not add {qualified_name}() [{node.lineno}] to the assertion catalog")

    # --- Call(func, args, keywords)
    #     where func is typically a Name or Attribute
    #     - Name(id)
    #     - Attribute(value, attr)
    def visit_Call(self, node):
        this_func = node.func
        function_name = "?function_name"

        ref_name: Optional[str] = None
        if isinstance(this_func, ast.Name):
            function_name = self.get_caller_name(node.func)
        elif isinstance(this_func, ast.Attribute):
            function_name = this_func.attr
            ref_name = self.get_caller_name(node.func.value)
        else:
            function_name = "?function_name"

        # check if function_name is in the assertion function whitelist
        std_fn_name = self.std_assertion_name(function_name)
        if std_fn_name is not None:
            # Additional check if there is a ref_name for this function-call
            if ref_name is not None:
                # A ref_name must be in the assertion module whitelist
                if self.is_assertions_module(ref_name):
                    qualified_name = f"{ref_name}.{function_name}"
                    self._report_call(node, qualified_name, self.did_add_to_catalog(node, qualified_name, std_fn_name))
                else:
                    print(f"Unknown '{ref_name}' line [{node.lineno}] - Omitting {ref_name}.{function_name}() from the assertion catalog")
                    # do not catalog
            else:
                self._report_call(node, function_name, self.did_add_to_catalog(node, function_name, std_fn_name))
        else:
            if ref_name is not None:
                if self.is_assertions_module(ref_name):
                    if function_name in CANONICAL_ASSERTION_FUNCTIONS:
                        std_fn_name = function_name
                        qualified_name = f"{ref_name}.{function_name}"
                        self._report_call(node, qualified_name, self.did_add_to_catalog(node, qualified_name, std_fn_name))
                    else:
                        print(f"Not a canonical assertion function {function_name}() [{node.lineno}] in tracked assertion module '{ref_name}'")
            else:
                if function_name in CANONICAL_ASSERTION_FUNCTIONS:
                    print(f"Did not add {function_name}() [{node.lineno}] to the assertion catalog")

        super().generic_visit(node)

    def argument_for_call(self, node: ast.AST, arg_idx: int) -> Optional[ast.AST]:
        if not isinstance(node, ast.Call):
            return None
        args = node.args
        n_arg = len(args)
        if 0 <= arg_idx < n_arg:
            return args[arg_idx]
        return None

    def literal_text(self, node: ast.AST) -> Optional[str]:
        if not isinstance(node, ast.Constant):
            return None
        message = node.value
        if not isinstance(message, str):
            return None
        return message

    # --- ClassDef (name, bases, keywords, body, decorator_list, type_params)
    def visit_ClassDef(self, node):
        old_class = self._class
        self._class = value_string_field(node, 'name')
        super().generic_visit(node)
        self._class = old_class

    # --- FunctionDef, AsyncFunctionDef (name, args, body, ...)
    def visit_FunctionDef(self, node):
        self._function = value_string_field(node, 'name')
        super().generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    # --- Lambda (args, body)
    def visit_Lambda(self, node):
        base_name = self._lambda_base_name
        lineno = node.lineno
        old_function = self._function
        self._function = f"{base_name}_lambda_{lineno}"
        super().generic_visit(node)
        self._function = old_function


def should_skip_dir(d: str) -> bool:
    lx = len(d)
    if lx > 0:
        first_char = d[0]
        if first_char == '.':
            return True
        if lx > 1:
            second_char = d[1]
            if first_char == '_' and second_char == '_':
                return True
    return False


def should_parse_file(root: str, f: str) -> bool:
    return f.endswith('.py') and not os.path.islink(f'{root}/{f}')


def scan_ast(tree: ast.AST, relpath: str, *, verbose: bool = False) -> List[Assertion]:
    """The assertion declarations in an already-parsed module.

    `relpath` names the module in each entry's `location.file` and should be
    relative to the scanned root.
    """
    found: List[Assertion] = []
    visitor = StatementVisitor(relpath, verbose, found)
    visitor.visit(tree)
    return found


def scan_source(source: str, relpath: str, *, verbose: bool = False) -> List[Assertion]:
    """The assertion declarations in one module's source text.

    Raises `SyntaxError` if the source does not parse.
    """
    return scan_ast(ast.parse(source, filename=relpath), relpath, verbose=verbose)


def iter_sources(root: str) -> Iterator[Tuple[str, str, str]]:
    """The catalogable Python sources under a directory, as
    ``(filepath, relpath, source)`` triples.

    Walks ``root`` in sorted order for ``.py`` files, skipping hidden and
    dunder directories and symlinked files. This is the walk policy for
    everything that catalogs a source tree -- `scan_tree` here and the
    platform's instrumentor both drive it -- so they cannot disagree about
    which files count.
    """
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not should_skip_dir(d))
        for name in sorted(f for f in files if should_parse_file(dirpath, f)):
            filepath = os.path.join(dirpath, name)
            relpath = PurePath(filepath).relative_to(root).as_posix()
            with open(filepath, "r", encoding="utf-8") as fp:
                yield filepath, relpath, fp.read()


def scan_tree(root: str, *, verbose: bool = False) -> List[Assertion]:
    """The assertion declarations under a source directory.

    Scans every file `iter_sources` yields. Files that do not parse are
    reported to stderr and skipped. Entries are in path order, so the
    result is stable for a given tree.
    """
    found: List[Assertion] = []
    for filepath, relpath, source in iter_sources(root):
        try:
            found.extend(scan_source(source, relpath, verbose=verbose))
        except SyntaxError as e:
            print(f"Antithesis: skipping {filepath!r}: {e}", file=sys.stderr)
    return found
