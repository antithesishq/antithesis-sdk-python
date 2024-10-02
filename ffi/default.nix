let
  pkgs = import <nixpkgs> {};
in
  with pkgs;
  python3.pkgs.buildPythonPackage {
    pname = "antithesis-sdk-python-ffi";
    version = "0.1.1";
    format = "pyproject";
    src = ./.;
    propagatedBuildInputs = with python3.pkgs; [
      setuptools
      cython
      cffi
    ];
    preBuild = ''
      python build_voidstar.py
    '';
    installPhase = ''
      mkdir -p $out/lib
      cp *.so $out/lib
    '';
  }

