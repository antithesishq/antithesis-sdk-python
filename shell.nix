{ pkgs ? (import ./../../star/build_tools/pinned_nixpkgs.nix).pkgs }:

pkgs.mkShell {
  packages = [
    pkgs.python312
    (pkgs.python312.withPackages (ps: with ps; [
      black
      build
      cffi
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
