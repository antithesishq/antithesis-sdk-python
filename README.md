Antithesis SDK for Python
=========================

Start a development shell.nix to install build tools to the working environment:

    $ nix develop


Tools installed includes: 

- black
- build
- mypy
- pdoc
- pip
- pytest
- python3

To format source:

		$ black [--check] src

To evaluate with type hints:

		$ mypy

To perform linting:

    $ pylint src

To build distributions:

    $ python -m build

To view docs:

    $ pdoc -d google --no-show-source -p 7070 -n src/*.py
    # browse http://localhost:7070/

To smoke-test:

    $ ./result/bin/version

		$ ./result/bin/addx 55 11

		$ ./result/bin/subx 55 11

		$ ./result/bin/always "Yes, this is ok now" t f t t f f t f

		$ ./result/bin/sometimes "Eventually we get this" t f t t f f t f

