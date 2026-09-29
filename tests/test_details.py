"""Details behaviour the cross-SDK conformance harness cannot reach: the
public signatures, Mapping implementations other than dict and how often they
are read, caller data staying untouched, the rich assertions' operands reaching
the diagnostics and the guidance watermark, catalog replay, and transport
failures. The wire shape and the diagnostics for JSON-shaped input are its
job."""

import json
from collections.abc import Mapping
from unittest.mock import Mock

import pytest

from antithesis import _details, _guidance, assertions, catalog, lifecycle


@pytest.fixture
def records(monkeypatch):
    emitted = []
    def output(text):
        emitted.append(json.loads(text))
    monkeypatch.setattr(assertions, "dispatch_output", output)
    monkeypatch.setattr(lifecycle, "dispatch_output", output)
    assertions.assert_tracker.clear()
    _details._warned_codes.clear()
    _guidance._numeric_trackers.clear()
    return emitted


def raw(details):
    assertions.assert_raw(False, "display message", details, "file", "function", "class",
                          1, 1, True, True, "always", "Always", "raw id")


def diagnostic_codes(records):
    return [record[key]["code"] for record in records
            for key in ("antithesis_error", "antithesis_warning") if key in record]


@pytest.mark.parametrize("call", [
    lambda: assertions.always(True, "optional always"),
    lambda: assertions.always_or_unreachable(True, "optional always or unreachable"),
    lambda: assertions.sometimes(True, "optional sometimes"),
    lambda: assertions.reachable("optional reachable"),
    lambda: assertions.unreachable("optional unreachable"),
    lambda: lifecycle.setup_complete(),
    lambda: lifecycle.send_event("optional event"),
])
def test_every_entry_point_accepts_omitted_details(records, call):
    call()
    assert len(records) == 1


class CountedMapping(Mapping):
    def __init__(self, values, fail=False):
        self.values = values
        self.reads = 0
        self.fail = fail

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        self.reads += 1
        if self.fail:
            raise RuntimeError("deliberate failure")
        return self.values[key]

    def __bool__(self):
        raise AssertionError("do not test details truthiness")


def test_mappings_are_serialized_once_per_emission(records):
    details = CountedMapping({"answer": 42})
    raw(details)
    # The tracker suppresses this second failure; a suppressed hit must not
    # read the caller's details at all.
    raw(details)
    assert details.reads == 1
    assert records[0]["antithesis_assert"]["details"] == {"answer": 42}


def test_empty_mapping_is_preserved_and_nested_mapping_is_supported(records):
    lifecycle.send_event("empty", CountedMapping({}))
    lifecycle.setup_complete(CountedMapping({}))
    lifecycle.send_event("nested", {"child": CountedMapping({"answer": 42})})
    assert records == [
        {"empty": {}}, {"antithesis_setup": {"status": "complete", "details": {}}},
        {"nested": {"child": {"answer": 42}}},
    ]


def test_non_finite_replacement_leaves_the_callers_data_untouched(records):
    nan = float("nan")
    values = {"nonfinite": [nan, 1.5]}
    raw(CountedMapping(values))
    assert records[0]["antithesis_warning"]["code"] == 6002
    assert records[1]["antithesis_assert"]["details"] == {"nonfinite": ["NaN", 1.5]}
    assert values["nonfinite"][0] is nan


def test_non_finite_guidance_operands_are_reported_in_place_of_the_guidance(records):
    assertions.always_greater_than(float("nan"), 1, "rich id")
    assert [list(record) for record in records] == [
        ["antithesis_warning"], ["antithesis_assert"], ["antithesis_warning"],
    ]
    assert records[0]["antithesis_warning"]["code"] == 6002
    assert records[1]["antithesis_assert"]["details"] == {"left": "NaN", "right": 1}
    assert records[2]["antithesis_warning"]["code"] == 6004
    assert records[2]["antithesis_warning"]["context"] == "rich id"


def test_non_finite_operands_leave_the_guidance_watermark_untouched(records):
    assertions.always_greater_than(float("nan"), 1, "rich id")
    assertions.always_greater_than(float("-inf"), 1, "rich id")
    assertions.always_greater_than(2, 1, "rich id")
    guidance = [record["antithesis_guidance"] for record in records
                if "antithesis_guidance" in record]
    assert [g["guidance_data"] for g in guidance] == [{"left": 2, "right": 1}]
    assert diagnostic_codes(records) == [6002, 6004]


@pytest.mark.parametrize("details, fires", [
    ({"v": 2**53}, True),
    ({"v": -(2**53)}, True),
    ({"v": [2**53]}, True),
    ({"v": {"nested": 1 << 60}}, True),
    ({"v": [0.5, -0.25, 1 << 60]}, True),
    ({"v": float("nan")}, True),
    ({"v": [1.5, float("-inf")]}, True),
    ({"v": 1 / 3}, False),  # sixteen fractional digits
    ({"v": [-0.1234567890123456]}, False),
    ({"v": 1e16}, False),  # written as 1e+16
    ({"v": 1.2345678901234567e+19}, False),
    ({"v": "123456789012345678901234"}, False),
    ({"v": {1 << 60: "an integer key is written as a string"}}, False),
])
def test_warning_prefilter_fires_for_integer_tokens_and_non_finite_floats_only(details, fires):
    # Nothing on the wire shows whether a record was re-parsed, so the
    # prefilter's precision is checked here; missing a case would lose a warning.
    assert _details._may_warn(json.dumps({"event": details})) is fires


def test_a_mapping_raising_any_exception_is_a_serialization_failure(records):
    raw(CountedMapping({"value": 1}, fail=True))
    assert records[0]["antithesis_error"]["code"] == 6001
    assert records[0]["antithesis_error"]["message"].endswith(": deliberate failure")
    assert "details" not in records[1]["antithesis_assert"]


def test_catalog_replay_ignores_even_supplied_details(records, tmp_path):
    # A legacy instrumentor catalog line carrying details: replaying it
    # declares the assertion, and a declaration never has details.
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({
        "id": "catalog", "message": "catalog", "hit": False, "condition": False,
        "must_hit": True, "assert_type": "always", "display_type": "Always",
        "location_info": {"file": "a.py", "function": "f", "class": "", "begin_line": 1, "begin_column": 0},
        "details": {"unneeded": 1},
    }) + "\n")
    catalog.register(catalog.load(path))
    assert len(records) == 1
    assert records[0]["antithesis_assert"]["hit"] is False
    assert records[0]["antithesis_assert"]["id"] == "catalog"
    assert "details" not in records[0]["antithesis_assert"]


def test_transport_failure_is_not_retried_as_a_details_error(monkeypatch):
    output = Mock(side_effect=OSError("transport"))
    monkeypatch.setattr(lifecycle, "dispatch_output", output)
    with pytest.raises(OSError, match="transport"):
        lifecycle.send_event("event", {})
    output.assert_called_once()
