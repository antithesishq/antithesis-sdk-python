let
  pkgs = import <nixpkgs> {};
  ffi_lib = import ./ffi/default.nix;
in
  with pkgs;
  python3.pkgs.buildPythonPackage {
    pname = "antithesis-sdk-python";
    version = "0.1.1";
    format = "pyproject";
    src = ./.;
    propagatedBuildInputs = with python3.pkgs; [
      setuptools
      cython
      cffi
    ];
    postInstall = ''
      cp ${ffi_lib}/lib/*.so $out/${python3.sitePackages}/internal
    '';
  }
