let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [
    pkgs.python3
    (pkgs.python3.withPackages (ps: with ps; [
      build
      cffi
      cython
      setuptools
      wheel
    ]))
  ];
}
