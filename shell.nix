{ pkgs ? (import ./../../star/build_tools/pinned_nixpkgs.nix).pkgs }:

pkgs.mkShell {
  packages = [
    pkgs.python39
    (pkgs.python39.withPackages (ps: with ps; [
      # black
      build
      cffi
      cython
      mypy
      pdoc
      # pylint
      pytest
      setuptools
      twine
      wheel
    ]))
  ];
}
