"""Data types for assertion catalog entries."""

from dataclasses import dataclass
from typing import Optional

from antithesis._assertinfo import AssertionKind


@dataclass(frozen=True)
class SourceLocation:
    """Where an assertion was declared.

    For scanned entries, `file` is relative to the scanned root; for loaded
    entries it is whatever the catalog file recorded. `class_name` is the
    enclosing class (serialized as ``class``, which Python reserves) and
    `function` the enclosing function, or ``""`` where there is none.
    """

    file: str
    begin_line: int
    begin_column: int
    class_name: str
    function: str


@dataclass(frozen=True)
class GuidanceDeclaration:
    """The guidance point a rich assertion declares alongside its assertion.

    A rich assertion is an assertion *and* a guidance point, so its catalog
    entry declares both -- otherwise the guidance turns up at runtime having
    never been declared. `maximize` says which direction is closer to the
    flipping point and is fixed for the life of the id.
    """

    guidance_type: str
    """Either ``"numeric"`` or ``"boolean"``."""

    maximize: bool


@dataclass(frozen=True)
class Assertion:
    """One assertion declaration.

    There is one per assertion call site the catalog knows about, whether or
    not that code ever runs: the catalog is a static property of the source,
    not of any particular execution.
    """

    id: str
    """The key under which Antithesis aggregates this assertion's evaluations
    into one test property. Currently equal to `message`; treat it as opaque."""

    message: str
    """The name of the test property, as shown in the triage report."""

    kind: AssertionKind
    location: SourceLocation

    guidance: Optional[GuidanceDeclaration] = None
    """Set for the rich assertions, which declare a guidance point too, and
    `None` for the basic ones, which do not."""
