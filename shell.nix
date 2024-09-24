
let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [
    pkgs.python3
    (pkgs.python3.withPackages (python-pkgs: [
      python-pkgs.build
      python-pkgs.mypy
      python-pkgs.pip
      python-pkgs.pytest
    ]))
  ];
}
