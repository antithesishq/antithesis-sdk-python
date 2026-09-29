# Antithesis Python

This library provides methods for Python programs to configure the [Antithesis](https://antithesis.com) platform. Functionality is grouped into the packages [`assert`](https://antithesis.com/docs/generated/sdk/python/antithesis/assertions.html) for defining new test properties, [`random`](https://antithesis.com/docs/generated/sdk/python/antithesis/random.html) for Antithesis input, and [`lifecycle`](https://antithesis.com/docs/generated/sdk/python/antithesis/lifecycle.html) for controlling the Antithesis simulation.

For local tooling, the [`catalog`](https://antithesis.com/docs/generated/sdk/python/antithesis/catalog.html) module lists the assertions a source tree declares without running it, and `python -m antithesis.catalog` writes that assertion catalog to a file for local runs.

For general usage guidance see the [Antithesis Python SDK Documentation](https://antithesis.com/docs/using_antithesis/sdk/python/)
