Antithesis SDK for Python
=========================

Start a development shell.nix to install build tools to the working environment:

    $ nix develop


Tools installed includes: 

- python3
- build
- mypy
- pip
- pytest
- black

To format source:

		$ black [-v] [--check] .

To evaluate with type hints:

		$ mypy src

To perform linting:

    $ pylint src/*.py

To build:

    $ python -m build

To smoke-test:

		$ ./result/bin/always "Yes, this is ok now" t f t t f f t f

		$ ./result/bin/sometimes "Eventually we get this" t f t t f f t f

