"""Runtime edge-notification golden tests.

Each case under ``tests/runtime_edges/<name>/`` is a self-contained, argv-driven,
side-effect-free program plus its instrumented symbol table and the edges each
input is expected to fire:

    runtime_edges/<name>/program.py        -- runnable `python program.py <args>`
    runtime_edges/<name>/expected.sym.tsv  -- the instrumentor's symbol table
    runtime_edges/<name>/cases.json        -- [{"args": [...], "edges": [ids...]}]

The runner activates the SDK coverage runtime with a **non-retiring** recorder
(``notify_coverage`` always returns true, as under pause-injection / EPS
collection), runs ``program.py`` as ``__main__`` for each input, and records the
edge ids notified **in firing order, including repeats** (e.g. a loop's arc once
per iteration). Edge ids are the ``.sym.tsv`` addresses; look up the label /
line / column there.

To regenerate ``expected.sym.tsv`` and the ``edges`` lists after an intentional
change (`args` are authored by hand and preserved)::

    UPDATE_RUNTIME_EDGES=1 python -m pytest sdk/python/repo/tests/test_runtime_edges.py
    # or, without pytest:
    python sdk/python/repo/tests/test_runtime_edges.py --update

``-update`` shells out to the instrumentor CLI (``../antithesis-instrumentor``)
purely as an external build tool -- the SDK never imports it -- so the two
packages stay decoupled. Normal runs read the committed ``expected.sym.tsv`` and
touch the instrumentor not at all.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antithesis._internal import coverage  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME_EDGES_DIR = os.path.join(_HERE, "runtime_edges")
INSTRUMENTOR_SRC = os.path.abspath(
    os.path.join(_HERE, "..", "..", "antithesis-instrumentor", "src")
)
INSTRUMENTOR_MAIN = os.path.join(INSTRUMENTOR_SRC, "instrumentor.py")

UPDATE = os.environ.get("UPDATE_RUNTIME_EDGES") == "1"


class RecordingLib:
    """libvoidstar stand-in that NEVER retires an edge (notify_coverage returns
    true), so every firing -- including repeats -- is recorded in order."""

    def __init__(self):
        self.notifies = []

    def init_coverage_module(self, edge_count, name):
        return 0  # module offset 0 -> notifies are raw addresses

    def notify_coverage(self, edge):
        self.notifies.append(edge)
        return True


class FakeHandler:
    def __init__(self, lib):
        self._lib = lib


def _reset():
    if coverage._ACTIVE is not None:
        try:
            coverage._ACTIVE.unregister()
        except Exception:
            pass
    coverage._ACTIVE = None
    coverage._INSTRUMENTATION_MODULE = None


def _regenerate_sym(program_path, dest_sym):
    """Run the instrumentor CLI on program.py and copy its .sym.tsv to dest_sym."""
    if not os.path.isfile(INSTRUMENTOR_MAIN):
        raise unittest.SkipTest(f"instrumentor not found at {INSTRUMENTOR_MAIN}")
    with tempfile.TemporaryDirectory() as scan, tempfile.TemporaryDirectory() as out:
        shutil.copy(program_path, os.path.join(scan, "program.py"))
        proc = subprocess.run(
            [sys.executable, INSTRUMENTOR_MAIN, "-p", out, scan],
            env={**os.environ, "PYTHONPATH": INSTRUMENTOR_SRC},
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"instrumentor failed:\n{proc.stdout}\n{proc.stderr}")
        produced = glob.glob(os.path.join(out, "python-*", "*.sym.tsv"))
        if not produced:
            raise RuntimeError("instrumentor produced no .sym.tsv")
        shutil.copyfile(produced[0], dest_sym)


def _run_case(sym_path, program_path, args):
    """Run program.py as __main__ with argv under coverage; return the ordered
    list of notified edge addresses (with repeats)."""
    _reset()
    lib = RecordingLib()
    os.environ["ANTITHESIS_OUTPUT_DIR"] = "1"
    resolver = coverage.activate(sym_path, handler=FakeHandler(lib))
    if resolver is None:
        raise RuntimeError(f"coverage did not activate for {sym_path}")
    with open(program_path, encoding="utf-8") as f:
        code = compile(f.read(), program_path, "exec")
    old_argv = sys.argv
    sys.argv = [program_path, *args]
    try:
        # An uncaught exception in the program is fine: edges fired up to the
        # raise are what we record (mirrors a real crash).
        exec(code, {"__name__": "__main__", "__file__": program_path})
    except Exception:
        pass
    finally:
        sys.argv = old_argv
        resolver.unregister()
    return list(lib.notifies)


def _discover():
    return sorted(
        os.path.dirname(p)
        for p in glob.glob(os.path.join(RUNTIME_EDGES_DIR, "*", "program.py"))
    )


def _process(case_dir):
    """Validate (or, under UPDATE, regenerate) one case dir. Returns a list of
    (label, message) assertion failures; empty on success."""
    program = os.path.join(case_dir, "program.py")
    sym = os.path.join(case_dir, "expected.sym.tsv")
    cases_path = os.path.join(case_dir, "cases.json")
    with open(cases_path, encoding="utf-8") as f:
        data = json.load(f)

    if UPDATE:
        _regenerate_sym(program, sym)
    if not os.path.isfile(sym):
        return [("sym", f"missing {sym}; run with UPDATE_RUNTIME_EDGES=1")]

    failures = []
    for case in data["cases"]:
        edges = _run_case(sym, program, case["args"])
        if UPDATE:
            case["edges"] = edges
        elif edges != case["edges"]:
            failures.append(
                (str(case["args"]), f"argv {case['args']}: {edges} != {case['edges']}")
            )
    if UPDATE:
        with open(cases_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    return failures


class RuntimeEdgeTests(unittest.TestCase):
    pass


def _make_test(case_dir):
    def test(self):
        if sys.version_info < (3, 12):
            self.skipTest("sys.monitoring coverage requires Python 3.12+")
        for label, message in _process(case_dir):
            with self.subTest(label):
                self.fail(message)

    return test


for _dir in _discover():
    setattr(RuntimeEdgeTests, f"test_{os.path.basename(_dir)}", _make_test(_dir))


if __name__ == "__main__":
    if "--update" in sys.argv:
        UPDATE = True
        sys.argv.remove("--update")
    unittest.main()
