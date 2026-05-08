# Changelog

## 0.2.0 - 2026-02-17

Add `AntithesisRandom`, a drop-in replacement for `random.Random` that uses Antithesis-driven randomness. This lets you pass an `AntithesisRandom` instance anywhere a `random.Random` is expected, giving Antithesis control over the random choices your code makes.

## 0.1.19 - 2026-02-09

Documentation improvements.

## 0.1.18 - 2025-01-24

Documentation improvements.

## 0.1.17 - 2024-12-13

Downgrade minimum cffi runtime requirement from 1.17 to 1.16.
