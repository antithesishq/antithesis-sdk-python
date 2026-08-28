import importlib
import os
import subprocess
import sys
import textwrap

import pytest

from antithesis._internal import coverage

_SYM_HEADER = "file\tfunction\tbegin_line\tbegin_column\tend_line\tend_column\taddress"
_SDK_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 12), reason="sys.monitoring coverage requires Python 3.12+"
)


# --------------------------------------------------------------------------
# Fakes + helpers
# --------------------------------------------------------------------------
class RecordingLib:
    """Stand-in for libvoidstar recording the coverage ABI calls."""

    def __init__(self):
        self.inits = []      # [(edge_count, sym_file_name), ...]
        self.notifies = []   # [edge, ...]

    def fuzz_json_data(self, message, length):
        pass

    def fuzz_flush(self):
        pass

    def fuzz_get_random(self):
        return 0

    def init_coverage_module(self, edge_count, name):
        self.inits.append(
            (edge_count, name.decode() if isinstance(name, (bytes, bytearray)) else name)
        )
        return 0  # module offset

    def notify_coverage(self, edge):
        self.notifies.append(edge)
        return False  # mustKeepCalling=False -> resolver retires this edge


class FakeHandler:
    """A libvoidstar-backed handler stand-in: exposes a recording _lib plus the
    Handler output/random surface so it can also stand in as _internal._HANDLER."""

    def __init__(self, lib):
        self._lib = lib

    def output(self, value):
        pass

    def random(self):
        return 0

    @property
    def handles_output(self):
        return True


def _write_sym(path, entries):
    """Write a .sym.tsv from (relpath, line) entries using whole-line spans.

    Addresses are 1-based, so entry i owns addresses 2i+1 (F) 
    and 2i+2 (T). Returns the edge_count (the highest address)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    addr = 0
    with open(path, "w", encoding="utf-8") as f:
        f.write(_SYM_HEADER + "\n")
        for rel, line in entries:
            for desc in ("branch fall-through", "branch jump"):
                addr += 1
                f.write(f"{rel}\tfn ({desc})\t{line}\t1\t{line}\t200\t{addr}\n")
    return addr


def _write_edges(path, rel, entries=(), branch_edges=()):
    """Write a single-file .sym.tsv. `entries` are (line, qualname) method-entry
    edges (one zero-width row each); `branch_edges` are line numbers (each an
    F+T pair). Returns an index
    {('S', line, qual): addr, ('F', line): addr, ('T', line): addr}."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    addr = 0
    idx = {}
    with open(path, "w", encoding="utf-8") as f:
        f.write(_SYM_HEADER + "\n")
        for line, qual in entries:
            addr += 1
            f.write(f"{rel}\t{qual} (method entry)\t{line}\t1\t{line}\t1\t{addr}\n")
            idx[("S", line, qual)] = addr
        for line in branch_edges:
            for arc, desc in (("F", "branch fall-through"), ("T", "branch jump")):
                addr += 1
                f.write(f"{rel}\tfn ({desc})\t{line}\t1\t{line}\t200\t{addr}\n")
                idx[(arc, line)] = addr
    return idx


def _run(source, filename):
    ns = {}
    exec(compile(textwrap.dedent(source).strip() + "\n", filename, "exec"), ns)
    return ns


@pytest.fixture(autouse=True)
def _reset_coverage(monkeypatch):
    """coverage keeps process globals and holds the singleton sys.monitoring
    COVERAGE_ID tool; reset both around every test so they don't leak."""
    monkeypatch.setenv("ANTITHESIS_OUTPUT_DIR", "1")

    def clear():
        if coverage._ACTIVE is not None:
            try:
                coverage._ACTIVE.unregister()
            except Exception:
                pass
        coverage._ACTIVE = None
        coverage._INSTRUMENTATION_MODULE = None

    clear()
    yield
    clear()


# --------------------------------------------------------------------------
# Registration + branch coverage
# --------------------------------------------------------------------------
def test_single_upfront_init_and_both_arcs_covered(tmp_path):
    sym = str(tmp_path / "prog.sym.tsv")
    # ran.py branch on line 2; dead.py branch on line 2 (never executed).
    edge_count = _write_sym(sym, [("ran.py", 2), ("dead.py", 2)])
    lib = RecordingLib()

    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None
    # Registration is a single up-front init over the whole table.
    assert lib.inits == [(edge_count, "prog.sym.tsv")]
    assert resolver.edge_count == edge_count == 4

    ns = _run(
        """
        def f(n):
            if n > 0:
                return 'pos'
            return 'neg'
        """,
        "/deploy/app/ran.py",
    )
    ns["f"](5)   # condition true
    ns["f"](-5)  # condition false
    resolver.unregister()

    # Both arcs of ran.py's branch (addresses 1 and 2) are notified.
    assert set(lib.notifies) == {1, 2}
    # dead.py's edges (3, 4) are in the denominator but never notified.
    assert 3 not in lib.notifies and 4 not in lib.notifies


def test_notify_is_idempotent_per_edge(tmp_path):
    sym = str(tmp_path / "m.sym.tsv")
    _write_sym(sym, [("loop.py", 2)])
    lib = RecordingLib()
    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None

    ns = _run(
        """
        def f(n):
            if n > 0:
                return 1
            return 0
        """,
        "/x/loop.py",
    )
    for _ in range(50):
        ns["f"](1)
        ns["f"](-1)
    resolver.unregister()

    # Each of the two arcs is reported at most once despite many executions
    # (notify_coverage returning False retires the edge).
    assert sorted(lib.notifies) == [1, 2]


def test_activation_is_idempotent(tmp_path):
    sym = str(tmp_path / "a.sym.tsv")
    _write_sym(sym, [("a.py", 2)])
    lib = RecordingLib()
    r1 = coverage.activate(sym, handler=FakeHandler(lib))
    r2 = coverage.activate(sym, handler=FakeHandler(RecordingLib()))
    assert r1 is r2
    assert len(lib.inits) == 1, "second activate must not re-init"


def test_local_handler_without_lib_is_a_noop(tmp_path):
    # A handler with no _lib (Local/Noop, or libvoidstar absent) -> no coverage.
    sym = str(tmp_path / "a.sym.tsv")
    _write_sym(sym, [("a.py", 2)])
    assert coverage.activate(sym, handler=object()) is None
    assert coverage._ACTIVE is None


# --------------------------------------------------------------------------
# Property: the coverage runtime stays inert unless running under Antithesis
# --------------------------------------------------------------------------
def test_coverage_inert_outside_antithesis(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTITHESIS_OUTPUT_DIR", raising=False)
    sym = str(tmp_path / "a.sym.tsv")
    _write_sym(sym, [("a.py", 2)])
    lib = RecordingLib()

    assert coverage.activate(sym, handler=FakeHandler(lib)) is None
    assert coverage._ACTIVE is None
    assert lib.inits == []


def test_activate_module_inert_outside_antithesis(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTITHESIS_OUTPUT_DIR", raising=False)
    import antithesis._internal as _internal

    cat = str(tmp_path)
    mod = "python-x"
    _write_sym(os.path.join(cat, mod, f"{mod}.sym.tsv"), [("a.py", 2)])
    monkeypatch.setenv("ANTITHESIS_ASSERTION_CATALOG", cat)
    monkeypatch.setattr(_internal, "_HANDLER", FakeHandler(RecordingLib()), raising=False)

    coverage.activate_module(mod)
    assert coverage.get_instrumentation_module() == mod
    assert coverage._ACTIVE is None


def test_suffix_resolution_is_deploy_location_agnostic(tmp_path):
    # Table stores the build-relative path pkg/mod.py; the code runs from an
    # unrelated absolute deploy path. Suffix matching must still resolve it.
    sym = str(tmp_path / "s.sym.tsv")
    edge_count = _write_sym(sym, [("pkg/mod.py", 2)])
    lib = RecordingLib()
    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None

    ns = _run(
        """
        def sign(n):
            if n < 0:
                return -1
            return 1
        """,
        "/some/where/else/pkg/mod.py",
    )
    ns["sign"](-5)
    ns["sign"](7)
    resolver.unregister()
    assert set(lib.notifies) == {1, 2} and edge_count == 2


def test_unrelated_files_are_not_instrumented(tmp_path):
    sym = str(tmp_path / "s.sym.tsv")
    _write_sym(sym, [("owned.py", 2)])
    lib = RecordingLib()
    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None

    # Code from a file not in the table (e.g. stdlib/third-party) is ignored.
    ns = _run(
        """
        def g(n):
            if n:
                return 1
            return 0
        """,
        "/usr/lib/python3.12/some_stdlib.py",
    )
    ns["g"](1)
    ns["g"](0)
    resolver.unregister()
    assert lib.notifies == []


def test_entry_edges_cover_entered_functions(tmp_path):
    sym = str(tmp_path / "prog.sym.tsv")
    # Method-entry edges for the module and two functions (no branch edges).
    idx = _write_edges(sym, "s.py", entries=[(1, "<module>"), (1, "f"), (4, "g")])
    lib = RecordingLib()
    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None
    assert lib.inits == [(3, "prog.sym.tsv")]

    ns = _run(
        """
        def f(n):
            return n + 1

        def g(n):
            return n - 1
        """,
        "/deploy/s.py",
    )
    ns["f"](5)
    resolver.unregister()

    got = set(lib.notifies)
    # The module body ran (during exec) and f was entered; g never was.
    assert idx[("S", 1, "<module>")] in got, "module entry not covered"
    assert idx[("S", 1, "f")] in got, "entered function f not covered"
    assert idx[("S", 4, "g")] not in got, "unentered function g should be uncovered"


def test_entry_and_branch_together(tmp_path):
    sym = str(tmp_path / "h.sym.tsv")
    # Entry edges for the module and f, plus a branch on line 2 (`if n > 0:`).
    idx = _write_edges(sym, "h.py", entries=[(1, "<module>"), (1, "f")], branch_edges=(2,))
    lib = RecordingLib()
    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None

    ns = _run(
        """
        def f(n):
            if n > 0:
                return 1
            return 0
        """,
        "/x/h.py",
    )
    ns["f"](5)  # true path: entry(f) + branch fall-through on line 2
    resolver.unregister()

    got = set(lib.notifies)
    assert idx[("S", 1, "f")] in got
    assert idx[("F", 2)] in got
    assert idx[("T", 2)] not in got, "not-taken branch arc should be uncovered"


def test_entry_edge_notified_once(tmp_path):
    sym = str(tmp_path / "loop.sym.tsv")
    idx = _write_edges(sym, "l.py", entries=[(1, "f")])
    lib = RecordingLib()
    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None

    ns = _run(
        """
        def f():
            return 0
        """,
        "/x/l.py",
    )
    for _ in range(25):
        ns["f"]()
    resolver.unregister()
    # f is entered 25 times but its entry edge is reported at most once.
    assert lib.notifies.count(idx[("S", 1, "f")]) == 1


class KeepCallingLib(RecordingLib):
    """libvoidstar stand-in that never retires an edge (notify_coverage returns
    True), as under pause injection / EPS collection."""

    def notify_coverage(self, edge):
        self.notifies.append(edge)
        return True  # mustKeepCalling=True -> caller must report every hit


def test_entry_edge_reported_every_hit_when_not_retired(tmp_path):
    sym = str(tmp_path / "loop.sym.tsv")
    idx = _write_edges(sym, "l.py", entries=[(1, "f")])
    lib = KeepCallingLib()
    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None

    ns = _run(
        """
        def f():
            return 0
        """,
        "/x/l.py",
    )
    for _ in range(25):
        ns["f"]()
    resolver.unregister()
    # notify_coverage keeps returning True (EPS / pause-injection mode): PY_START
    # must NOT be DISABLE'd after the first entry, so all 25 entries are reported.
    assert lib.notifies.count(idx[("S", 1, "f")]) == 25


def test_resolve_module_from_marker(tmp_path):
    marked = tmp_path / "prog.py"
    marked.write_text(
        "def f():\n    return 1\n# antithesis-module: python-abc123def456\n"
    )
    assert coverage.resolve_module_from_marker(str(marked)) == "python-abc123def456"

    unmarked = tmp_path / "plain.py"
    unmarked.write_text("def f():\n    return 1\n")
    assert coverage.resolve_module_from_marker(str(unmarked)) is None

    assert coverage.resolve_module_from_marker(str(tmp_path / "missing.py")) is None


def test_reification_scope_does_not_notify_entry_edge(tmp_path):
    # A PEP 695 generic def runs a `<generic parameters of gen>` scope at
    # definition time that shares gen's co_firstlineno. Keying the entry edge on
    # co_qualname must keep that reification from marking gen covered -- only a
    # real call to gen counts.
    sym = str(tmp_path / "g.sym.tsv")
    idx = _write_edges(sym, "g.py", entries=[(1, "gen")])
    lib = RecordingLib()
    resolver = coverage.activate(sym, handler=FakeHandler(lib))
    assert resolver is not None

    ns = _run(
        """
        def gen[T](x: T) -> T:
            return x
        """,
        "/x/g.py",
    )
    # Defining gen ran its reification scope, but gen itself was never called.
    assert lib.notifies == [], "reification scope must not notify the entry edge"

    ns["gen"](1)
    resolver.unregister()
    assert idx[("S", 1, "gen")] in set(lib.notifies)


# --------------------------------------------------------------------------
# Property: graceful degradation when instrumentation was not run / produced no
# edge table -- no crash, no interference with the running application
# --------------------------------------------------------------------------
def test_missing_symtable_is_graceful(tmp_path):
    lib = RecordingLib()
    # A .sym.tsv that does not exist -> activation declines without raising.
    assert coverage.activate(str(tmp_path / "nope.sym.tsv"), handler=FakeHandler(lib)) is None
    assert coverage._ACTIVE is None


def test_empty_symtable_is_inert(tmp_path):
    sym = str(tmp_path / "empty.sym.tsv")
    _write_sym(sym, [])  # header only -> zero edges
    lib = RecordingLib()
    # A zero-edge table registers no monitoring and does not announce an empty
    # module to libvoidstar; activation returns None.
    assert coverage.activate(sym, handler=FakeHandler(lib)) is None
    assert coverage._ACTIVE is None
    assert lib.inits == []


def test_activate_module_without_symtable_records_identity_only(tmp_path, monkeypatch):
    import antithesis._internal as _internal

    monkeypatch.setenv("ANTITHESIS_ASSERTION_CATALOG", str(tmp_path))  # no subdir/.sym.tsv
    monkeypatch.setattr(_internal, "_HANDLER", FakeHandler(RecordingLib()), raising=False)
    # Instrumentation never produced a table for this module: identity is still
    # recorded (for catalog resolution) but coverage stays inert
    coverage.activate_module("python-uninstrumented")
    assert coverage.get_instrumentation_module() == "python-uninstrumented"
    assert coverage._ACTIVE is None


def test_catalog_loads_even_when_edge_table_absent(tmp_path, monkeypatch):
    import antithesis._internal as _internal
    import antithesis.assertions as assertions

    cat = str(tmp_path / "cat")
    mod = "python-noedges"
    os.makedirs(os.path.join(cat, mod))
    # A one-line assertion catalog, but deliberately NO {mod}.sym.tsv.
    with open(os.path.join(cat, mod, "assertion_catalog.json"), "w", encoding="utf-8") as f:
        f.write('{"assert_type":"always","message":"m","id":"m"}\n')

    saved_handler = _internal._HANDLER
    _internal._HANDLER = FakeHandler(RecordingLib())
    monkeypatch.setenv("ANTITHESIS_ASSERTION_CATALOG", cat)
    try:
        importlib.reload(assertions)

        assert coverage.get_instrumentation_module() == mod
        assert coverage._ACTIVE is None
    finally:
        _internal._HANDLER = saved_handler
        monkeypatch.delenv("ANTITHESIS_ASSERTION_CATALOG", raising=False)
        importlib.reload(assertions)


# --------------------------------------------------------------------------
# Assertion-catalog folder selection
# --------------------------------------------------------------------------
def _make_catalog(root, subdirs):
    for sub in subdirs:
        d = os.path.join(root, sub)
        os.makedirs(d)
        open(os.path.join(d, "assertion_catalog.json"), "w").close()


def test_catalog_selection_by_recorded_identity(tmp_path):
    import antithesis.assertions as A

    cat = str(tmp_path)
    _make_catalog(cat, ["python-real0001", "python-decoy999"])

    # A recorded identity resolves the exact module unambiguously, even with
    # several subdirs present (no marker-less vote needed).
    coverage._INSTRUMENTATION_MODULE = "python-real0001"
    assert A._select_instrumentation_folder(cat) == "python-real0001"

    # Identity naming a module whose catalog isn't present -> None (no fallback).
    coverage._INSTRUMENTATION_MODULE = "python-ghost0000"
    assert A._select_instrumentation_folder(cat) is None


def test_catalog_selection_single_subdir_fallback(tmp_path):
    import antithesis.assertions as A

    cat = str(tmp_path)
    _make_catalog(cat, ["python-solo0002"])
    coverage._INSTRUMENTATION_MODULE = None
    # Exactly one subdir and no identity -> unambiguous, use it.
    assert A._select_instrumentation_folder(cat) == "python-solo0002"


def test_sdk_import_fallback_activates_coverage(tmp_path):
    import antithesis._internal as _internal
    import antithesis.assertions as assertions

    cat = str(tmp_path / "cat")
    mod = "python-fb01"
    sym = os.path.join(cat, mod, f"{mod}.sym.tsv")
    _write_sym(sym, [("tgt.py", 2)])
    open(os.path.join(cat, mod, "assertion_catalog.json"), "w").close()

    lib = RecordingLib()
    saved_handler = _internal._HANDLER
    saved_env = os.environ.get("ANTITHESIS_ASSERTION_CATALOG")
    _internal._HANDLER = FakeHandler(lib)
    os.environ["ANTITHESIS_ASSERTION_CATALOG"] = cat
    try:
        # Re-running the on-load block (single subdir) resolves the module and,
        # with no runner having activated coverage, starts it as a fallback.
        importlib.reload(assertions)
        assert coverage.get_instrumentation_module() == mod
        assert lib.inits == [(2, f"{mod}.sym.tsv")]

        # Code executed after the SDK import is covered from that point on.
        ns = _run(
            """
            def h(n):
                if n > 0:
                    return 'p'
                return 'n'
            """,
            os.path.join(cat, "..", "tgt.py"),
        )
        ns["h"](3)
        ns["h"](-3)
        assert set(lib.notifies) == {1, 2}
    finally:
        _internal._HANDLER = saved_handler
        if saved_env is None:
            os.environ.pop("ANTITHESIS_ASSERTION_CATALOG", None)
        else:
            os.environ["ANTITHESIS_ASSERTION_CATALOG"] = saved_env
        # Restore assertions' module state to the no-catalog baseline for other tests.
        importlib.reload(assertions)


# --------------------------------------------------------------------------
# `python -m antithesis <target>` runner (end-to-end, subprocess)
# --------------------------------------------------------------------------
def test_runner_covers_main_target(tmp_path):
    prog = tmp_path / "prog.py"
    prog.write_text(
        "def pick(n):\n"
        "    if n > 0:\n"
        "        return 'pos'\n"
        "    return 'nonpos'\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    print('PROG_RAN', pick(5), pick(-5))\n"
    )

    cat = tmp_path / "cat"
    mod = "python-runner01"
    _write_sym(str(cat / mod / f"{mod}.sym.tsv"), [("prog.py", 2)])
    (cat / mod / "assertion_catalog.json").write_text("")

    # A sitecustomize that injects a recording libvoidstar by patching
    # ctypes.CDLL, and records the coverage ABI calls to a results file
    # (libvoidstar is absent in the test environment, so without this the
    # handler has no _lib). The stub's entry points are plain functions, so
    # the handler's argtypes/restype typing sticks to them harmlessly; the
    # v2 lease symbols are deliberately absent, exercising the v1 fallback.
    results = tmp_path / "results.txt"
    sc = tmp_path / "sc"
    sc.mkdir()
    (sc / "sitecustomize.py").write_text(textwrap.dedent(f"""
        import ctypes
        _OUT = {str(results)!r}
        def _rec(s):
            with open(_OUT, 'a') as f:
                f.write(s + '\\n')
        class _Lib:
            def __init__(self):
                self.fuzz_json_data = lambda m, n: None
                self.fuzz_flush = lambda: None
                self.fuzz_get_random = lambda: 0
                def _init(ec, name):
                    _rec('init:%d:%s' % (ec, name.decode() if isinstance(name, bytes) else name))
                    return 0
                self.init_coverage_module = _init
                def _notify(e):
                    _rec('notify:%d' % e)
                    return False
                self.notify_coverage = _notify
        ctypes.CDLL = lambda path: _Lib()
    """))

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(sc), _SDK_SRC])
    env["ANTITHESIS_ASSERTION_CATALOG"] = str(cat)
    env["ANTITHESIS_OUTPUT_DIR"] = str(tmp_path)  # simulate the Antithesis environment
    out = subprocess.run(
        [sys.executable, "-m", "antithesis", str(prog)],
        env=env, capture_output=True, text=True,
    )
    assert "PROG_RAN pos nonpos" in out.stdout, (out.stdout, out.stderr)

    lines = results.read_text().splitlines() if results.exists() else []
    inits = [l for l in lines if l.startswith("init:")]
    notifies = [l for l in lines if l.startswith("notify:")]
    assert inits, f"coverage never activated via `-m antithesis` (stderr: {out.stderr})"
    assert f"{mod}.sym.tsv" in inits[0]
    # Both arcs of the __main__ target's branch were covered before user code ran.
    assert set(notifies) == {"notify:1", "notify:2"}
