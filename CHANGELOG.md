# Changelog

## 0.4.0

The instrumentor's symbol table changes shape. A method's enclosing class (its qualified name, e.g. `Outer.Inner`) moves out of the `function` column into a new `class` column, and the edge's role (`entry`, `fall-through`, `jump`), which `function` used to carry as a suffix, moves into a new `edge_kind` column, so `function` holds only the function's own name as it does for the other instrumented languages. The runtime matcher resolves columns by header name and rebuilds `co_qualname` as `class.function`. This is a breaking change in the instrumentation cataloging format.

Add a `catalog` module exposing the assertion catalog. `catalog.scan_tree()`
finds the assertion declarations in a source tree with the same scanner the
Antithesis platform runs at build time; `catalog.write()` / `catalog.load()`
serialize them in the catalog file format the `ANTITHESIS_ASSERTION_CATALOG`
environment variable consumes (which now also accepts a path to such a file,
in addition to a platform catalog directory); `catalog.register()` declares
entries at runtime; `catalog.assertions()` lists the catalog registered for
this process. `python -m antithesis.catalog <src> -o catalog.json` runs the
scanner from the command line.

Details serialization failures report `antithesis_error` with the assertion ID or
lifecycle context, and still emit the original record without details (or `{}` for
an event). Non-finite numbers are emitted as the strings "NaN", "Infinity", or
"-Infinity", with warning 6002. Integers of magnitude at least 2^53 produce
warning 6003 and retain their exact digits. Suppressed assertion hits no longer construct assertion records.
`random_choice` raises `IndexError` on an empty list instead of returning `None`,
matching `random.choice`.

Add rich assertions (`always_greater_than`, `always_greater_than_or_equal_to`,
`always_less_than`, `always_less_than_or_equal_to` and their `sometimes_`
counterparts for assertions over numeric value comparisons; `always_some` and
`sometimes_all` for assertions over a set of named propositions). Each behaves like
the corresponding basic assertion and additionally reports the values compared as
guidance so that Antithesis can steer toward the values most likely to flip the
assertion.

## 0.3.1 - 2026-09-03

Use `inspect.currentframe()` instead of `inspect.stack()` when annotating assertions for improved efficiency

Forgo dispatching `init_coverage_module` FFI call when an incompatible symbol table is encountered

## 0.3.0 - 2026-08-28

Remove small modulo bias from `random_choice`.

When used in local debug mode, the output file (`ANTITHESIS_SDK_LOCAL_OUTPUT`) will no longer be truncated at initialization.

Fixed emission of non-ASCII messages.

Free-threading Python interpreters without the GIL are now supported.

The native library bridge uses `ctypes` instead of `cffi`. The SDK now has no runtime dependencies.

## 0.2.0 - 2026-02-17

Add `AntithesisRandom`, a drop-in replacement for `random.Random` that uses Antithesis-driven randomness. This lets you pass an `AntithesisRandom` instance anywhere a `random.Random` is expected, giving Antithesis control over the random choices your code makes.

## 0.1.19 - 2026-02-09

Documentation improvements.

## 0.1.18 - 2025-01-24

Documentation improvements.

## 0.1.17 - 2024-12-13

Downgrade minimum cffi runtime requirement from 1.17 to 1.16.
