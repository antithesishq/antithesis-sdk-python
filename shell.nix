let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [
    pkgs.python312
    (pkgs.python312.withPackages (ps: with ps; [
      black
      build
      cffi
      cython
      mypy
      pdoc
      pylint
      pytest
      setuptools
      wheel
    ]))
  ];
}
