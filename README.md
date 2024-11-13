Antithesis SDK for Python
=========================

If using nix, start a development shell to install build tools to the working environment:

    $ nix-shell


Tools installed includes: 

- black
- build
- mypy
- pdoc
- pylint
- pytest
- python312
- setuptools
- wheel

Packages installed:
- cffi
- Cython

To format source:

		$ black [--check] src

To evaluate with type hints:

		$ mypy

To perform linting:

    $ pylint src

To perform testing:

    $ pytest

To build distributions:

    $ python -m build

To view docs:

    $ pdoc -d google --no-show-source -p 7070 -n src/*.py
    # browse http://localhost:7070/

To smoke-test:

		$ ./result/bin/addx 55 11

		$ ./result/bin/setupx

		$ ./result/bin/eventx

		$ ./result/bin/randomx

		$ ./result/bin/always "Yes, this is ok now" t f t t f f t f

		$ ./result/bin/sometimes "Eventually we get this" t f t t f f t f
