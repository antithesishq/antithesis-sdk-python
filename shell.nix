let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [
    pkgs.python3
    (pkgs.python3.withPackages (ps: with ps; [
      black
      build
      cffi
      cython
      mypy
      pdoc
      pip
      pylint
      pytest
      setuptools
      wheel
    ]))
  ];
}
