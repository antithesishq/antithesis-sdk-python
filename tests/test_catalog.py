import io
import json
import os
import subprocess
import sys
import textwrap

import pytest

from antithesis.catalog import (
    Assertion,
    AssertionKind,
    GuidanceDeclaration,
    SourceLocation,
    assertions,
    load,
    register,
    scan_source,
    scan_tree,
    write,
)
from antithesis._assertinfo import AssertType

FIVE_CALLS = '''
{prelude}

{always}(x > y, "example always", {{}})
{always_or_unreachable}(y > z, "example always or unreachable", {{}})
{sometimes}(z < a, "example sometimes", {{}})
{reachable}("example reachable", {{}})
{unreachable}("example unreachable", {{}})
'''

FIVE_EXPECTED = [
    ("example always", AssertionKind.ALWAYS, AssertType.ALWAYS, True),
    ("example always or unreachable", AssertionKind.ALWAYS_OR_UNREACHABLE, AssertType.ALWAYS, False),
    ("example sometimes", AssertionKind.SOMETIMES, AssertType.SOMETIMES, True),
    ("example reachable", AssertionKind.REACHABLE, AssertType.REACHABILITY, True),
    ("example unreachable", AssertionKind.UNREACHABLE, AssertType.REACHABILITY, False),
]


def _five_calls(prelude, qualifier=""):
    names = {
        fn: f"{qualifier}{fn}"
        for fn in ["always", "always_or_unreachable", "sometimes", "reachable", "unreachable"]
    }
    return FIVE_CALLS.format(prelude=prelude, **names)


@pytest.mark.parametrize(
    "prelude,qualifier",
    [
        ("import antithesis.assertions", "assertions."),
        ("from antithesis.assertions import always, always_or_unreachable, sometimes, reachable, unreachable", ""),
        ("from antithesis.assertions import *", ""),
        ("from antithesis import assertions", "assertions."),
        ("import antithesis.assertions as ant", "ant."),
    ],
)
def test_scan_catalogs_each_import_style(prelude, qualifier):
    found = scan_source(_five_calls(prelude, qualifier), "foo.py")
    assert len(found) == 5
    for entry, (message, kind, assert_type, must_hit) in zip(found, FIVE_EXPECTED):
        assert entry.message == message
        assert entry.id == message
        assert entry.kind == kind
        assert entry.kind.assert_type == assert_type
        assert entry.kind.must_hit == must_hit
        assert entry.location.file == "foo.py"


def test_scan_resolves_function_aliases():
    src = textwrap.dedent("""
        from antithesis.assertions import sometimes as occasionally, unreachable as impossible

        occasionally(x > 0, "aliased sometimes", {})
        impossible("aliased unreachable", {})
        """)
    found = scan_source(src, "foo.py")
    assert [(e.message, e.kind) for e in found] == [
        ("aliased sometimes", AssertionKind.SOMETIMES),
        ("aliased unreachable", AssertionKind.UNREACHABLE),
    ]


def test_scan_records_location():
    src = textwrap.dedent("""
        from antithesis.assertions import sometimes

        class Game:
            def step(self, x):
                sometimes(x > 0, "in a method", {})

        def helper(y):
            sometimes(y, "in a function", {})
        """)
    found = scan_source(src, "pkg/game.py")
    assert found[0].location == SourceLocation(
        file="pkg/game.py", begin_line=6, begin_column=0, class_name="Game", function="step"
    )
    assert found[1].location == SourceLocation(
        file="pkg/game.py", begin_line=9, begin_column=0, class_name="", function="helper"
    )


def test_scan_skips_what_the_platform_skips():
    src = textwrap.dedent("""
        from antithesis.assertions import sometimes

        def wrapper(cond, msg):
            sometimes(cond, msg, {})           # non-literal message

        def run(y):
            sometimes(y, f"dynamic {y}", {})   # f-string message
            my_own_sometimes(y, "not the SDK's function", {})
        """)
    assert scan_source(src, "foo.py") == []


def test_scan_tree_walks_and_skips(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(
        'from antithesis.assertions import reachable\nreachable("in pkg/a", {})\n'
    )
    (tmp_path / "b.py").write_text(
        'from antithesis.assertions import reachable\nreachable("in b", {})\n'
    )
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "c.py").write_text(
        'from antithesis.assertions import reachable\nreachable("in pycache", {})\n'
    )
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "d.py").write_text(
        'from antithesis.assertions import reachable\nreachable("in hidden", {})\n'
    )
    (tmp_path / "broken.py").write_text("def broken(:\n")

    found = scan_tree(str(tmp_path))
    assert [(e.message, e.location.file) for e in found] == [
        ("in b", "b.py"),
        ("in pkg/a", "pkg/a.py"),
    ]


def test_write_produces_registration_events(tmp_path):
    entry = Assertion(
        id="m",
        message="m",
        kind=AssertionKind.SOMETIMES,
        location=SourceLocation(
            file="a.py", begin_line=3, begin_column=0, class_name="C", function="f"
        ),
    )
    buf = io.StringIO()
    write([entry], buf)
    # One registration event per line — the same event schema every SDK's
    # runtime output uses.
    assert buf.getvalue() == (
        '{"antithesis_assert": {"condition": false, "must_hit": true, '
        '"hit": false, "id": "m", "message": "m", '
        '"display_type": "Sometimes", "assert_type": "sometimes", '
        '"location": {"file": "a.py", "function": "f", "class": "C", '
        '"begin_line": 3, "begin_column": 0}}}\n'
    )


def test_write_matches_register(monkeypatch):
    # `write` and `register` share the AssertInfo construction; a written
    # catalog file is byte-identical to the registration stream.
    entry = Assertion(
        id="goal: parity",
        message="goal: parity",
        kind=AssertionKind.ALWAYS_OR_UNREACHABLE,
        location=SourceLocation(
            file="b.py", begin_line=7, begin_column=2, class_name="", function="g"
        ),
    )
    emitted = []
    monkeypatch.setattr("antithesis.assertions.dispatch_output", emitted.append)
    register([entry])
    buf = io.StringIO()
    write([entry], buf)
    assert buf.getvalue().splitlines() == emitted


def test_load_reads_the_legacy_instrumentor_format(tmp_path):
    # The bare-entry format older instrumentors wrote: no envelope, and the
    # location field spelled "location_info".
    path = tmp_path / "assertion_catalog.json"
    path.write_text(
        '{"condition": false, "message": "m", "details": {}, '
        '"location_info": {"file": "a.py", "function": "f", "class": "C", '
        '"begin_line": 3, "begin_column": 0}, '
        '"hit": false, "must_hit": true, "assert_type": "sometimes", '
        '"display_type": "Sometimes", "id": "m"}\n',
        encoding="utf-8",
    )
    assert load(path) == [
        Assertion(
            id="m",
            message="m",
            kind=AssertionKind.SOMETIMES,
            location=SourceLocation(
                file="a.py", begin_line=3, begin_column=0, class_name="C", function="f"
            ),
        )
    ]


def test_load_skips_runtime_evaluations(tmp_path):
    # Loading a run log yields just the declarations it carries.
    entry = Assertion(
        id="m",
        message="m",
        kind=AssertionKind.SOMETIMES,
        location=SourceLocation(
            file="a.py", begin_line=3, begin_column=0, class_name="C", function="f"
        ),
    )
    path = tmp_path / "run_log.jsonl"
    with open(path, "w", encoding="utf-8") as fp:
        write([entry], fp)
        fp.write(
            '{"antithesis_assert": {"condition": true, "must_hit": true, '
            '"hit": true, "id": "m", "message": "m", '
            '"display_type": "Sometimes", "assert_type": "sometimes", '
            '"location": {"file": "a.py", "function": "f", "class": "C", '
            '"begin_line": 3, "begin_column": 0}, "details": {}}}\n'
        )
    assert load(path) == [entry]


def test_write_load_round_trip(tmp_path):
    entries = scan_source(
        _five_calls("from antithesis.assertions import *"), "foo.py"
    )
    path = tmp_path / "catalog.json"
    write(entries, path)
    assert load(path) == entries


def test_load_skips_junk_lines(tmp_path):
    path = tmp_path / "catalog.json"
    entry = Assertion(
        id="m", message="m", kind=AssertionKind.ALWAYS,
        location=SourceLocation(file="a.py", begin_line=1, begin_column=0, class_name="", function=""),
    )
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("not json at all\n")
        fp.write('{"antithesis_sdk": {"version": "irrelevant"}}\n')
        write([entry], fp)
    assert load(path) == [entry]


def test_load_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "nope.json")
    with pytest.raises(FileNotFoundError):
        load(tmp_path)  # a directory containing no catalog


def test_load_platform_directory_layouts(tmp_path):
    entries = scan_source(
        'from antithesis.assertions import sometimes\nsometimes(x, "the goal", {})\n',
        "app.py",
    )
    # The catalog file directly in the directory
    direct = tmp_path / "direct"
    direct.mkdir()
    write(entries, direct / "assertion_catalog.json")
    assert load(direct) == entries

    # The platform layout: parent dir with one instrumentation subdir
    parent = tmp_path / "parent"
    (parent / "python-abc123").mkdir(parents=True)
    write(entries, parent / "python-abc123" / "assertion_catalog.json")
    assert load(parent) == entries


def test_assertions_resolves_the_env_var(tmp_path, monkeypatch):
    entries = scan_source(
        'from antithesis.assertions import sometimes\nsometimes(x, "the goal", {})\n',
        "app.py",
    )
    path = tmp_path / "catalog.json"
    write(entries, path)

    monkeypatch.delenv("ANTITHESIS_ASSERTION_CATALOG", raising=False)
    assert assertions() == []
    monkeypatch.setenv("ANTITHESIS_ASSERTION_CATALOG", str(path))
    assert assertions() == entries
    monkeypatch.setenv("ANTITHESIS_ASSERTION_CATALOG", str(tmp_path / "gone"))
    assert assertions() == []


# ----------------------------------------------------------------------
# Subprocess tests: handler selection is pinned at import, so anything
# that must observe emitted output runs in a child interpreter.
# ----------------------------------------------------------------------

GAME = '''
from antithesis.assertions import sometimes, reachable

def main():
    sometimes(True, "goal: exercised", {})

def never_called():
    reachable("goal: never reached", {})
'''


def _run(args, tmp_path, **env_overrides):
    env = {k: v for k, v in os.environ.items() if not k.startswith("ANTITHESIS_")}
    env.update(env_overrides)
    return subprocess.run(
        args, env=env, cwd=tmp_path, capture_output=True, text=True, check=True
    )


def _emitted(out_file):
    events = []
    with open(out_file, encoding="utf-8") as fp:
        for line in fp:
            wrapped = json.loads(line)
            if "antithesis_assert" in wrapped:
                events.append(wrapped["antithesis_assert"])
    return events


def _all_records(out_file):
    """Every emitted record, envelope intact -- `_emitted` unwraps only the
    assertion half, and the guidance half is the point here."""
    with open(out_file, encoding="utf-8") as fp:
        return [json.loads(line) for line in fp]


def _assert_goal_then_hit(events):
    goals = [e["message"] for e in events if not e["hit"]]
    hits = {e["message"] for e in events if e["hit"]}
    assert goals == ["goal: exercised", "goal: never reached"]
    assert hits == {"goal: exercised"}
    # The unexercised goal is exactly the catalog-minus-hits complement.
    assert set(goals) - hits == {"goal: never reached"}


def test_cli_writes_a_loadable_catalog(tmp_path):
    (tmp_path / "game.py").write_text(GAME)
    _run(
        [sys.executable, "-m", "antithesis.catalog", str(tmp_path), "-o", "catalog.json"],
        tmp_path,
    )
    entries = load(tmp_path / "catalog.json")
    assert [e.message for e in entries] == ["goal: exercised", "goal: never reached"]

    # stdout mode emits the same lines
    result = _run([sys.executable, "-m", "antithesis.catalog", str(tmp_path)], tmp_path)
    assert result.stdout == (tmp_path / "catalog.json").read_text()


def test_catalog_file_env_var_end_to_end(tmp_path):
    (tmp_path / "game.py").write_text(GAME)
    _run(
        [sys.executable, "-m", "antithesis.catalog", str(tmp_path), "-o", "catalog.json"],
        tmp_path,
    )
    out_file = tmp_path / "out.jsonl"
    _run(
        [sys.executable, "-c", "import game; game.main()"],
        tmp_path,
        ANTITHESIS_ASSERTION_CATALOG=str(tmp_path / "catalog.json"),
        ANTITHESIS_SDK_LOCAL_OUTPUT=str(out_file),
    )
    _assert_goal_then_hit(_emitted(out_file))


def test_catalog_directory_env_var_end_to_end(tmp_path):
    # The platform layout: the env var names a parent directory holding one
    # instrumentation subdirectory.
    (tmp_path / "game.py").write_text(GAME)
    catalog_dir = tmp_path / "catalog" / "python-fake"
    catalog_dir.mkdir(parents=True)
    write(scan_tree(str(tmp_path)), catalog_dir / "assertion_catalog.json")

    out_file = tmp_path / "out.jsonl"
    _run(
        [sys.executable, "-c", "import game; game.main()"],
        tmp_path,
        ANTITHESIS_ASSERTION_CATALOG=str(tmp_path / "catalog"),
        ANTITHESIS_SDK_LOCAL_OUTPUT=str(out_file),
    )
    _assert_goal_then_hit(_emitted(out_file))


def test_scan_and_register_in_process(tmp_path):
    # The no-files workflow: a harness scans its own source at startup and
    # registers the result directly.
    (tmp_path / "game.py").write_text(GAME)
    driver = '''
import antithesis.catalog as catalog
catalog.register(catalog.scan_tree("."))
import game
game.main()
'''
    out_file = tmp_path / "out.jsonl"
    _run(
        [sys.executable, "-c", driver],
        tmp_path,
        ANTITHESIS_SDK_LOCAL_OUTPUT=str(out_file),
    )
    _assert_goal_then_hit(_emitted(out_file))


RICH = """
from antithesis.assertions import (
    always_greater_than,
    always_greater_than_or_equal_to,
    always_less_than,
    always_less_than_or_equal_to,
    sometimes_greater_than,
    sometimes_greater_than_or_equal_to,
    sometimes_less_than,
    sometimes_less_than_or_equal_to,
    always_some,
    sometimes_all,
)

def main():
    always_greater_than(1, 0, "rich: always_greater_than")
    always_greater_than_or_equal_to(1, 0, "rich: always_greater_than_or_equal_to")
    always_less_than(0, 1, "rich: always_less_than")
    always_less_than_or_equal_to(0, 1, "rich: always_less_than_or_equal_to")
    sometimes_greater_than(1, 0, "rich: sometimes_greater_than")
    sometimes_greater_than_or_equal_to(1, 0, "rich: sometimes_greater_than_or_equal_to")
    sometimes_less_than(0, 1, "rich: sometimes_less_than")
    sometimes_less_than_or_equal_to(0, 1, "rich: sometimes_less_than_or_equal_to")
    always_some({"yes": True}, "rich: always_some")
    sometimes_all({"yes": True}, "rich: sometimes_all")
"""

RICH_GUIDANCE = {
    "rich: always_greater_than": ("numeric", False),
    "rich: always_greater_than_or_equal_to": ("numeric", False),
    "rich: always_less_than": ("numeric", True),
    "rich: always_less_than_or_equal_to": ("numeric", True),
    "rich: sometimes_greater_than": ("numeric", True),
    "rich: sometimes_greater_than_or_equal_to": ("numeric", True),
    "rich: sometimes_less_than": ("numeric", False),
    "rich: sometimes_less_than_or_equal_to": ("numeric", False),
    "rich: always_some": ("boolean", False),
    "rich: sometimes_all": ("boolean", True),
}


def test_scan_declares_a_guidance_point_per_rich_assertion():
    # A rich assertion is an assertion *and* a guidance point
    found = {a.message: a for a in scan_source(RICH, "rich.py")}
    assert set(found) == set(RICH_GUIDANCE)
    for message, (guidance_type, maximize) in RICH_GUIDANCE.items():
        assert found[message].guidance == GuidanceDeclaration(guidance_type, maximize), message


def test_basic_assertions_declare_no_guidance_point():
    for assertion in scan_source(GAME, "game.py"):
        assert assertion.guidance is None, assertion.message


def test_written_catalog_carries_both_halves_and_round_trips(tmp_path):
    entries = scan_source(RICH, "rich.py")
    out_file = tmp_path / "catalog.json"
    write(entries, out_file)
    lines = [json.loads(l) for l in out_file.read_text().splitlines() if l.strip()]
    guidance = [l["antithesis_guidance"] for l in lines if "antithesis_guidance" in l]
    assert len(guidance) == len(RICH_GUIDANCE)
    for record in guidance:
        guidance_type, maximize = RICH_GUIDANCE[record["message"]]
        assert record["guidance_type"] == guidance_type
        assert record["maximize"] == maximize
        assert record["hit"] is False
        # A declaration describes a guidance point; it carries no operands.
        assert "guidance_data" not in record
    assert load(out_file) == entries


def test_register_emits_both_halves(tmp_path):
    (tmp_path / "rich.py").write_text(RICH)
    driver = """
import antithesis.catalog as catalog
catalog.register(catalog.scan_tree("."))
"""
    out_file = tmp_path / "out.jsonl"
    _run(
        [sys.executable, "-c", driver],
        tmp_path,
        ANTITHESIS_SDK_LOCAL_OUTPUT=str(out_file),
    )
    events = _all_records(out_file)
    declared = {
        e["antithesis_guidance"]["message"]: (
            e["antithesis_guidance"]["guidance_type"],
            e["antithesis_guidance"]["maximize"],
        )
        for e in events
        if "antithesis_guidance" in e and not e["antithesis_guidance"]["hit"]
    }
    assert declared == RICH_GUIDANCE
    assert all(
        "guidance_data" not in e["antithesis_guidance"]
        for e in events
        if "antithesis_guidance" in e
    )
