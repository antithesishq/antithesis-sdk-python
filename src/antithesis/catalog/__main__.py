"""``python -m antithesis.catalog <src-dir>... [-o catalog.json]`` -- scan
Python source for assertion declarations and write the assertion catalog.

The catalog is written to stdout, or to ``-o``, as registration-event lines
(the format `antithesis.catalog.load` and the ``ANTITHESIS_ASSERTION_CATALOG``
environment variable consume):

    python -m antithesis.catalog src/ -o catalog.json
    ANTITHESIS_ASSERTION_CATALOG=catalog.json \\
    ANTITHESIS_SDK_LOCAL_OUTPUT=out.jsonl pytest
"""

import argparse
import os
import sys

from antithesis.catalog import scan_source, scan_tree, write


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m antithesis.catalog",
        description="Scan Python source for Antithesis assertion declarations "
        "and write the assertion catalog as JSON lines.",
    )
    parser.add_argument("src", nargs="+", help="source directory (or single .py file) to scan")
    parser.add_argument("-o", "--output", help="catalog file to write (default: stdout)")
    parser.add_argument("--verbose", action="store_true", help="log each call site considered")
    args = parser.parse_args()

    entries = []
    for src in args.src:
        if os.path.isdir(src):
            entries.extend(scan_tree(src, verbose=args.verbose))
        elif os.path.isfile(src):
            with open(src, "r", encoding="utf-8") as fp:
                source = fp.read()
            entries.extend(scan_source(source, os.path.basename(src), verbose=args.verbose))
        else:
            print(f"error: no such file or directory: {src!r}", file=sys.stderr)
            return 2

    if args.output is None:
        write(entries, sys.stdout)
    else:
        write(entries, args.output)
    print(f"{len(entries)} assertion(s) cataloged", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
