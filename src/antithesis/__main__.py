"""``python -m antithesis <target> [args...]`` -- launch a Python program with
Antithesis coverage + assertion cataloging activated before it runs.

Analogous to ``coverage run [-m] <target>`` (i.e. ``python -m coverage run ...``).
"""

import os
import runpy
import sys


def _activate(target_file: str) -> None:
    """Resolve the target's instrumentation subdir and activate coverage + the
    scoped assertion catalog. Best-effort; never raises into the launch."""
    try:
        from antithesis._internal import coverage
    except Exception:
        return  # SDK not importable -> nothing to activate
    try:
        catalog = os.getenv("ANTITHESIS_ASSERTION_CATALOG")
        if not catalog or not os.path.isdir(catalog):
            return  # do nothing when not running in Antithesis or if instrumentation failed to generate coverage artifacts
        # Prefer the module-identity marker baked into the source.
        # Recording it here makes the assertions on-load reuse this exact identity.
        module = coverage.resolve_module_from_marker(target_file)
        if module is not None and os.path.isdir(os.path.join(catalog, module)):
            coverage.activate_module(module)
        # Importing assertions runs its on-load: it reuses the identity recorded
        # above, or -- for a marker-less build -- falls back to the importability
        # vote. Either path runs before the target, so coverage stays complete.
        import antithesis.assertions  # noqa: F401
        if coverage.get_instrumentation_module() is None:
            print(
                f"Antithesis: no instrumentation module resolved for {target_file!r}; "
                "running without coverage / assertion catalog.",
                file=sys.stderr,
            )
    except Exception as exc:
        print(f"Antithesis runner: activation skipped: {exc!r}", file=sys.stderr)


def main(argv) -> None:
    if not argv:
        sys.stderr.write(
            "usage: python -m antithesis [-m module | script.py] [args...]\n"
        )
        raise SystemExit(2)

    if argv[0] == "-m":
        if len(argv) < 2:
            sys.stderr.write("usage: python -m antithesis -m module [args...]\n")
            raise SystemExit(2)
        mod, rest = argv[1], argv[2:]
        target_file = mod
        try:
            import importlib.util

            spec = importlib.util.find_spec(mod)
            if spec and spec.origin:
                target_file = spec.origin
        except Exception:
            pass
        _activate(target_file)
        sys.argv = [target_file] + rest
        runpy.run_module(mod, run_name="__main__", alter_sys=True)
    else:
        script, rest = argv[0], argv[1:]
        _activate(os.path.abspath(script))
        sys.argv = [script] + rest
        runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main(sys.argv[1:])
