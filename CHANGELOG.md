# Changelog

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
